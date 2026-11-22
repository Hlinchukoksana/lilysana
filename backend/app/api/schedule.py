from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from app.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.courses import CourseSession
from app.models.nmt import NMTRepetition, TestResult, NMTTest, NMTTopic, NMTSubject

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


def _make_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class ScheduleItemOut(BaseModel):
    type: str            # "course_session" | "nmt_repetition"
    id: int
    title: str
    subtitle: Optional[str]
    scheduled_at: datetime
    duration_minutes: int
    is_completed: bool
    is_missed: bool
    reference_id: Optional[int]  # course_id or test_id


@router.get("", response_model=List[ScheduleItemOut])
async def get_schedule(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all scheduled events in the given date range (defaults to next 30 days)."""
    now = datetime.now(timezone.utc)
    if not start_date:
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        end_date = start_date + timedelta(days=30)

    items: List[ScheduleItemOut] = []

    # Course sessions
    q = await db.execute(
        select(CourseSession).where(
            and_(
                CourseSession.user_id == user.id,
                CourseSession.scheduled_at >= start_date,
                CourseSession.scheduled_at < end_date,
            )
        ).order_by(CourseSession.scheduled_at)
    )
    course_sessions = q.scalars().all()

    for s in course_sessions:
        # Fetch course name
        from app.models.courses import Course
        cq = await db.execute(select(Course).where(Course.id == s.course_id))
        course = cq.scalar_one_or_none()
        items.append(ScheduleItemOut(
            type="course_session",
            id=s.id,
            title=course.name if course else "Курс",
            subtitle="Навчальне заняття",
            scheduled_at=s.scheduled_at,
            duration_minutes=s.planned_minutes,
            is_completed=s.is_completed,
            is_missed=s.is_missed,
            reference_id=s.course_id,
        ))

    # NMT repetitions
    q = await db.execute(
        select(NMTRepetition).where(
            and_(
                NMTRepetition.user_id == user.id,
                NMTRepetition.scheduled_date >= start_date,
                NMTRepetition.scheduled_date < end_date,
                NMTRepetition.skipped == False,
            )
        ).order_by(NMTRepetition.scheduled_date)
    )
    repetitions = q.scalars().all()

    for r in repetitions:
        # Fetch test/topic name
        rq = await db.execute(
            select(TestResult).where(TestResult.id == r.result_id)
        )
        result = rq.scalar_one_or_none()
        test_name = "НМТ Повторення"
        if result:
            tq = await db.execute(select(NMTTest).where(NMTTest.id == result.test_id))
            test = tq.scalar_one_or_none()
            if test:
                test_name = f"Повторення: {test.name}"

        items.append(ScheduleItemOut(
            type="nmt_repetition",
            id=r.id,
            title=test_name,
            subtitle="НМТ повторення",
            scheduled_at=r.scheduled_date,
            duration_minutes=r.duration_minutes,
            is_completed=r.completed,
            is_missed=False,
            reference_id=r.result_id,
        ))

    # Sort everything by date
    items.sort(key=lambda x: _make_aware(x.scheduled_at))
    return items
