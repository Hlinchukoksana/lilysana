"""
Course schedule generation algorithm.

Given a course's total_hours, hours_per_week, and optional deadline,
generates a list of CourseSession records distributed across available days.

Rules:
- Never plan in the past
- Respect daily_limit_minutes (with reserve)
- Respect course_hours_per_week weekly limit
- Respect deadline
- Alert if deadline is unreachable
- Leave reserve buffer (reserve_percent)
"""
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.courses import Course, CourseSession
from app.models.user import LearningLimits, BusySlot, UserSettings
from app.services.load_control import get_daily_used_minutes, get_weekly_used_minutes


async def generate_course_schedule(
    db: AsyncSession,
    user_id: int,
    course: Course,
) -> Tuple[List[CourseSession], Optional[str]]:
    """
    Returns (sessions_to_create, warning_message_or_None).
    """
    now = datetime.now(timezone.utc)

    # Get limits
    limits_q = await db.execute(
        select(LearningLimits).where(LearningLimits.user_id == user_id)
    )
    limits = limits_q.scalar_one_or_none()

    daily_limit_min = (limits.daily_limit_minutes if limits else 120)
    reserve = (limits.reserve_percent if limits else 20) / 100
    weekly_course_limit_min = (limits.course_hours_per_week * 60 if limits else 240)

    effective_daily = daily_limit_min * (1 - reserve)
    # Cap individual session at 2 hours for comfort
    max_session_min = min(120, int(effective_daily))

    # Preferred session chunk: derive from hours_per_week
    # If user wants 4 h/week and we target ~3 sessions/week → ~80 min/session
    sessions_per_week = 3
    preferred_session_min = max(
        30,
        min(
            max_session_min,
            int((course.hours_per_week * 60) / sessions_per_week),
        ),
    )

    total_minutes_needed = int(course.total_hours * 60)

    # Find deadline pressure
    deadline = course.deadline
    if deadline and deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    latest_date = deadline if deadline else (now + timedelta(weeks=26))
    if latest_date <= now:
        return [], "Дедлайн вже минув. Будь ласка, оновіть курс."

    # Get user settings for preferred study days and time
    settings_q = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    user_settings = settings_q.scalar_one_or_none()

    study_days_set = {0, 1, 2, 3, 4}  # default: Mon–Fri
    if user_settings and user_settings.study_days:
        try:
            parsed = {int(d.strip()) for d in str(user_settings.study_days).split(",") if d.strip()}
            if parsed:
                study_days_set = parsed
        except Exception:
            pass

    preferred_hour = user_settings.preferred_start_hour if (user_settings and user_settings.preferred_start_hour is not None) else 18
    preferred_min = user_settings.preferred_start_minute if (user_settings and user_settings.preferred_start_minute is not None) else 0

    # Get busy slots
    busy_q = await db.execute(
        select(BusySlot).where(BusySlot.user_id == user_id)
    )
    busy_slots: List[BusySlot] = list(busy_q.scalars().all())

    sessions_created: List[dict] = []
    minutes_scheduled = 0
    current_day = now + timedelta(days=1)
    current_day = current_day.replace(hour=preferred_hour, minute=preferred_min, second=0, microsecond=0)

    safety_cap = 365  # max days to iterate
    days_iterated = 0

    while minutes_scheduled < total_minutes_needed and current_day < latest_date:
        days_iterated += 1
        if days_iterated > safety_cap:
            break

        # Check if day is an allowed study day
        if current_day.weekday() not in study_days_set:
            current_day += timedelta(days=1)
            current_day = current_day.replace(hour=preferred_hour, minute=preferred_min, second=0, microsecond=0)
            continue

        # Check weekly limit
        week_start = current_day - timedelta(days=current_day.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)

        _, course_used_this_week = await get_weekly_used_minutes(db, user_id, week_start, week_end)
        # Also count sessions we're planning this week
        planned_this_week = sum(
            s["planned_minutes"]
            for s in sessions_created
            if week_start <= s["scheduled_at"] < week_end
        )
        total_course_week = course_used_this_week + planned_this_week

        if total_course_week >= weekly_course_limit_min:
            # Skip to next week
            current_day = week_end + timedelta(hours=preferred_hour, minutes=preferred_min)
            continue

        # Check daily used (from DB)
        daily_used = await get_daily_used_minutes(db, user_id, current_day)
        # Also count sessions we plan today
        day_start = current_day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        planned_today = sum(
            s["planned_minutes"]
            for s in sessions_created
            if day_start <= s["scheduled_at"] < day_end
        )
        total_daily = daily_used + planned_today

        available_today = effective_daily - total_daily
        if available_today <= 0:
            current_day += timedelta(days=1)
            current_day = current_day.replace(hour=preferred_hour, minute=preferred_min, second=0, microsecond=0)
            continue

        # Cap by weekly remaining
        remaining_weekly = weekly_course_limit_min - total_course_week
        session_min = min(
            preferred_session_min,
            int(available_today),
            int(remaining_weekly),
            total_minutes_needed - minutes_scheduled,
        )

        if session_min < 15:  # too short to be useful
            current_day += timedelta(days=1)
            current_day = current_day.replace(hour=preferred_hour, minute=preferred_min, second=0, microsecond=0)
            continue

        # Check if day is busy (simple check: skip fully-busy days)
        if _is_fully_busy(current_day, busy_slots, session_min):
            current_day += timedelta(days=1)
            current_day = current_day.replace(hour=preferred_hour, minute=preferred_min, second=0, microsecond=0)
            continue

        sessions_created.append({
            "course_id": course.id,
            "user_id": user_id,
            "scheduled_at": current_day,
            "planned_minutes": session_min,
        })
        minutes_scheduled += session_min

        # Move to next day
        current_day += timedelta(days=1)
        current_day = current_day.replace(hour=preferred_hour, minute=preferred_min, second=0, microsecond=0)

    warning = None
    if minutes_scheduled < total_minutes_needed:
        remaining_h = (total_minutes_needed - minutes_scheduled) / 60
        if deadline:
            warning = (
                f"Увага: не вдається запланувати всі {course.total_hours} год курсу до дедлайну. "
                f"Залишилося {remaining_h:.1f} год незаплановано. "
                "Розгляньте збільшення тижневого ліміту або перенесення дедлайну."
            )
        else:
            warning = None  # just schedule what fits

    # Create ORM objects
    session_objects = []
    for s in sessions_created:
        obj = CourseSession(
            course_id=s["course_id"],
            user_id=s["user_id"],
            scheduled_at=s["scheduled_at"],
            planned_minutes=s["planned_minutes"],
        )
        session_objects.append(obj)

    return session_objects, warning


def _is_fully_busy(day: datetime, busy_slots: List[BusySlot], needed_minutes: int) -> bool:
    """Very simple check: if total busy time on this day covers >4h, skip."""
    day_busy = 0
    for slot in busy_slots:
        if slot.is_recurring and slot.day_of_week == day.weekday():
            day_busy += slot.duration_minutes
        elif not slot.is_recurring and slot.date:
            slot_date = slot.date
            if slot_date.tzinfo is None:
                slot_date = slot_date.replace(tzinfo=timezone.utc)
            if slot_date.date() == day.date():
                day_busy += slot.duration_minutes
    return day_busy >= 240  # 4+ hours busy → skip
