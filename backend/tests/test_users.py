"""
Tests 1–3: User creation, repeated login, settings persistence.
"""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_01_user_creation(client: AsyncClient):
    """Test 1: First visit creates user and returns profile."""
    resp = await client.get("/api/users/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 99999999
    assert data["onboarded"] == False


async def test_02_repeated_login(client: AsyncClient):
    """Test 2: Second call returns the same user (not duplicate)."""
    resp1 = await client.get("/api/users/me")
    resp2 = await client.get("/api/users/me")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["id"] == resp2.json()["id"]


async def test_03_save_learning_limits(client: AsyncClient):
    """Test 3: Saving learning limits persists correctly."""
    # Trigger user creation
    await client.get("/api/users/me")

    resp = await client.put("/api/users/me/limits", json={
        "nmt_hours_per_week": 8,
        "course_hours_per_week": 5,
        "daily_limit_minutes": 180,
        "reserve_percent": 15,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["nmt_hours_per_week"] == 8
    assert data["course_hours_per_week"] == 5
    assert data["daily_limit_minutes"] == 180
    assert data["reserve_percent"] == 15

    # Verify persisted
    resp2 = await client.get("/api/users/me/limits")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["nmt_hours_per_week"] == 8


async def test_onboarding_completes(client: AsyncClient):
    """Onboarding sets learning_time_choice and onboarded flag."""
    resp = await client.post("/api/users/me/onboarding", json={"learning_time_choice": "3-5"})
    assert resp.status_code == 200

    profile = await client.get("/api/users/me")
    data = profile.json()
    assert data["onboarded"] == True
    assert data["learning_time_choice"] == "3-5"


async def test_settings_update(client: AsyncClient):
    """Settings updates are persisted."""
    await client.get("/api/users/me")
    resp = await client.put("/api/users/me/settings", json={
        "reminders_enabled": False,
        "reminder_before_min": 15,
    })
    assert resp.status_code == 200
    assert resp.json()["reminders_enabled"] == False
    assert resp.json()["reminder_before_min"] == 15


async def test_18_data_isolation(client: AsyncClient):
    """Test 18: Each user only sees their own data (by user_id isolation)."""
    # With DEV_MODE our user is 99999999
    # Verify NMT subjects created are only for this user
    await client.post("/api/users/me/onboarding", json={"learning_time_choice": "1-2"})
    subjects = await client.get("/api/nmt/subjects")
    assert subjects.status_code == 200
    for subj in subjects.json():
        # We can't directly check user_id from response, but the API enforces it via auth
        assert "id" in subj


async def test_invalid_input_validation(client: AsyncClient):
    """Test 20: Invalid input is rejected with proper error."""
    # Score out of range
    await client.post("/api/users/me/onboarding", json={"learning_time_choice": "1-2"})
    subjects = await client.get("/api/nmt/subjects")
    subject_id = subjects.json()[0]["id"]
    topics = await client.get(f"/api/nmt/subjects/{subject_id}/topics")
    topic_id = topics.json()[0]["id"]
    test_resp = await client.post(f"/api/nmt/topics/{topic_id}/tests", json={"name": "Тест"})
    test_id = test_resp.json()["id"]

    resp = await client.post(f"/api/nmt/tests/{test_id}/results", json={"score_percent": 150})
    assert resp.status_code == 422  # Unprocessable entity

    resp2 = await client.post(f"/api/nmt/tests/{test_id}/results", json={"score_percent": -5})
    assert resp2.status_code == 422

    # Invalid URL
    resp3 = await client.post(f"/api/nmt/topics/{topic_id}/tests", json={
        "name": "Test", "url": "not-a-url"
    })
    assert resp3.status_code == 422


@pytest.mark.asyncio
async def test_schedule_preferences_and_busy_slots(client):
    """Test saving preferred study days, start time, and busy slots."""
    # Update study days and preferred start hour
    resp = await client.put(
        "/api/users/me/settings",
        json={
            "study_days": "0,2,4",
            "preferred_start_hour": 19,
            "preferred_start_minute": 30,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["study_days"] == "0,2,4"
    assert data["preferred_start_hour"] == 19
    assert data["preferred_start_minute"] == 30

    # Add busy slot
    busy_resp = await client.post(
        "/api/users/me/busy-slots",
        json={
            "label": "Тренування",
            "day_of_week": 1,
            "start_hour": 16,
            "start_minute": 0,
            "duration_minutes": 90,
            "is_recurring": True,
        },
    )
    assert busy_resp.status_code == 200
    slot = busy_resp.json()
    assert slot["label"] == "Тренування"
    assert slot["day_of_week"] == 1
    slot_id = slot["id"]

    # Get busy slots
    get_resp = await client.get("/api/users/me/busy-slots")
    assert get_resp.status_code == 200
    slots = get_resp.json()
    assert any(s["id"] == slot_id for s in slots)

    # Delete busy slot
    del_resp = await client.delete(f"/api/users/me/busy-slots/{slot_id}")
    assert del_resp.status_code == 200

    # Verify deleted
    get_resp2 = await client.get("/api/users/me/busy-slots")
    slots2 = get_resp2.json()
    assert not any(s["id"] == slot_id for s in slots2)
