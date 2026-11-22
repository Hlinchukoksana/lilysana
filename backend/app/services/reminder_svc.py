"""
Reminder service: APScheduler-based.
Loads pending reminders from DB on startup.
Sends via Aiogram bot.
"""
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.reminders import Reminder, ReminderStatus
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler = None
_bot = None  # Will be set at startup


def init_reminder_service(bot, scheduler: AsyncIOScheduler):
    global _bot, _scheduler
    _bot = bot
    _scheduler = scheduler


async def _send_reminder(reminder_id: int):
    """Job function: fetch reminder from DB, send message, mark sent."""
    async with AsyncSessionLocal() as db:
        q = await db.execute(select(Reminder).where(Reminder.id == reminder_id))
        reminder = q.scalar_one_or_none()
        if not reminder or reminder.status != ReminderStatus.PENDING:
            return

        try:
            if _bot:
                await _bot.send_message(
                    chat_id=reminder.user_id,
                    text=reminder.message_text,
                    parse_mode="HTML",
                )
            reminder.status = ReminderStatus.SENT
            reminder.sent_at = datetime.now(timezone.utc)
            logger.info(f"Reminder {reminder_id} sent to user {reminder.user_id}")
        except Exception as e:
            logger.error(f"Failed to send reminder {reminder_id}: {e}")
            reminder.status = ReminderStatus.FAILED

        await db.commit()


def schedule_reminder(reminder: Reminder):
    """Add a single reminder to APScheduler."""
    if not _scheduler:
        return
    job_id = f"reminder_{reminder.id}"
    # Remove existing job with same ID to avoid duplicates
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)

    _scheduler.add_job(
        _send_reminder,
        trigger=DateTrigger(run_date=reminder.fire_at),
        id=job_id,
        args=[reminder.id],
        replace_existing=True,
        misfire_grace_time=3600,  # allow 1h late fire
    )


async def restore_reminders_from_db(session_maker=None):
    """Called on server startup to reload all pending reminders."""
    maker = session_maker or AsyncSessionLocal
    async with maker() as db:
        now = datetime.now(timezone.utc)
        q = await db.execute(
            select(Reminder).where(
                and_(
                    Reminder.status == ReminderStatus.PENDING,
                    Reminder.fire_at > now,
                )
            )
        )
        reminders = q.scalars().all()
        count = 0
        for r in reminders:
            schedule_reminder(r)
            count += 1
        logger.info(f"Restored {count} pending reminders from DB")


async def cancel_reminder(db: AsyncSession, reminder_id: int):
    """Cancel a scheduled reminder."""
    q = await db.execute(select(Reminder).where(Reminder.id == reminder_id))
    reminder = q.scalar_one_or_none()
    if reminder:
        reminder.status = ReminderStatus.CANCELLED
        if _scheduler:
            job_id = f"reminder_{reminder_id}"
            if _scheduler.get_job(job_id):
                _scheduler.remove_job(job_id)
        await db.commit()
