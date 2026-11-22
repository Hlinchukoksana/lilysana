"""
FastAPI main application.
Mounts all routers, sets up CORS for Mini App, initializes DB and bot.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import init_db
from app.api import users, nmt, courses, schedule, statistics
from app.services.reminder_svc import init_reminder_service, restore_reminders_from_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🌸 Starting Lilysana Education backend...")
    await init_db()

    # Start scheduler
    scheduler.start()
    logger.info("APScheduler started")

    # Init bot for reminders (lazy — bot instance set by run.py)
    bot_instance = getattr(app.state, "bot", None)
    init_reminder_service(bot_instance, scheduler)

    # Restore pending reminders from DB
    await restore_reminders_from_db()

    logger.info("✅ Backend ready")
    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("👋 Backend shutting down")


app = FastAPI(
    title="Lilysana Education API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow Telegram Mini App origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(users.router)
app.include_router(nmt.router)
app.include_router(courses.router)
app.include_router(schedule.router)
app.include_router(statistics.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "service": "Lilysana Education"}


@app.get("/api/optional-subjects")
async def get_optional_subjects():
    """Return available optional NMT subjects for 4th subject selection."""
    from app.models.nmt import OPTIONAL_SUBJECTS
    return {"subjects": OPTIONAL_SUBJECTS}


# Serve Mini App static files (mounted after all API routes)
from pathlib import Path
_frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
