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

# One-time cleanup before the app/engine is ever imported — if a stale
# test.db from an older local run (possibly with an outdated schema) is
# lying around, remove it so we start from a clean slate. CI always starts
# from a fresh checkout so this is a no-op there.
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()


@pytest.fixture(autouse=True)
def _fresh_database():
    """Resets the schema between tests via the app's own long-lived engine,
    rather than deleting/recreating the SQLite file on disk. Deleting the
    file was the original approach here, but it caused 'attempt to write a
    readonly database' errors: the engine's connection pool kept a cached
    connection handle pointing at the just-deleted file, which SQLite
    doesn't tolerate well. Dropping and recreating tables through the same
    engine avoids ever touching the file at the OS level after the first
    test starts."""
    from app.database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_db_file():
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
