from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime, timezone

from app.database import get_db
from app.api.auth import get_current_user
from app.models.user import (
    User, UserSettings, LearningLimits, ActiveModules, BusySlot, LearningTimeChoice
)
from app.models.nmt import NMTSubject, NMTTopic, CORE_SUBJECTS, OPTIONAL_SUBJECTS, SEED_TOPICS

router = APIRouter(prefix="/api/users", tags=["users"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    first_name: Optional[str]
    username: Optional[str]
    timezone: str
    learning_time_choice: Optional[str]
    onboarded: bool
    mini_app_welcomed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class OnboardingIn(BaseModel):
    learning_time_choice: LearningTimeChoice


class LimitsIn(BaseModel):
    nmt_hours_per_week: Optional[int] = None
    course_hours_per_week: Optional[int] = None
    daily_limit_minutes: Optional[int] = None
    reserve_percent: Optional[int] = None

    @field_validator("nmt_hours_per_week", "course_hours_per_week")
    @classmethod
    def validate_hours(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Hours per week must be 0–100")
        return v

    @field_validator("daily_limit_minutes")
    @classmethod
    def validate_daily(cls, v):
        if v is not None and (v < 30 or v > 720):
            raise ValueError("Daily limit must be 30–720 minutes")
        return v

    @field_validator("reserve_percent")
    @classmethod
    def validate_reserve(cls, v):
        if v is not None and (v < 0 or v > 50):
            raise ValueError("Reserve must be 0–50%")
        return v


class LimitsOut(BaseModel):
    nmt_hours_per_week: int
    course_hours_per_week: int
    daily_limit_minutes: int
    reserve_percent: int

    class Config:
        from_attributes = True


class SettingsIn(BaseModel):
    reminder_before_min: Optional[int] = None
    reminders_enabled: Optional[bool] = None
    nmt_reminders: Optional[bool] = None
    schedule_change_notifications: Optional[bool] = None
    timezone: Optional[str] = None
    study_days: Optional[str] = None
    preferred_start_hour: Optional[int] = None
    preferred_start_minute: Optional[int] = None


class SettingsOut(BaseModel):
    reminder_before_min: int
    reminders_enabled: bool
    nmt_reminders: bool
    schedule_change_notifications: bool
    study_days: Optional[str] = "0,1,2,3,4"
    preferred_start_hour: Optional[int] = 18
    preferred_start_minute: Optional[int] = 0

    class Config:
        from_attributes = True


class BusySlotIn(BaseModel):
    label: Optional[str] = None
    day_of_week: Optional[int] = None  # 0=Mon..6=Sun
    start_hour: int
    start_minute: int = 0
    duration_minutes: int
    is_recurring: bool = True


class BusySlotOut(BaseModel):
    id: int
    label: Optional[str]
    day_of_week: Optional[int]
    start_hour: int
    start_minute: int
    duration_minutes: int
    is_recurring: bool

    class Config:
        from_attributes = True


class ActiveModulesIn(BaseModel):
    nmt_enabled: Optional[bool] = None
    courses_enabled: Optional[bool] = None


class ActiveModulesOut(BaseModel):
    nmt_enabled: bool
    courses_enabled: bool

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.post("/me/onboarding")
async def complete_onboarding(
    data: OnboardingIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Complete first-run onboarding: save learning time choice and seed NMT subjects."""
    user.learning_time_choice = data.learning_time_choice
    user.onboarded = True

    # Create defaults if they don't exist
    if not user.limits:
        limits = LearningLimits(user_id=user.id)
        db.add(limits)
        user.limits = limits

    if not user.settings:
        s = UserSettings(user_id=user.id)
        db.add(s)
        user.settings = s

    if not user.active_modules:
        am = ActiveModules(user_id=user.id)
        db.add(am)
        user.active_modules = am

    # Seed core NMT subjects if none exist
    existing_q = await db.execute(
        select(NMTSubject).where(NMTSubject.user_id == user.id)
    )
    if not existing_q.scalars().first():
        for subj_data in CORE_SUBJECTS:
            subj = NMTSubject(
                user_id=user.id,
                name=subj_data["name"],
                display_order=subj_data["display_order"],
                is_optional=False,
            )
            db.add(subj)
            await db.flush()
            # Seed topics
            for topic_name in SEED_TOPICS.get(subj_data["name"], []):
                topic = NMTTopic(
                    subject_id=subj.id,
                    user_id=user.id,
                    name=topic_name,
                )
                db.add(topic)

        # Add 4th subject placeholder (Англійська мова by default)
        fourth = NMTSubject(
            user_id=user.id,
            name="Англійська мова",
            display_order=3,
            is_optional=True,
        )
        db.add(fourth)

    await db.commit()
    return {"status": "ok", "message": "Налаштування збережено!"}


@router.post("/me/welcome-seen")
async def mark_welcome_seen(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.mini_app_welcomed = True
    await db.commit()
    return {"status": "ok"}


@router.get("/me/limits", response_model=LimitsOut)
async def get_limits(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user.limits:
        limits = LearningLimits(user_id=user.id)
        db.add(limits)
        await db.commit()
        await db.refresh(limits)
        return limits
    return user.limits


@router.put("/me/limits", response_model=LimitsOut)
async def update_limits(
    data: LimitsIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(select(LearningLimits).where(LearningLimits.user_id == user.id))
    limits = q.scalar_one_or_none()
    if not limits:
        limits = LearningLimits(user_id=user.id)
        db.add(limits)

    for field, val in data.model_dump(exclude_none=True).items():
        setattr(limits, field, val)

    limits.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(limits)
    return limits


@router.get("/me/settings", response_model=SettingsOut)
async def get_settings(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user.settings:
        s = UserSettings(user_id=user.id)
        db.add(s)
        await db.commit()
        await db.refresh(s)
        return s
    return user.settings


@router.put("/me/settings", response_model=SettingsOut)
async def update_settings(
    data: SettingsIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(select(UserSettings).where(UserSettings.user_id == user.id))
    settings = q.scalar_one_or_none()
    if not settings:
        settings = UserSettings(user_id=user.id)
        db.add(settings)

    for field, val in data.model_dump(exclude_none=True).items():
        if field == "timezone":
            user.timezone = val
        else:
            setattr(settings, field, val)

    await db.commit()
    await db.refresh(settings)
    return settings


@router.get("/me/modules", response_model=ActiveModulesOut)
async def get_modules(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user.active_modules:
        am = ActiveModules(user_id=user.id)
        db.add(am)
        await db.commit()
        await db.refresh(am)
        return am
    return user.active_modules


@router.put("/me/modules", response_model=ActiveModulesOut)
async def update_modules(
    data: ActiveModulesIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(select(ActiveModules).where(ActiveModules.user_id == user.id))
    am = q.scalar_one_or_none()
    if not am:
        am = ActiveModules(user_id=user.id)
        db.add(am)

    for field, val in data.model_dump(exclude_none=True).items():
        setattr(am, field, val)

    am.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(am)
    return am


# ── Busy Slots Endpoints ──────────────────────────────────────────────────────

@router.get("/me/busy-slots", response_model=List[BusySlotOut])
async def get_busy_slots(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(select(BusySlot).where(BusySlot.user_id == user.id))
    return q.scalars().all()


@router.post("/me/busy-slots", response_model=BusySlotOut)
async def create_busy_slot(
    data: BusySlotIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    slot = BusySlot(
        user_id=user.id,
        label=data.label,
        day_of_week=data.day_of_week,
        start_hour=data.start_hour,
        start_minute=data.start_minute,
        duration_minutes=data.duration_minutes,
        is_recurring=data.is_recurring,
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return slot


@router.delete("/me/busy-slots/{slot_id}")
async def delete_busy_slot(
    slot_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = await db.execute(
        select(BusySlot).where(BusySlot.id == slot_id, BusySlot.user_id == user.id)
    )
    slot = q.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Слот не знайдено")
    await db.delete(slot)
    await db.commit()
    return {"status": "ok"}
