from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime, timezone

from app.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.courses import Course, CourseSession
from app.services.scheduler import generate_course_schedule

router = APIRouter(prefix="/api/courses", tags=["courses"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class CourseIn(BaseModel):
    name: str
    url: Optional[str] = None
    total_hours: float
    hours_per_week: float = 4.0
    deadline: Optional[datetime] = None
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Назва не може бути порожньою")
        return v.strip()

    @field_validator("total_hours")
    @classmethod
    def validate_hours(cls, v):
        if v <= 0 or v > 1000:
            raise ValueError("Загальна тривалість має бути від 0 до 1000 годин")
        return v

    @field_validator("hours_per_week")
    @classmethod
    def validate_weekly_hours(cls, v):
        if v <= 0 or v > 100:
            raise ValueError("Годин на тиждень має бути від 1 до 100")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if v and not v.strip().startswith(("http://", "https://")):
            raise ValueError("URL повинен починатися з http:// або https://")
        return v


class CourseOut(BaseModel):
    id: int
    name: str
    url: Optional[str]
    total_hours: float
    hours_per_week: float
    deadline: Optional[datetime]
    description: Optional[str]
    is_active: bool
    manual_progress_percent: Optional[float]
    created_at: datetime
    class Config:
        from_attributes = True


class CourseProgressOut(BaseModel):
    course_id: int
    course_name: str
    total_hours: float
    completed_hours: float
    time_progress_percent: float
    manual_progress_percent: Optional[float]
    total_sessions: int
    completed_sessions: int
    missed_sessions: int


class SessionOut(BaseModel):
    id: int
    course_id: int
    scheduled_at: datetime
    planned_minutes: int
    actual_minutes: Optional[int]
    is_completed: bool
    is_missed: bool
    is_rescheduled: bool = False
    completed_at: Optional[datetime]
    class Config:
        from_attributes = True


class SessionCompleteIn(BaseModel):
    actual_minutes: Optional[int] = None


class ManualProgressIn(BaseModel):
    manual_progress_percent: float

    @field_validator("manual_progress_percent")
    @classmethod
    def validate_pct(cls, v):
        if v < 0 or v > 100:
            raise ValueError("Відсоток має бути від 0 до 100")
        return round(v, 1)


# ── Courses ──────────────────────────────────────────────────────────────────

@router.get("", response_model=List[CourseOut])
async def list_courses(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(Course).where(Course.user_id == user.id, Course.is_active == True)
        .order_by(Course.created_at.desc())
    )
    return q.scalars().all()


@router.post("", response_model=CourseOut, status_code=201)
async def create_course(
    data: CourseIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    course = Course(
        user_id=user.id,
        name=data.name,
        url=data.url,
        total_hours=data.total_hours,
        hours_per_week=data.hours_per_week,
        deadline=data.deadline,
        description=data.description,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


@router.get("/{course_id}", response_model=CourseOut)
async def get_course(
    course_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user.id)
    )
    course = q.scalar_one_or_none()
    if not course:
        raise HTTPException(404, "Курс не знайдено")
    return course


@router.put("/{course_id}", response_model=CourseOut)
async def update_course(
    course_id: int,
    data: CourseIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user.id)
    )
    course = q.scalar_one_or_none()
    if not course:
        raise HTTPException(404, "Курс не знайдено")

    for field, val in data.model_dump(exclude_none=True).items():
        setattr(course, field, val)
    course.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(course)
    return course


@router.delete("/{course_id}")
async def archive_course(
    course_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user.id)
    )
    course = q.scalar_one_or_none()
    if not course:
        raise HTTPException(404, "Курс не знайдено")
    course.is_active = False
    await db.commit()
    return {"status": "ok"}


@router.post("/{course_id}/generate-schedule")
async def generate_schedule(
    course_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and persist a course session schedule."""
    q = await db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user.id)
    )
    course = q.scalar_one_or_none()
    if not course:
        raise HTTPException(404, "Курс не знайдено")

    # Remove old unfinished sessions before regenerating
    old_q = await db.execute(
        select(CourseSession).where(
            CourseSession.course_id == course_id,
            CourseSession.is_completed == False,
        )
    )
    for old_session in old_q.scalars().all():
        await db.delete(old_session)
    await db.flush()

    sessions, warning = await generate_course_schedule(db, user.id, course)

    for s in sessions:
        db.add(s)

    await db.commit()

    return {
        "sessions_created": len(sessions),
        "warning": warning,
        "sessions": [SessionOut.model_validate(s) for s in sessions],
    }


# ── Progress ─────────────────────────────────────────────────────────────────

@router.get("/{course_id}/progress", response_model=CourseProgressOut)
async def get_progress(
    course_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user.id)
    )
    course = q.scalar_one_or_none()
    if not course:
        raise HTTPException(404, "Курс не знайдено")

    q = await db.execute(
        select(CourseSession).where(CourseSession.course_id == course_id)
    )
    sessions = q.scalars().all()

    total_sessions = len(sessions)
    completed = [s for s in sessions if s.is_completed]
    missed = [s for s in sessions if s.is_missed]

    completed_minutes = sum(
        (s.actual_minutes or s.planned_minutes) for s in completed
    )
    completed_hours = completed_minutes / 60
    time_pct = min(100.0, (completed_hours / course.total_hours * 100)) if course.total_hours else 0

    return CourseProgressOut(
        course_id=course_id,
        course_name=course.name,
        total_hours=course.total_hours,
        completed_hours=round(completed_hours, 2),
        time_progress_percent=round(time_pct, 1),
        manual_progress_percent=course.manual_progress_percent,
        total_sessions=total_sessions,
        completed_sessions=len(completed),
        missed_sessions=len(missed),
    )


@router.put("/{course_id}/manual-progress")
async def set_manual_progress(
    course_id: int,
    data: ManualProgressIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user.id)
    )
    course = q.scalar_one_or_none()
    if not course:
        raise HTTPException(404, "Курс не знайдено")
    course.manual_progress_percent = data.manual_progress_percent
    await db.commit()
    return {"status": "ok", "manual_progress_percent": data.manual_progress_percent}


# ── Sessions ─────────────────────────────────────────────────────────────────

@router.get("/{course_id}/sessions", response_model=List[SessionOut])
async def list_sessions(
    course_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(CourseSession).where(
            CourseSession.course_id == course_id,
            CourseSession.user_id == user.id,
        ).order_by(CourseSession.scheduled_at)
    )
    return q.scalars().all()


@router.patch("/sessions/{session_id}/complete")
async def complete_session(
    session_id: int,
    data: SessionCompleteIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a session complete. Prevents double-counting hours."""
    q = await db.execute(
        select(CourseSession).where(
            CourseSession.id == session_id, CourseSession.user_id == user.id
        )
    )
    session = q.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Заняття не знайдено")
    if session.is_completed:
        raise HTTPException(400, "Заняття вже позначено виконаним")

    session.is_completed = True
    session.is_missed = False
    session.completed_at = datetime.now(timezone.utc)
    if data.actual_minutes is not None:
        if data.actual_minutes < 0:
            raise HTTPException(400, "Фактичний час не може бути від'ємним")
        session.actual_minutes = data.actual_minutes
    else:
        session.actual_minutes = session.planned_minutes

    await db.commit()
    await db.refresh(session)
    return SessionOut.model_validate(session)


@router.patch("/sessions/{session_id}/reschedule")
async def reschedule_session(
    session_id: int,
    new_date: datetime,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reschedule a missed or future session to a new date."""
    q = await db.execute(
        select(CourseSession).where(
            CourseSession.id == session_id, CourseSession.user_id == user.id
        )
    )
    session = q.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Заняття не знайдено")
    if session.is_completed:
        raise HTTPException(400, "Не можна перенести виконане заняття")

    if new_date <= datetime.now(timezone.utc):
        raise HTTPException(400, "Нова дата повинна бути в майбутньому")

    session.scheduled_at = new_date
    session.is_missed = False
    session.is_rescheduled = True
    await db.commit()
    await db.refresh(session)
    return SessionOut.model_validate(session)


@router.patch("/sessions/{session_id}/mark-missed")
async def mark_session_missed(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(CourseSession).where(
            CourseSession.id == session_id, CourseSession.user_id == user.id
        )
    )
    session = q.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Заняття не знайдено")
    if session.is_completed:
        raise HTTPException(400, "Заняття вже виконано")

    session.is_missed = True
    await db.commit()
    return {"status": "ok", "message": "Заняття позначено як пропущене"}
