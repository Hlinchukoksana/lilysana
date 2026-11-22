"""
Telegram initData verification per official Telegram docs.
HMAC-SHA256 based — never trusts client-provided user_id.
"""
import hashlib
import hmac
import json
import time
from urllib.parse import unquote, parse_qsl
from typing import Optional, Tuple
from fastapi import HTTPException, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from sqlalchemy import select


def verify_telegram_init_data(init_data: str, bot_token: str) -> dict:
    """
    Verifies Telegram WebApp initData string.
    Returns parsed data dict if valid, raises ValueError if invalid.
    Per: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise ValueError("Missing hash in initData")

    # Build data-check-string: sorted key=value pairs joined by \n
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    # HMAC-SHA256(data_check_string, HMAC-SHA256("WebAppData", bot_token))
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256,
    ).digest()

    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("initData hash mismatch — possible forgery")

    # Optional: check auth_date freshness (allow 1 hour)
    auth_date = int(parsed.get("auth_date", 0))
    if auth_date and (time.time() - auth_date) > 3600:
        raise ValueError("initData expired")

    return parsed


def extract_user_from_init_data(parsed: dict) -> Tuple[int, Optional[str], Optional[str]]:
    """Extract user_id, first_name, username from verified initData."""
    user_json = parsed.get("user", "{}")
    if isinstance(user_json, str):
        user_data = json.loads(unquote(user_json))
    else:
        user_data = user_json

    user_id = int(user_data.get("id", 0))
    first_name = user_data.get("first_name")
    username = user_data.get("username")
    return user_id, first_name, username


async def get_current_user(
    x_init_data: Optional[str] = Header(None, alias="X-Init-Data"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency: verifies initData and returns the authenticated User.
    In DEV_MODE with no initData, returns/creates a mock dev user.
    """
    if settings.DEV_MODE and not x_init_data:
        # Dev mode: use mock user
        user_id = settings.DEV_USER_ID
        q = await db.execute(select(User).where(User.id == user_id))
        user = q.scalar_one_or_none()
        if not user:
            user = User(id=user_id, first_name="Dev", username="dev_user")
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user

    if not x_init_data:
        raise HTTPException(status_code=401, detail="X-Init-Data header required")

    try:
        parsed = verify_telegram_init_data(x_init_data, settings.BOT_TOKEN)
        user_id, first_name, username = extract_user_from_init_data(parsed)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if not user_id:
        raise HTTPException(status_code=401, detail="Cannot extract user_id from initData")

    # Get or create user
    q = await db.execute(select(User).where(User.id == user_id))
    user = q.scalar_one_or_none()
    if not user:
        user = User(id=user_id, first_name=first_name, username=username)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user
