# models/__init__.py — import all models so SQLAlchemy finds them
from app.models.user import User, UserSettings, LearningLimits, ActiveModules, BusySlot  # noqa
from app.models.nmt import NMTSubject, NMTTopic, NMTTest, TestResult, NMTRepetition  # noqa
from app.models.courses import Course, CourseSession  # noqa
from app.models.reminders import Reminder  # noqa
