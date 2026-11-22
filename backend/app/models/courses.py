from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(300), nullable=False)
    url = Column(Text, nullable=True)
    total_hours = Column(Float, nullable=False)          # estimated total duration
    hours_per_week = Column(Float, nullable=False, default=4.0)
    deadline = Column(DateTime(timezone=True), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Manual progress override (what % of content is actually covered)
    manual_progress_percent = Column(Float, nullable=True)

    user = relationship("User", back_populates="courses")
    sessions = relationship("CourseSession", back_populates="course", cascade="all, delete-orphan", order_by="CourseSession.scheduled_at", lazy="selectin")


class CourseSession(Base):
    """An individual planned study session for a course."""
    __tablename__ = "course_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    planned_minutes = Column(Integer, nullable=False)
    actual_minutes = Column(Integer, nullable=True)
    is_completed = Column(Boolean, default=False)
    is_missed = Column(Boolean, default=False)
    is_rescheduled = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    course = relationship("Course", back_populates="sessions")
