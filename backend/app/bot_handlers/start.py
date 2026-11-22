"""
Telegram Bot handlers for the /start command and onboarding flow.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.user import User, LearningTimeChoice, LearningLimits, UserSettings, ActiveModules
from app.config import settings

router = Router()


class OnboardingStates(StatesGroup):
    waiting_for_time_choice = State()


def get_time_choice_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏱ 1–2 години", callback_data="time:1-2")],
        [InlineKeyboardButton(text="📚 3–5 годин", callback_data="time:3-5")],
        [InlineKeyboardButton(text="🎯 5–8 годин", callback_data="time:5-8")],
    ])


def get_open_app_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🌸 Відкрити Lilysana",
            web_app=WebAppInfo(url=settings.MINI_APP_URL),
        )],
    ])


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    async with AsyncSessionLocal() as db:
        user_id = message.from_user.id
        q = await db.execute(select(User).where(User.id == user_id))
        user = q.scalar_one_or_none()

        if user and user.onboarded:
            # Already onboarded — just open the app
            await message.answer(
                f"З поверненням, {user.first_name or 'друже'}! 🌸\n\n"
                "Натисни кнопку нижче, щоб відкрити Lilysana Education.",
                reply_markup=get_open_app_keyboard(),
            )
            return

        if not user:
            user = User(
                id=user_id,
                first_name=message.from_user.first_name,
                username=message.from_user.username,
            )
            db.add(user)
            await db.commit()

    await message.answer(
        "👋 Привіт! Я Lilysana Education — твій помічник у навчанні.\n\n"
        "Перш ніж розпочати, скажи: "
        "<b>скільки часу на день ти готовий(-а) приділяти навчанню?</b>\n\n"
        "Це допоможе скласти зручний розклад 📅",
        reply_markup=get_time_choice_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(OnboardingStates.waiting_for_time_choice)


@router.callback_query(F.data.startswith("time:"))
async def handle_time_choice(callback: CallbackQuery, state: FSMContext):
    choice_raw = callback.data.split(":")[1]
    choice_map = {
        "1-2": LearningTimeChoice.ONE_TO_TWO,
        "3-5": LearningTimeChoice.THREE_TO_FIVE,
        "5-8": LearningTimeChoice.FIVE_TO_EIGHT,
    }
    choice = choice_map.get(choice_raw)
    if not choice:
        await callback.answer("Невірний вибір")
        return

    async with AsyncSessionLocal() as db:
        user_id = callback.from_user.id
        q = await db.execute(select(User).where(User.id == user_id))
        user = q.scalar_one_or_none()

        if not user:
            user = User(
                id=user_id,
                first_name=callback.from_user.first_name,
                username=callback.from_user.username,
            )
            db.add(user)

        user.learning_time_choice = choice
        user.onboarded = True

        # Create defaults
        existing_limits_q = await db.execute(select(LearningLimits).where(LearningLimits.user_id == user_id))
        if not existing_limits_q.scalar_one_or_none():
            db.add(LearningLimits(user_id=user_id))

        existing_settings_q = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        if not existing_settings_q.scalar_one_or_none():
            db.add(UserSettings(user_id=user_id))

        existing_modules_q = await db.execute(select(ActiveModules).where(ActiveModules.user_id == user_id))
        if not existing_modules_q.scalar_one_or_none():
            db.add(ActiveModules(user_id=user_id))

        await db.commit()

    choice_labels = {
        "1-2": "1–2 години",
        "3-5": "3–5 годин",
        "5-8": "5–8 годин",
    }

    await callback.message.edit_text(
        f"✅ Чудово! Запам'ятала: <b>{choice_labels[choice_raw]}</b> на день.\n\n"
        "Тепер відкрий Lilysana Education, щоб обрати модулі та розпочати навчання! 🚀",
        reply_markup=get_open_app_keyboard(),
        parse_mode="HTML",
    )
    await state.clear()
    await callback.answer()


@router.message()
async def handle_any_message(message: Message):
    """Fallback handler for any message — always returns a fresh Mini App button."""
    await message.answer(
        "🌸 <b>Lilysana Education</b> готова до роботи!\n\n"
        "Натисни кнопку нижче, щоб відкрити застосунок:",
        reply_markup=get_open_app_keyboard(),
        parse_mode="HTML",
    )
