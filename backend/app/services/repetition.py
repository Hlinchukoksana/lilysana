"""
Spaced repetition recommendation logic.
Thresholds are config-driven per spec.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.config import settings


class RepetitionRecommendation:
    def __init__(
        self,
        category: str,              # "low" | "mid" | "high"
        message: str,
        days_until_review: Optional[int],
        duration_minutes: Optional[int],
        user_choice_required: bool = False,
        choices: Optional[list] = None,
    ):
        self.category = category
        self.message = message
        self.days_until_review = days_until_review
        self.duration_minutes = duration_minutes
        self.user_choice_required = user_choice_required
        self.choices = choices or []

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "message": self.message,
            "days_until_review": self.days_until_review,
            "duration_minutes": self.duration_minutes,
            "user_choice_required": self.user_choice_required,
            "choices": self.choices,
        }


def get_repetition_recommendation(score_percent: float) -> RepetitionRecommendation:
    """
    Returns a recommendation based on the test score.
    Uses config thresholds — not hardcoded values.
    """
    if score_percent <= settings.THRESHOLD_LOW:
        return RepetitionRecommendation(
            category="low",
            message=(
                "Схоже, цю тему варто ще трохи закріпити. "
                "Пропонуємо виділити час на повторення матеріалу та повторне проходження тесту."
            ),
            days_until_review=settings.REVIEW_DAYS_LOW,
            duration_minutes=settings.REVIEW_DURATION_LOW_MIN,
        )
    elif score_percent <= settings.THRESHOLD_MID:
        days = (settings.REVIEW_DAYS_MID_MIN + settings.REVIEW_DAYS_MID_MAX) // 2
        return RepetitionRecommendation(
            category="mid",
            message=(
                "Чудовий результат! Так тримати. "
                "Пропонуємо повторити тему пізніше, щоб закріпити знання."
            ),
            days_until_review=days,
            duration_minutes=60,
        )
    else:
        return RepetitionRecommendation(
            category="high",
            message=(
                "Твій результат уже на дуже високому рівні! Як бажаєш продовжити?"
            ),
            days_until_review=None,
            duration_minutes=45,
            user_choice_required=True,
            choices=[
                {
                    "id": "regular",
                    "label": "Перейти до регулярного повторення раз на 2–3 тижні",
                    "days": settings.REVIEW_DAYS_HIGH_MIN,
                },
                {
                    "id": "practice",
                    "label": "Продовжувати практику, прагнучи 100%",
                    "days": 3,
                },
            ],
        )


def calculate_repetition_date(
    recommendation: RepetitionRecommendation,
    choice_id: Optional[str] = None,
    reference_date: Optional[datetime] = None,
) -> datetime:
    """Calculate the actual date for a repetition session."""
    base = reference_date or datetime.now(timezone.utc)

    if recommendation.user_choice_required and choice_id:
        for c in recommendation.choices:
            if c["id"] == choice_id:
                return base + timedelta(days=c["days"])
        # Fallback: use min days
        return base + timedelta(days=settings.REVIEW_DAYS_HIGH_MIN)

    days = recommendation.days_until_review or settings.REVIEW_DAYS_LOW
    return base + timedelta(days=days)
