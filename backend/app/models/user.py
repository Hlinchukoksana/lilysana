from sqlalchemy import Column, BigInteger, String, Integer, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.database import Base


class LearningTimeChoice(str, enum.Enum):
    ONE_TO_TWO = "1-2"
    THREE_TO_FIVE = "3-5"
    FIVE_TO_EIGHT = "5-8"


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)  # Telegram user_id
    first_name = Column(String(100), nullable=True)
    username = Column(String(100), nullable=True)
    timezone = Column(String(50), default="Europe/Kyiv")
    learning_time_choice = Column(SAEnum(LearningTimeChoice), nullable=True)
    onboarded = Column(Boolean, default=False)
    mini_app_welcomed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    limits = relationship("LearningLimits", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    active_modules = relationship("ActiveModules", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    busy_slots = relationship("BusySlot", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    courses = relationship("Course", back_populates="user", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    reminder_before_min = Column(Integer, default=30)  # minutes before session
    reminders_enabled = Column(Boolean, default=True)
    nmt_reminders = Column(Boolean, default=True)
    schedule_change_notifications = Column(Boolean, default=True)
    study_days = Column(String(50), default="0,1,2,3,4")  # 0=Mon, 1=Tue, 2=Wed, etc.
    preferred_start_hour = Column(Integer, default=18)     # 18:00
    preferred_start_minute = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="settings")


class LearningLimits(Base):
    __tablename__ = "learning_limits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    nmt_hours_per_week = Column(Integer, default=6)       # weekly NMT limit
    course_hours_per_week = Column(Integer, default=4)    # weekly courses limit
    daily_limit_minutes = Column(Integer, default=120)    # max minutes/day total
    reserve_percent = Column(Integer, default=20)         # % of time left as buffer
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="limits")


class ActiveModules(Base):
    __tablename__ = "active_modules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    nmt_enabled = Column(Boolean, default=False)
    courses_enabled = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="active_modules")


class BusySlot(Base):
    """Recurring or one-off busy time blocks that scheduler must avoid."""
    __tablename__ = "busy_slots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    label = Column(String(200), nullable=True)
    day_of_week = Column(Integer, nullable=True)   # 0=Mon…6=Sun, None=one-off
    date = Column(DateTime(timezone=True), nullable=True)   # for one-off
    start_hour = Column(Integer, nullable=False)
    start_minute = Column(Integer, default=0)
    duration_minutes = Column(Integer, nullable=False)
    is_recurring = Column(Boolean, default=True)

    user = relationship("User", back_populates="busy_slots")
