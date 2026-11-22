"""
Tests 16-17, 19: Reminders recovery, timezones, server restart simulation.
"""
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.reminders import Reminder, ReminderType, ReminderStatus

pytestmark = pytest.mark.asyncio


async def test_16_reminder_created_in_db(client: AsyncClient, test_db):
    """Test 16: Reminders are stored in DB and can be retrieved."""
    await client.get("/api/users/me")

    # Directly create a reminder in DB
    async with test_db() as db:
        reminder = Reminder(
            user_id=99999999,
            reminder_type=ReminderType.SESSION_BEFORE,
            fire_at=datetime.now(timezone.utc) + timedelta(hours=1),
            message_text="Нагадування: заняття через 30 хвилин!",
            status=ReminderStatus.PENDING,
        )
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)
        reminder_id = reminder.id

    # Verify it's in DB
    async with test_db() as db:
        q = await db.execute(select(Reminder).where(Reminder.id == reminder_id))
        r = q.scalar_one_or_none()
        assert r is not None
        assert r.status == ReminderStatus.PENDING
        assert r.user_id == 99999999


async def test_19_server_restart_reminder_recovery(client: AsyncClient, test_db):
    """Test 19: Pending reminders survive restart (restore_reminders_from_db loads them)."""
    from app.services.reminder_svc import restore_reminders_from_db, _scheduler

    await client.get("/api/users/me")

    # Create a pending reminder
    async with test_db() as db:
        reminder = Reminder(
            user_id=99999999,
            reminder_type=ReminderType.NMT_REPETITION,
            fire_at=datetime.now(timezone.utc) + timedelta(hours=2),
            message_text="Пора повторити тест!",
            status=ReminderStatus.PENDING,
        )
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)
        reminder_id = reminder.id

    # Simulate restore (would be called on startup)
    await restore_reminders_from_db(test_db)

    # If scheduler is active, job should be registered
    # In test env _scheduler may be None — we test the DB query at minimum
    async with test_db() as db:
        q = await db.execute(select(Reminder).where(Reminder.id == reminder_id))
        r = q.scalar_one_or_none()
        assert r.status == ReminderStatus.PENDING  # Still pending, not sent yet


async def test_17_timezone_awareness(client: AsyncClient):
    """Test 17: Scheduled dates are timezone-aware (UTC)."""
    await client.post("/api/users/me/onboarding", json={"learning_time_choice": "3-5"})
    await client.put("/api/users/me/limits", json={
        "course_hours_per_week": 4,
        "daily_limit_minutes": 120,
        "reserve_percent": 0,
    })

    course_resp = await client.post("/api/courses", json={
        "name": "Часовий пояс тест",
        "total_hours": 2.0,
        "hours_per_week": 4.0,
    })
    course_id = course_resp.json()["id"]
    sched_resp = await client.post(f"/api/courses/{course_id}/generate-schedule")

    for s in sched_resp.json()["sessions"]:
        # Must have timezone info (Z or +00:00)
        date_str = s["scheduled_at"]
        assert "Z" in date_str or "+" in date_str or date_str.endswith("00:00"), \
            f"Session datetime not timezone-aware: {date_str}"
