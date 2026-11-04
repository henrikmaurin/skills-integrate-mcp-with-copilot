"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=current_dir / "static"), name="static")

TEACHERS_FILE = current_dir / "teachers.json"
SESSION_COOKIE = "teacher_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
PASSWORD_HASH_ITERATIONS = 600_000
SESSION_SECRET = os.environ.get("SESSION_SECRET") or secrets.token_urlsafe(32)
SECURE_COOKIES = os.environ.get("SECURE_COOKIES", "").lower() == "true"
if len(SESSION_SECRET.encode("utf-8")) < 32:
    raise ValueError("SESSION_SECRET must be at least 32 bytes")


class LoginRequest(BaseModel):
    username: str
    password: str


def _decode_password_hash(encoded_hash: str) -> tuple[int, bytes, bytes]:
    try:
        algorithm, iterations, salt, digest = encoded_hash.split("$")
        iteration_count = int(iterations)
        salt_bytes = base64.b64decode(salt, validate=True)
        digest_bytes = base64.b64decode(digest, validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError("Invalid teacher password hash") from error

    if algorithm != "pbkdf2_sha256" or not PASSWORD_HASH_ITERATIONS <= iteration_count <= 2_000_000:
        raise ValueError("Unsupported teacher password hash")
    if len(salt_bytes) < 16 or len(digest_bytes) != hashlib.sha256().digest_size:
        raise ValueError("Invalid teacher password hash")

    return iteration_count, salt_bytes, digest_bytes


def _load_teachers() -> dict[str, str]:
    with TEACHERS_FILE.open(encoding="utf-8") as teachers_file:
        configuration = json.load(teachers_file)

    if not isinstance(configuration, dict) or not isinstance(
        configuration.get("teachers"), list
    ):
        raise ValueError("teachers.json must contain a 'teachers' list")

    teachers: dict[str, str] = {}
    for teacher in configuration["teachers"]:
        if not isinstance(teacher, dict):
            raise ValueError("Each teacher entry must be an object")

        username = teacher.get("username")
        password_hash = teacher.get("password_hash")
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Each teacher entry must have a username")
        if username in teachers:
            raise ValueError(f"Duplicate teacher username: {username}")
        if not isinstance(password_hash, str):
            raise ValueError(f"Missing password hash for teacher: {username}")

        _decode_password_hash(password_hash)
        teachers[username] = password_hash

    return teachers


TEACHERS = _load_teachers()


def _verify_password(password: str, encoded_hash: str) -> bool:
    iterations, salt, expected_digest = _decode_password_hash(encoded_hash)
    actual_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def _create_session_token(username: str) -> str:
    expires_at = int(time.time()) + SESSION_TTL_SECONDS
    payload = f"{username}\n{expires_at}".encode("utf-8")
    signature = hmac.new(
        SESSION_SECRET.encode("utf-8"), payload, hashlib.sha256
    ).digest()
    encoded_payload = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    return f"{encoded_payload}.{encoded_signature}"


def _get_session_username(token: str | None) -> str | None:
    if not token:
        return None

    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        payload = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
        expected_signature = hmac.new(
            SESSION_SECRET.encode("utf-8"), payload, hashlib.sha256
        ).digest()
        if not hmac.compare_digest(signature, expected_signature):
            return None

        username, expires_at = payload.decode("utf-8").rsplit("\n", 1)
        if int(expires_at) <= int(time.time()):
            return None
    except (ValueError, UnicodeDecodeError):
        return None

    return username if username in TEACHERS else None


def require_teacher(request: Request) -> str:
    username = _get_session_username(request.cookies.get(SESSION_COOKIE))
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Teacher login required",
        )
    return username


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


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/auth/session")
def get_session(request: Request):
    username = _get_session_username(request.cookies.get(SESSION_COOKIE))
    return {"authenticated": username is not None, "username": username}


@app.post("/auth/login")
def login(credentials: LoginRequest, response: Response):
    password_hash = TEACHERS.get(credentials.username)
    if password_hash is None or not _verify_password(
        credentials.password, password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    response.set_cookie(
        key=SESSION_COOKIE,
        value=_create_session_token(credentials.username),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=SECURE_COOKIES,
        samesite="strict",
    )
    return {"username": credentials.username}


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=SECURE_COOKIES,
        samesite="strict",
    )
    return {"message": "Logged out"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str, email: str, _: str = Depends(require_teacher)
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

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
def unregister_from_activity(
    activity_name: str, email: str, _: str = Depends(require_teacher)
):
    """Unregister a student from an activity"""
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
