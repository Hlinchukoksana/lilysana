"""
Workload control service.
Checks user limits before scheduling new sessions.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.courses import CourseSession
from app.models.nmt import NMTRepetition
from app.models.user import LearningLimits


async def get_weekly_used_minutes(
    db: AsyncSession,
    user_id: int,
    week_start: datetime,
    week_end: datetime,
) -> Tuple[int, int]:
    """
    Returns (nmt_minutes_used, course_minutes_used) for the given week.
    NMT minutes come from NMTRepetition sessions.
    Course minutes come from CourseSession sessions.
    """
    # NMT repetitions in this week
    nmt_q = await db.execute(
        select(func.sum(NMTRepetition.duration_minutes)).where(
            and_(
                NMTRepetition.user_id == user_id,
                NMTRepetition.scheduled_date >= week_start,
                NMTRepetition.scheduled_date < week_end,
                NMTRepetition.skipped == False,
            )
        )
    )
    nmt_minutes = nmt_q.scalar() or 0

    # Course sessions in this week
    course_q = await db.execute(
        select(func.sum(CourseSession.planned_minutes)).where(
            and_(
                CourseSession.user_id == user_id,
                CourseSession.scheduled_at >= week_start,
                CourseSession.scheduled_at < week_end,
                CourseSession.is_missed == False,
            )
        )
    )
    course_minutes = course_q.scalar() or 0

    return int(nmt_minutes), int(course_minutes)


async def get_daily_used_minutes(
    db: AsyncSession,
    user_id: int,
    day: datetime,
) -> int:
    """Returns total planned minutes for a specific calendar day."""
    day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    nmt_q = await db.execute(
        select(func.sum(NMTRepetition.duration_minutes)).where(
            and_(
                NMTRepetition.user_id == user_id,
                NMTRepetition.scheduled_date >= day_start,
                NMTRepetition.scheduled_date < day_end,
                NMTRepetition.skipped == False,
            )
        )
    )
    nmt_min = nmt_q.scalar() or 0

    course_q = await db.execute(
        select(func.sum(CourseSession.planned_minutes)).where(
            and_(
                CourseSession.user_id == user_id,
                CourseSession.scheduled_at >= day_start,
                CourseSession.scheduled_at < day_end,
                CourseSession.is_missed == False,
            )
        )
    )
    course_min = course_q.scalar() or 0

    return int(nmt_min) + int(course_min)


async def can_schedule_session(
    db: AsyncSession,
    user_id: int,
    session_minutes: int,
    target_date: datetime,
    module: str,  # "nmt" | "course"
) -> Tuple[bool, str]:
    """
    Returns (can_schedule: bool, reason: str).
    Checks daily limit and weekly module limit.
    """
    limits_q = await db.execute(
        select(LearningLimits).where(LearningLimits.user_id == user_id)
    )
    limits = limits_q.scalar_one_or_none()
    if not limits:
        return True, "ok"  # no limits set yet

    # Daily check
    daily_used = await get_daily_used_minutes(db, user_id, target_date)
    effective_daily_limit = limits.daily_limit_minutes * (1 - limits.reserve_percent / 100)
    if daily_used + session_minutes > effective_daily_limit:
        return False, (
            f"Денний ліміт перевищено. Використано {daily_used} хв, "
            f"ліміт {int(effective_daily_limit)} хв."
        )

    # Weekly module check
    week_start = target_date - timedelta(days=target_date.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    nmt_used, course_used = await get_weekly_used_minutes(db, user_id, week_start, week_end)

    if module == "nmt":
        weekly_limit_min = limits.nmt_hours_per_week * 60
        if nmt_used + session_minutes > weekly_limit_min:
            return False, (
                f"Тижневий ліміт НМТ перевищено. "
                f"Використано {nmt_used} хв, ліміт {int(weekly_limit_min)} хв."
            )
    elif module == "course":
        weekly_limit_min = limits.course_hours_per_week * 60
        if course_used + session_minutes > weekly_limit_min:
            return False, (
                f"Тижневий ліміт курсів перевищено. "
                f"Використано {course_used} хв, ліміт {int(weekly_limit_min)} хв."
            )

    return True, "ok"
