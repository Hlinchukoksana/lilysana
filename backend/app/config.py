from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    BOT_TOKEN: str = "test_token"
    SECRET_KEY: str = "dev_secret_key_change_in_production"
    DATABASE_URL: str = "sqlite+aiosqlite:///./lilysana.db"
    MINI_APP_URL: str = "http://localhost:3000"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEV_MODE: bool = False
    DEV_USER_ID: int = 12345678
    WEBHOOK_URL: Optional[str] = None
    DEFAULT_TIMEZONE: str = "Europe/Kyiv"

    # Spaced repetition thresholds (easily configurable per spec)
    THRESHOLD_LOW: int = 70       # <= this → review in ~3 days
    THRESHOLD_MID: int = 94       # <= this → review in 7-14 days
    # above THRESHOLD_MID → user chooses 14-21 days or sooner

    REVIEW_DAYS_LOW: int = 3
    REVIEW_DURATION_LOW_MIN: int = 90
    REVIEW_DAYS_MID_MIN: int = 7
    REVIEW_DAYS_MID_MAX: int = 14
    REVIEW_DAYS_HIGH_MIN: int = 14
    REVIEW_DAYS_HIGH_MAX: int = 21

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
