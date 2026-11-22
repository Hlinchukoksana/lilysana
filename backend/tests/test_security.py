"""
Test security: initData verification logic.
"""
import pytest
import hashlib
import hmac
import json
import time

from app.api.auth import verify_telegram_init_data, extract_user_from_init_data

pytestmark = pytest.mark.asyncio


def _make_init_data(user_id: int, bot_token: str, age_seconds: int = 0) -> str:
    """Generate a valid Telegram initData string for testing."""
    auth_date = int(time.time()) - age_seconds
    user_json = json.dumps({"id": user_id, "first_name": "Test", "username": "testuser"})

    params = {
        "auth_date": str(auth_date),
        "user": user_json,
        "query_id": "test_query_123",
    }

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    params["hash"] = computed_hash
    return "&".join(f"{k}={v}" for k, v in params.items())


def test_valid_init_data_verifies():
    """Valid initData passes verification."""
    bot_token = "test:TOKEN123"
    init_data = _make_init_data(12345, bot_token)
    parsed = verify_telegram_init_data(init_data, bot_token)
    assert "user" in parsed
    assert "auth_date" in parsed


def test_tampered_init_data_rejected():
    """Modified hash is rejected."""
    bot_token = "test:TOKEN123"
    init_data = _make_init_data(12345, bot_token)
    # Tamper with the data
    tampered = init_data.replace("hash=", "hash=00") + "x"
    with pytest.raises(ValueError, match="hash"):
        verify_telegram_init_data(tampered, bot_token)


def test_wrong_bot_token_rejected():
    """initData with wrong bot token is rejected."""
    init_data = _make_init_data(12345, "real:TOKEN")
    with pytest.raises(ValueError):
        verify_telegram_init_data(init_data, "wrong:TOKEN")


def test_expired_init_data_rejected():
    """initData older than 1 hour is rejected."""
    bot_token = "test:TOKEN123"
    init_data = _make_init_data(12345, bot_token, age_seconds=3700)
    with pytest.raises(ValueError, match="expired"):
        verify_telegram_init_data(init_data, bot_token)


def test_missing_hash_rejected():
    """initData without hash is rejected."""
    with pytest.raises(ValueError, match="hash"):
        verify_telegram_init_data("user=test&auth_date=12345", "test:TOKEN")


def test_extract_user_id():
    """User ID is extracted from verified initData correctly."""
    import urllib.parse
    bot_token = "test:TOKEN123"
    init_data = _make_init_data(99887766, bot_token)
    parsed = verify_telegram_init_data(init_data, bot_token)
    user_id, first_name, username = extract_user_from_init_data(parsed)
    assert user_id == 99887766
    assert first_name == "Test"
    assert username == "testuser"
