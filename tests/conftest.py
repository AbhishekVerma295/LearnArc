"""
tests/conftest.py — Test Configuration and Fixtures
=====================================================

WHY SQLITE IN-MEMORY FOR TESTS
--------------------------------
The original conftest used the live MySQL database which causes:
  - Tests depend on a running MySQL server (bad for CI portability)
  - Test data accumulates in the real DB (rows from one test run pollute the next)
  - Tests can interfere with each other via shared DB state

Instead, we:
  1. Create a fresh SQLite :memory: database for each test module.
  2. Create all tables from the SQLAlchemy models (same schema as MySQL).
  3. Override the FastAPI `get_db` dependency to use this test DB.
  4. Override environment variables so no real .env is required in CI.

NOTE ON SQLITE vs MYSQL ENUM COLUMNS
--------------------------------------
SQLite does not support ENUM column types natively. SQLAlchemy silently maps
MySQL ENUM → VARCHAR in SQLite, so enum values are stored as plain strings.
This is fine for testing business logic — the behaviour is identical.
"""

import os
import pytest

# ── Override environment before any app imports ────────────────────────────────
# These must be set BEFORE importing anything from `app` because
# app/core/config.py reads env vars at module import time.
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-testing-1234")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USER", "root")
os.environ.setdefault("DB_PASSWORD", "root")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.models.base import Base


# ── Test Database Setup ────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def test_db_engine():
    """
    Creates a fresh SQLite in-memory database for each test module.
    StaticPool ensures the same in-memory DB connection is shared
    across the entire module (instead of each call getting a new DB).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Create all tables from the ORM models
    Base.metadata.create_all(bind=engine)
    yield engine
    # Drop all tables after the test module finishes
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="module")
def test_session_factory(test_db_engine):
    """Returns a session factory bound to the test engine."""
    return sessionmaker(bind=test_db_engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="module")
def client(test_session_factory):
    """
    Provides a TestClient with the DB dependency overridden to use
    the in-memory SQLite test database.
    """
    def override_get_db():
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    # Clean up: restore the original dependency after the module finishes.
    app.dependency_overrides.clear()
