"""High School Management System API."""

import hashlib
import json
import os
from pathlib import Path
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

session_secret = os.environ.get("SESSION_SECRET") or secrets.token_hex(32)
app.add_middleware(SessionMiddleware, secret_key=session_secret, same_site="lax")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")
users_file = current_dir / "users.json"

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


class LoginRequest(BaseModel):
    username: str
    password: str


def load_users() -> dict:
    with users_file.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


users = load_users()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        200000,
    ).hex()
    return secrets.compare_digest(password_hash, expected_hash)


def get_current_user(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_admin(request: Request) -> dict:
    user = get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/auth/login")
def login(credentials: LoginRequest, request: Request):
    user_record = users.get(credentials.username)
    if not user_record or not verify_password(
        credentials.password,
        user_record["salt"],
        user_record["password_hash"],
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    session_user = {
        "username": credentials.username,
        "role": user_record["role"],
        "email": user_record["email"],
    }
    request.session.clear()
    request.session["user"] = session_user
    return {"authenticated": True, "user": session_user}


@app.post("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out"}


@app.get("/auth/session")
def read_session(request: Request):
    user = request.session.get("user")
    return {"authenticated": bool(user), "user": user}


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, request: Request):
    """Sign up a student for an activity"""
    current_user = get_current_user(request)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    if current_user["role"] == "student" and email != current_user["email"]:
        raise HTTPException(
            status_code=403,
            detail="Students can only sign up themselves",
        )

    # Get the specific activity
    activity = activities[activity_name]

    if len(activity["participants"]) >= activity["max_participants"]:
        raise HTTPException(status_code=400, detail="Activity is full")

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, request: Request):
    """Unregister a student from an activity"""
    require_admin(request)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
