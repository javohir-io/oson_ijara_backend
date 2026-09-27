import os
import pathlib

# Point the app at a throwaway SQLite file instead of Postgres, and set this
# before any `app.*` module is imported — pydantic-settings reads env vars
# once, at import time.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
from fastapi.testclient import TestClient

TEST_DB_PATH = pathlib.Path("test.db")


@pytest.fixture(autouse=True)
def _fresh_database():
    """Every test gets a brand-new, empty database file — the app's own
    startup event (Base.metadata.create_all) recreates the schema in it
    when the TestClient's `with` block enters below."""
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    yield
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture
def client():
    from app.main import app  # imported lazily so the env vars above are set first

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def register_user(client):
    """Registers a user via the real API and returns their token/headers —
    exercises the actual registration flow (hashing, JWT signing, etc.)
    rather than inserting a row directly."""

    def _register(email="user@example.com", password="testpass123", full_name="Test User", phone=None):
        payload = {"full_name": full_name, "email": email, "password": password}
        if phone:
            payload["phone"] = phone
        response = client.post("/auth/register", json=payload)
        assert response.status_code == 201, response.text
        data = response.json()
        return {
            "token": data["access_token"],
            "headers": {"Authorization": f"Bearer {data['access_token']}"},
            "user": data["user"],
        }

    return _register


@pytest.fixture
def make_admin():
    """Directly flips is_admin in the database — intentionally not exposed
    via any API endpoint, so tests reach into the DB the same way an
    operator would (e.g. via Adminer) to promote the first admin."""

    def _make_admin(email: str):
        from app import models
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            user = db.query(models.User).filter(models.User.email == email).first()
            user.is_admin = True
            db.commit()
        finally:
            db.close()

    return _make_admin
