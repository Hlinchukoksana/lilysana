from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, List
from datetime import datetime, timezone

from app.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.nmt import (
    NMTSubject, NMTTopic, NMTTest, TestResult, NMTRepetition,
    OPTIONAL_SUBJECTS
)
from app.services.repetition import get_repetition_recommendation, calculate_repetition_date

router = APIRouter(prefix="/api/nmt", tags=["nmt"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class SubjectOut(BaseModel):
    id: int
    name: str
    is_optional: bool
    is_active: bool
    display_order: int
    class Config:
        from_attributes = True


class SubjectCreate(BaseModel):
    name: str
    is_optional: bool = True

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Назва не може бути порожньою")
        return v.strip()


class TopicOut(BaseModel):
    id: int
    subject_id: int
    name: str
    created_at: datetime
    class Config:
        from_attributes = True


class TopicCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Назва теми не може бути порожньою")
        return v.strip()


class TestOut(BaseModel):
    id: int
    topic_id: int
    name: str
    url: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True


class TestCreate(BaseModel):
    name: str
    url: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Назва тесту не може бути порожньою")
        return v.strip()

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if v and not v.strip().startswith(("http://", "https://")):
            raise ValueError("URL повинен починатися з http:// або https://")
        return v


class TestResultIn(BaseModel):
    score_percent: float
    notes: Optional[str] = None

    @field_validator("score_percent")
    @classmethod
    def validate_score(cls, v):
        if v < 0 or v > 100:
            raise ValueError("Результат повинен бути від 0 до 100")
        return round(v, 1)


class TestResultOut(BaseModel):
    id: int
    test_id: int
    score_percent: float
    taken_at: datetime
    notes: Optional[str]
    class Config:
        from_attributes = True


class TestHistoryOut(BaseModel):
    test_id: int
    test_name: str
    attempts: int
    first_score: Optional[float]
    last_score: Optional[float]
    best_score: Optional[float]
    results: List[TestResultOut]


class RepetitionOut(BaseModel):
    id: int
    scheduled_date: datetime
    duration_minutes: int
    completed: bool
    skipped: bool
    class Config:
        from_attributes = True


class RepetitionChoiceIn(BaseModel):
    choice_id: Optional[str] = None  # "regular" | "practice" for high scores


# ── Subjects ─────────────────────────────────────────────────────────────────

@router.get("/subjects", response_model=List[SubjectOut])
async def list_subjects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(NMTSubject)
        .where(NMTSubject.user_id == user.id, NMTSubject.is_active == True)
        .order_by(NMTSubject.display_order)
    )
    return q.scalars().all()


@router.post("/subjects", response_model=SubjectOut, status_code=201)
async def create_subject(
    data: SubjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.name not in OPTIONAL_SUBJECTS and data.is_optional:
        pass  # Custom subjects are allowed
    subj = NMTSubject(
        user_id=user.id,
        name=data.name,
        is_optional=data.is_optional,
        display_order=100,
    )
    db.add(subj)
    await db.commit()
    await db.refresh(subj)
    return subj


@router.put("/subjects/{subject_id}", response_model=SubjectOut)
async def update_subject(
    subject_id: int,
    data: SubjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(NMTSubject).where(
            NMTSubject.id == subject_id, NMTSubject.user_id == user.id
        )
    )
    subj = q.scalar_one_or_none()
    if not subj:
        raise HTTPException(404, "Предмет не знайдено")
    subj.name = data.name
    await db.commit()
    await db.refresh(subj)
    return subj


@router.delete("/subjects/{subject_id}")
async def deactivate_subject(
    subject_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(NMTSubject).where(
            NMTSubject.id == subject_id,
            NMTSubject.user_id == user.id,
            NMTSubject.is_optional == True,  # Only optional subjects can be removed
        )
    )
    subj = q.scalar_one_or_none()
    if not subj:
        raise HTTPException(404, "Предмет не знайдено або є обов'язковим")
    subj.is_active = False
    await db.commit()
    return {"status": "ok"}


# ── Topics ─────────────────────────────────────────────────────────────────

@router.get("/subjects/{subject_id}/topics", response_model=List[TopicOut])
async def list_topics(
    subject_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(NMTSubject).where(
            NMTSubject.id == subject_id, NMTSubject.user_id == user.id
        )
    )
    if not q.scalar_one_or_none():
        raise HTTPException(404, "Предмет не знайдено")

    q = await db.execute(
        select(NMTTopic)
        .where(NMTTopic.subject_id == subject_id, NMTTopic.user_id == user.id)
        .order_by(NMTTopic.created_at)
    )
    return q.scalars().all()


@router.post("/subjects/{subject_id}/topics", response_model=TopicOut, status_code=201)
async def create_topic(
    subject_id: int,
    data: TopicCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(NMTSubject).where(
            NMTSubject.id == subject_id, NMTSubject.user_id == user.id
        )
    )
    if not q.scalar_one_or_none():
        raise HTTPException(404, "Предмет не знайдено")

    topic = NMTTopic(subject_id=subject_id, user_id=user.id, name=data.name)
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic


# ── Tests ─────────────────────────────────────────────────────────────────

@router.get("/topics/{topic_id}/tests", response_model=List[TestOut])
async def list_tests(
    topic_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(NMTTopic).where(
            NMTTopic.id == topic_id, NMTTopic.user_id == user.id
        )
    )
    if not q.scalar_one_or_none():
        raise HTTPException(404, "Тему не знайдено")

    q = await db.execute(
        select(NMTTest)
        .where(NMTTest.topic_id == topic_id, NMTTest.user_id == user.id)
        .order_by(NMTTest.created_at)
    )
    return q.scalars().all()


@router.post("/topics/{topic_id}/tests", response_model=TestOut, status_code=201)
async def create_test(
    topic_id: int,
    data: TestCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(NMTTopic).where(
            NMTTopic.id == topic_id, NMTTopic.user_id == user.id
        )
    )
    if not q.scalar_one_or_none():
        raise HTTPException(404, "Тему не знайдено")

    test = NMTTest(topic_id=topic_id, user_id=user.id, name=data.name, url=data.url)
    db.add(test)
    await db.commit()
    await db.refresh(test)
    return test


# ── Results ─────────────────────────────────────────────────────────────────

@router.post("/tests/{test_id}/results")
async def add_result(
    test_id: int,
    data: TestResultIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a test result and return a repetition recommendation."""
    q = await db.execute(
        select(NMTTest).where(NMTTest.id == test_id, NMTTest.user_id == user.id)
    )
    test = q.scalar_one_or_none()
    if not test:
        raise HTTPException(404, "Тест не знайдено")

    result = TestResult(
        test_id=test_id,
        user_id=user.id,
        score_percent=data.score_percent,
        notes=data.notes,
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)

    recommendation = get_repetition_recommendation(data.score_percent)
    return {
        "result": TestResultOut.model_validate(result),
        "recommendation": recommendation.to_dict(),
    }


@router.get("/tests/{test_id}/results", response_model=TestHistoryOut)
async def get_test_history(
    test_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(NMTTest).where(NMTTest.id == test_id, NMTTest.user_id == user.id)
    )
    test = q.scalar_one_or_none()
    if not test:
        raise HTTPException(404, "Тест не знайдено")

    q = await db.execute(
        select(TestResult)
        .where(TestResult.test_id == test_id, TestResult.user_id == user.id)
        .order_by(TestResult.taken_at)
    )
    results = q.scalars().all()

    scores = [r.score_percent for r in results]
    return TestHistoryOut(
        test_id=test_id,
        test_name=test.name,
        attempts=len(results),
        first_score=scores[0] if scores else None,
        last_score=scores[-1] if scores else None,
        best_score=max(scores) if scores else None,
        results=[TestResultOut.model_validate(r) for r in results],
    )


# ── Repetitions ─────────────────────────────────────────────────────────────

@router.post("/results/{result_id}/schedule-repetition", response_model=RepetitionOut)
async def schedule_repetition(
    result_id: int,
    data: RepetitionChoiceIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(TestResult).where(
            TestResult.id == result_id, TestResult.user_id == user.id
        )
    )
    result = q.scalar_one_or_none()
    if not result:
        raise HTTPException(404, "Результат не знайдено")

    # Check if repetition already exists
    if result.repetition and not result.repetition.skipped:
        raise HTTPException(400, "Повторення вже заплановано")

    recommendation = get_repetition_recommendation(result.score_percent)
    rep_date = calculate_repetition_date(recommendation, data.choice_id)

    rep = NMTRepetition(
        result_id=result_id,
        user_id=user.id,
        scheduled_date=rep_date,
        duration_minutes=recommendation.duration_minutes or 60,
    )
    db.add(rep)
    await db.commit()
    await db.refresh(rep)
    return rep


@router.get("/repetitions", response_model=List[RepetitionOut])
async def list_repetitions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(NMTRepetition)
        .where(
            NMTRepetition.user_id == user.id,
            NMTRepetition.completed == False,
            NMTRepetition.skipped == False,
        )
        .order_by(NMTRepetition.scheduled_date)
    )
    return q.scalars().all()


@router.patch("/repetitions/{rep_id}/complete")
async def complete_repetition(
    rep_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(NMTRepetition).where(
            NMTRepetition.id == rep_id, NMTRepetition.user_id == user.id
        )
    )
    rep = q.scalar_one_or_none()
    if not rep:
        raise HTTPException(404, "Повторення не знайдено")
    if rep.completed:
        raise HTTPException(400, "Повторення вже виконано")

    rep.completed = True
    rep.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "ok"}
