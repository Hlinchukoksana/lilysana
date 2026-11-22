"""
Tests 11–14: NMT topics, tests, results, repetition logic.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _setup(client: AsyncClient):
    """Helper: onboard user and get first subject/topic."""
    await client.post("/api/users/me/onboarding", json={"learning_time_choice": "3-5"})
    subjects_resp = await client.get("/api/nmt/subjects")
    subjects = subjects_resp.json()
    assert len(subjects) >= 3
    subject_id = subjects[0]["id"]

    topics_resp = await client.get(f"/api/nmt/subjects/{subject_id}/topics")
    topics = topics_resp.json()
    assert len(topics) >= 1
    topic_id = topics[0]["id"]
    return subject_id, topic_id


async def test_11_add_nmt_topic(client: AsyncClient):
    """Test 11: Adding a NMT topic."""
    subject_id, _ = await _setup(client)
    resp = await client.post(
        f"/api/nmt/subjects/{subject_id}/topics",
        json={"name": "Нова тема тест"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Нова тема тест"
    assert data["subject_id"] == subject_id


async def test_12_save_test_result(client: AsyncClient):
    """Test 12: Saving a test result."""
    _, topic_id = await _setup(client)
    test_resp = await client.post(
        f"/api/nmt/topics/{topic_id}/tests",
        json={"name": "Контрольний тест", "url": "https://example.com/test"},
    )
    assert test_resp.status_code == 201
    test_id = test_resp.json()["id"]

    result_resp = await client.post(
        f"/api/nmt/tests/{test_id}/results",
        json={"score_percent": 65.0},
    )
    assert result_resp.status_code == 200
    data = result_resp.json()
    assert data["result"]["score_percent"] == 65.0
    assert "recommendation" in data


async def test_13_multiple_test_results_preserved(client: AsyncClient):
    """Test 13: Multiple results are all preserved (not overwritten)."""
    _, topic_id = await _setup(client)
    test_resp = await client.post(
        f"/api/nmt/topics/{topic_id}/tests",
        json={"name": "Тест повторний"},
    )
    test_id = test_resp.json()["id"]

    scores = [45.0, 72.0, 88.0]
    for score in scores:
        await client.post(f"/api/nmt/tests/{test_id}/results", json={"score_percent": score})

    history_resp = await client.get(f"/api/nmt/tests/{test_id}/results")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert history["attempts"] == 3
    assert history["first_score"] == 45.0
    assert history["last_score"] == 88.0
    assert history["best_score"] == 88.0
    assert len(history["results"]) == 3


async def test_14_repetition_recommendation_logic(client: AsyncClient):
    """Test 14: Repetition recommendations follow threshold rules."""
    _, topic_id = await _setup(client)
    test_resp = await client.post(
        f"/api/nmt/topics/{topic_id}/tests",
        json={"name": "Тест рекомендації"},
    )
    test_id = test_resp.json()["id"]

    # Low score → category "low"
    r1 = await client.post(f"/api/nmt/tests/{test_id}/results", json={"score_percent": 55.0})
    assert r1.json()["recommendation"]["category"] == "low"
    assert r1.json()["recommendation"]["days_until_review"] == 3

    # Mid score → category "mid"
    r2 = await client.post(f"/api/nmt/tests/{test_id}/results", json={"score_percent": 80.0})
    assert r2.json()["recommendation"]["category"] == "mid"
    assert r2.json()["recommendation"]["days_until_review"] is not None

    # High score → category "high", user choice required
    r3 = await client.post(f"/api/nmt/tests/{test_id}/results", json={"score_percent": 97.0})
    assert r3.json()["recommendation"]["category"] == "high"
    assert r3.json()["recommendation"]["user_choice_required"] == True
    assert len(r3.json()["recommendation"]["choices"]) == 2


async def test_schedule_repetition(client: AsyncClient):
    """Scheduling a repetition creates a future date record."""
    _, topic_id = await _setup(client)
    test_resp = await client.post(
        f"/api/nmt/topics/{topic_id}/tests",
        json={"name": "Тест для повторення"},
    )
    test_id = test_resp.json()["id"]

    result_resp = await client.post(
        f"/api/nmt/tests/{test_id}/results",
        json={"score_percent": 60.0},
    )
    result_id = result_resp.json()["result"]["id"]

    rep_resp = await client.post(
        f"/api/nmt/results/{result_id}/schedule-repetition",
        json={},
    )
    assert rep_resp.status_code == 200
    data = rep_resp.json()
    assert data["completed"] == False
    assert "scheduled_date" in data


async def test_nmt_access_control(client: AsyncClient):
    """Cannot access topics from another user's subject."""
    subject_id, _ = await _setup(client)
    # Try accessing a subject ID that doesn't belong to this user
    resp = await client.get("/api/nmt/subjects/99999/topics")
    assert resp.status_code == 404
