from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class NMTSubject(Base):
    __tablename__ = "nmt_subjects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    is_optional = Column(Boolean, default=False)   # True for the 4th/extra subjects
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    topics = relationship("NMTTopic", back_populates="subject", cascade="all, delete-orphan", lazy="selectin")


class NMTTopic(Base):
    __tablename__ = "nmt_topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("nmt_subjects.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(300), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    subject = relationship("NMTSubject", back_populates="topics")
    tests = relationship("NMTTest", back_populates="topic", cascade="all, delete-orphan", lazy="selectin")


class NMTTest(Base):
    __tablename__ = "nmt_tests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("nmt_topics.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(300), nullable=False)
    url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    topic = relationship("NMTTopic", back_populates="tests")
    results = relationship("TestResult", back_populates="test", cascade="all, delete-orphan", order_by="TestResult.taken_at", lazy="selectin")


class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_id = Column(Integer, ForeignKey("nmt_tests.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    score_percent = Column(Float, nullable=False)   # 0.0 – 100.0
    taken_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    notes = Column(Text, nullable=True)

    test = relationship("NMTTest", back_populates="results")
    repetition = relationship("NMTRepetition", back_populates="result", uselist=False, cascade="all, delete-orphan", lazy="selectin")


class NMTRepetition(Base):
    """Scheduled repetition session linked to a test result."""
    __tablename__ = "nmt_repetitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    result_id = Column(Integer, ForeignKey("test_results.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    scheduled_date = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, default=90)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    skipped = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    result = relationship("TestResult", back_populates="repetition")


# ── Seed data helper ─────────────────────────────────────────────────────────

CORE_SUBJECTS = [
    {"name": "Українська мова", "display_order": 0},
    {"name": "Математика", "display_order": 1},
    {"name": "Історія України", "display_order": 2},
]

OPTIONAL_SUBJECTS = [
    "Англійська мова",
    "Біологія",
    "Хімія",
    "Географія",
    "Фізика",
    "Українська література",
]

SEED_TOPICS = {
    "Українська мова": [
        "Орфографія та пунктуація",
        "Синтаксис",
        "Морфологія",
        "Лексикологія та фразеологія",
        "Стилістика",
    ],
    "Математика": [
        "Алгебра та рівняння",
        "Геометрія",
        "Тригонометрія",
        "Теорія ймовірностей",
        "Похідні та інтеграли",
    ],
    "Історія України": [
        "Козацька доба",
        "Українська революція 1917–1921",
        "Радянська доба",
        "Незалежна Україна",
        "Новітня історія",
    ],
}
