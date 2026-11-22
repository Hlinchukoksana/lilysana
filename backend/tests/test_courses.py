"""
Tests 4–10, 15: Course creation, scheduling, limits, deadline, session completion, rescheduling.
"""
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _onboard(client: AsyncClient):
    await client.get("/api/users/me")
    await client.post("/api/users/me/onboarding", json={"learning_time_choice": "3-5"})
    await client.put("/api/users/me/limits", json={
        "nmt_hours_per_week": 6,
        "course_hours_per_week": 4,
        "daily_limit_minutes": 120,
        "reserve_percent": 20,
    })


async def test_04_add_course(client: AsyncClient):
    """Test 4: Adding a course."""
    await _onboard(client)
    resp = await client.post("/api/courses", json={
        "name": "Python для початківців",
        "url": "https://prometheus.org.ua/course/python",
        "total_hours": 12.0,
        "hours_per_week": 4.0,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Python для початківців"
    assert data["total_hours"] == 12.0


async def test_05_generate_schedule(client: AsyncClient):
    """Test 5: Generating a schedule creates sessions."""
    await _onboard(client)
    course_resp = await client.post("/api/courses", json={
        "name": "Курс з математики",
        "total_hours": 8.0,
        "hours_per_week": 4.0,
    })
    course_id = course_resp.json()["id"]

    sched_resp = await client.post(f"/api/courses/{course_id}/generate-schedule")
    assert sched_resp.status_code == 200
    data = sched_resp.json()
    assert data["sessions_created"] > 0
    assert len(data["sessions"]) > 0

    # All sessions in the future
    now = datetime.now(timezone.utc)
    for s in data["sessions"]:
        sched_at = datetime.fromisoformat(s["scheduled_at"])
        assert sched_at > now


async def test_06_schedule_respects_weekly_limits(client: AsyncClient):
    """Test 6: Schedule never exceeds weekly course limit."""
    await _onboard(client)
    # Set a small weekly limit
    await client.put("/api/users/me/limits", json={
        "course_hours_per_week": 2,
        "daily_limit_minutes": 120,
        "reserve_percent": 0,
    })
    course_resp = await client.post("/api/courses", json={
        "name": "Обмежений курс",
        "total_hours": 20.0,
        "hours_per_week": 2.0,
    })
    course_id = course_resp.json()["id"]

    sched_resp = await client.post(f"/api/courses/{course_id}/generate-schedule")
    sessions = sched_resp.json()["sessions"]

    # Group sessions by week and check each week <= 120 min
    from collections import defaultdict
    week_minutes = defaultdict(int)
    for s in sessions:
        dt = datetime.fromisoformat(s["scheduled_at"])
        week_key = dt.isocalendar()[:2]  # (year, week)
        week_minutes[week_key] += s["planned_minutes"]

    for week, total in week_minutes.items():
        assert total <= 120 + 5, f"Week {week} has {total} min, exceeds 120 min limit"


async def test_07_deadline_handling(client: AsyncClient):
    """Test 7: Deadline too close returns a warning."""
    await _onboard(client)
    # Deadline in 2 days with large course
    deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    course_resp = await client.post("/api/courses", json={
        "name": "Курс з дедлайном",
        "total_hours": 50.0,
        "hours_per_week": 4.0,
        "deadline": deadline,
    })
    course_id = course_resp.json()["id"]

    sched_resp = await client.post(f"/api/courses/{course_id}/generate-schedule")
    data = sched_resp.json()
    # With 2-day deadline and 50h course, warning should be present
    assert data["warning"] is not None
    assert "Увага" in data["warning"]


async def test_08_complete_session(client: AsyncClient):
    """Test 8: Marking a session as complete."""
    await _onboard(client)
    course_resp = await client.post("/api/courses", json={
        "name": "Завершений курс",
        "total_hours": 4.0,
        "hours_per_week": 4.0,
    })
    course_id = course_resp.json()["id"]
    await client.post(f"/api/courses/{course_id}/generate-schedule")

    sessions_resp = await client.get(f"/api/courses/{course_id}/sessions")
    sessions = sessions_resp.json()
    assert len(sessions) > 0
    session_id = sessions[0]["id"]

    complete_resp = await client.patch(
        f"/api/courses/sessions/{session_id}/complete",
        json={"actual_minutes": 45},
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["is_completed"] == True
    assert complete_resp.json()["actual_minutes"] == 45


async def test_09_actual_time_change(client: AsyncClient):
    """Test 9: Actual minutes can differ from planned."""
    await _onboard(client)
    course_resp = await client.post("/api/courses", json={
        "name": "Курс з часом",
        "total_hours": 4.0,
        "hours_per_week": 4.0,
    })
    course_id = course_resp.json()["id"]
    await client.post(f"/api/courses/{course_id}/generate-schedule")

    sessions_resp = await client.get(f"/api/courses/{course_id}/sessions")
    session_id = sessions_resp.json()[0]["id"]
    planned = sessions_resp.json()[0]["planned_minutes"]

    # Complete with different actual time
    actual = planned + 20
    complete_resp = await client.patch(
        f"/api/courses/sessions/{session_id}/complete",
        json={"actual_minutes": actual},
    )
    assert complete_resp.json()["actual_minutes"] == actual
    assert complete_resp.json()["planned_minutes"] == planned


async def test_10_progress_calculation(client: AsyncClient):
    """Test 10: Progress updates correctly after session completion."""
    await _onboard(client)
    course_resp = await client.post("/api/courses", json={
        "name": "Прогрес курс",
        "total_hours": 2.0,
        "hours_per_week": 4.0,
    })
    course_id = course_resp.json()["id"]
    await client.post(f"/api/courses/{course_id}/generate-schedule")

    sessions_resp = await client.get(f"/api/courses/{course_id}/sessions")
    sessions = sessions_resp.json()

    # Initial progress = 0
    prog1 = await client.get(f"/api/courses/{course_id}/progress")
    assert prog1.json()["completed_sessions"] == 0

    # Complete first session
    await client.patch(
        f"/api/courses/sessions/{sessions[0]['id']}/complete",
        json={},
    )

    prog2 = await client.get(f"/api/courses/{course_id}/progress")
    assert prog2.json()["completed_sessions"] == 1
    assert prog2.json()["time_progress_percent"] > 0

    # Double-completion rejected
    double_resp = await client.patch(
        f"/api/courses/sessions/{sessions[0]['id']}/complete",
        json={},
    )
    assert double_resp.status_code == 400


async def test_15_reschedule_missed_session(client: AsyncClient):
    """Test 15: Rescheduling a missed session."""
    await _onboard(client)
    course_resp = await client.post("/api/courses", json={
        "name": "Курс перенесення",
        "total_hours": 2.0,
        "hours_per_week": 4.0,
    })
    course_id = course_resp.json()["id"]
    await client.post(f"/api/courses/{course_id}/generate-schedule")

    sessions_resp = await client.get(f"/api/courses/{course_id}/sessions")
    session_id = sessions_resp.json()[0]["id"]

    # Mark missed
    await client.patch(f"/api/courses/sessions/{session_id}/mark-missed")

    # Reschedule to future
    new_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    reschedule_resp = await client.patch(
        f"/api/courses/sessions/{session_id}/reschedule",
        params={"new_date": new_date},
    )
    assert reschedule_resp.status_code == 200
    assert reschedule_resp.json()["is_missed"] == False
    assert reschedule_resp.json()["is_rescheduled"] == True


async def test_no_past_scheduling(client: AsyncClient):
    """Sessions must never be scheduled in the past."""
    await _onboard(client)
    course_resp = await client.post("/api/courses", json={
        "name": "Тест минуле",
        "total_hours": 4.0,
        "hours_per_week": 4.0,
    })
    course_id = course_resp.json()["id"]
    sched_resp = await client.post(f"/api/courses/{course_id}/generate-schedule")
    sessions = sched_resp.json()["sessions"]

    now = datetime.now(timezone.utc)
    for s in sessions:
        sched_at = datetime.fromisoformat(s["scheduled_at"])
        assert sched_at > now, f"Session scheduled in the past: {sched_at}"
