from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.database import Base


class ReminderType(str, enum.Enum):
    SESSION_BEFORE = "session_before"
    NMT_REPETITION = "nmt_repetition"
    SCHEDULE_CHANGE = "schedule_change"
    CUSTOM = "custom"


class ReminderStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    reminder_type = Column(SAEnum(ReminderType), nullable=False)
    fire_at = Column(DateTime(timezone=True), nullable=False)       # UTC time to send
    message_text = Column(String(1000), nullable=False)
    status = Column(SAEnum(ReminderStatus), default=ReminderStatus.PENDING)
    reference_id = Column(Integer, nullable=True)   # e.g., session_id or repetition_id
    reference_type = Column(String(50), nullable=True)   # "course_session" | "nmt_repetition"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    sent_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="reminders")
