from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from app.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.courses import Course, CourseSession
from app.models.nmt import NMTRepetition, TestResult, NMTSubject

router = APIRouter(prefix="/api/statistics", tags=["statistics"])


def _make_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class StatisticsOut(BaseModel):
    total_study_hours: float
    completed_sessions: int
    total_sessions: int
    missed_sessions: int
    completion_rate_percent: float
    nmt_repetitions_completed: int
    nmt_repetitions_total: int
    nmt_repetitions_pending: int
    nmt_tests_total: int
    nmt_subjects_active: int
    courses_active: int
    avg_nmt_score: Optional[float]
    best_nmt_score: Optional[float]
    week_hours_completed: float
    week_hours_planned: float
    study_streak_days: Optional[int]


@router.get("", response_model=StatisticsOut)
async def get_statistics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    # Course sessions
    all_sessions_q = await db.execute(
        select(CourseSession).where(CourseSession.user_id == user.id)
    )
    all_sessions = all_sessions_q.scalars().all()

    completed_sessions = [s for s in all_sessions if s.is_completed]
    total_sessions = len(all_sessions)
    comp_count = len(completed_sessions)

    total_study_minutes = sum(
        (s.actual_minutes or s.planned_minutes) for s in completed_sessions
    )
    total_study_hours = round(total_study_minutes / 60, 2)

    completion_rate = (comp_count / total_sessions * 100) if total_sessions else 0.0

    # Week stats
    week_sessions = [
        s for s in all_sessions
        if _make_aware(s.scheduled_at) is not None and _make_aware(s.scheduled_at) >= week_start
    ]
    week_planned = sum(s.planned_minutes for s in week_sessions)
    week_completed_sessions = [s for s in week_sessions if s.is_completed]
    week_completed_min = sum(
        (s.actual_minutes or s.planned_minutes) for s in week_completed_sessions
    )

    # NMT repetitions
    reps_q = await db.execute(
        select(NMTRepetition).where(
            NMTRepetition.user_id == user.id,
            NMTRepetition.skipped == False,
        )
    )
    reps = reps_q.scalars().all()
    reps_completed = [r for r in reps if r.completed]

    # Missed sessions
    missed_count = sum(1 for s in all_sessions if s.is_missed)

    # NMT scores
    scores_q = await db.execute(
        select(TestResult.score_percent).where(TestResult.user_id == user.id)
    )
    scores = [row[0] for row in scores_q.all()]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None
    best_score = max(scores) if scores else None

    # NMT tests total
    nmt_tests_q = await db.execute(
        select(func.count(TestResult.id)).where(TestResult.user_id == user.id)
    )
    nmt_tests_total = nmt_tests_q.scalar() or 0

    # Active NMT subjects
    nmt_subj_q = await db.execute(
        select(func.count(NMTSubject.id)).where(NMTSubject.user_id == user.id)
    )
    nmt_subjects_active = nmt_subj_q.scalar() or 0

    # Pending repetitions
    reps_pending = [r for r in reps if not r.completed and _make_aware(r.scheduled_date) is not None and _make_aware(r.scheduled_date) >= now]

    # Active courses
    courses_q = await db.execute(
        select(func.count(Course.id)).where(
            Course.user_id == user.id, Course.is_active == True
        )
    )
    active_courses = courses_q.scalar() or 0

    # Study streak (days with at least one completed session)
    study_streak_days = None
    if completed_sessions:
        sorted_dates = sorted(
            {s.scheduled_at.date() for s in completed_sessions}, reverse=True
        )
        streak = 1
        for i in range(1, len(sorted_dates)):
            delta = (sorted_dates[i-1] - sorted_dates[i]).days
            if delta == 1:
                streak += 1
            else:
                break
        study_streak_days = streak

    return StatisticsOut(
        total_study_hours=total_study_hours,
        completed_sessions=comp_count,
        total_sessions=total_sessions,
        missed_sessions=missed_count,
        completion_rate_percent=round(completion_rate, 1),
        nmt_repetitions_completed=len(reps_completed),
        nmt_repetitions_total=len(reps),
        nmt_repetitions_pending=len(reps_pending),
        nmt_tests_total=nmt_tests_total,
        nmt_subjects_active=nmt_subjects_active,
        courses_active=active_courses,
        avg_nmt_score=avg_score,
        best_nmt_score=best_score,
        week_hours_completed=round(week_completed_min / 60, 2),
        week_hours_planned=round(week_planned / 60, 2),
        study_streak_days=study_streak_days,
    )
