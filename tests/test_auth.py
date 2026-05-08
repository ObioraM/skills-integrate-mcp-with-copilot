from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


@pytest.fixture(autouse=True)
def reset_activities():
    original_state = deepcopy(activities)
    yield
    activities.clear()
    activities.update(deepcopy(original_state))


def test_signup_requires_authentication():
    client = TestClient(app)

    response = client.post("/activities/Chess%20Club/signup?email=student@mergington.edu")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_student_can_log_in_and_sign_up_self():
    client = TestClient(app)

    login_response = client.post(
        "/auth/login",
        json={"username": "student", "password": "student-password"},
    )
    signup_response = client.post(
        "/activities/Chess%20Club/signup?email=student@mergington.edu"
    )

    assert login_response.status_code == 200
    assert login_response.json()["user"]["role"] == "student"
    assert signup_response.status_code == 200
    assert "student@mergington.edu" in activities["Chess Club"]["participants"]


def test_student_cannot_sign_up_other_student():
    client = TestClient(app)
    client.post(
        "/auth/login",
        json={"username": "student", "password": "student-password"},
    )

    response = client.post(
        "/activities/Chess%20Club/signup?email=someoneelse@mergington.edu"
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Students can only sign up themselves"


def test_admin_can_unregister_students():
    client = TestClient(app)
    client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin-password"},
    )

    response = client.delete(
        "/activities/Chess%20Club/unregister?email=michael@mergington.edu"
    )

    assert response.status_code == 200
    assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]