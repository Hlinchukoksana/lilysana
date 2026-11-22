"""
Unified launcher: starts both Aiogram bot (polling) and FastAPI (uvicorn) concurrently.
"""
import asyncio
import os
import logging
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import MenuButtonWebApp, WebAppInfo
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.main import app
from app.bot_handlers.start import router as start_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def run_bot(bot: Bot):
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start_router)

    # Set persistent Menu Button in Telegram
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🌸 Lilysana",
                web_app=WebAppInfo(url=settings.MINI_APP_URL),
            )
        )
        logger.info(f"✅ Menu button configured with URL: {settings.MINI_APP_URL}")
    except Exception as e:
        logger.warning(f"Could not set menu button: {e}")

    logger.info("🤖 Starting bot polling...")
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await bot.session.close()


async def run_api():
    port = int(os.environ.get("PORT", settings.PORT))
    logger.info(f"🌐 Starting Uvicorn API server on 0.0.0.0:{port}")
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    # Share bot instance with FastAPI app for reminders
    app.state.bot = bot

    logger.info(f"🌸 Lilysana Education v2.0 starting on port {settings.PORT}")
    logger.info(f"📱 Mini App URL: {settings.MINI_APP_URL}")
    logger.info(f"🔧 Dev mode: {settings.DEV_MODE}")

    await asyncio.gather(
        run_bot(bot),
        run_api(),
    )


if __name__ == "__main__":
    asyncio.run(main())
