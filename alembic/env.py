"""
alembic/env.py — Alembic Migration Environment
===============================================

WHY THIS FILE EXISTS
--------------------
Alembic needs to know:
  1. HOW to connect to the database (the URL)
  2. WHAT models exist (so it can compare them to the live DB)

This file provides both by:
  1. Using settings.database_url (from our Pydantic config) instead of
     a hardcoded URL — keeps credentials out of version control.
  2. Importing all our models so their table definitions are visible
     in Base.metadata.

OFFLINE vs ONLINE MODE
-----------------------
Alembic can run in two modes:

  Offline mode: generates SQL scripts without connecting to the DB.
    Used when you want to inspect the SQL before running it.
    Command: alembic upgrade head --sql

  Online mode: connects to the DB and applies migrations directly.
    The normal workflow.
    Command: alembic upgrade head

This file supports both modes.

HOW TO USE ALEMBIC (QUICK REFERENCE)
--------------------------------------
  # Generate a new migration from model changes:
  alembic revision --autogenerate -m "add phone to instructor"

  # Apply all pending migrations:
  alembic upgrade head

  # Roll back the last migration:
  alembic downgrade -1

  # Mark the current DB state as "already at this revision"
  # (used when the DB was created manually, not via Alembic):
  alembic stamp head

  # See migration history:
  alembic history
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Path Fix ──────────────────────────────────────────────────────────────────
# Alembic runs from the `learnarc/` directory. Adding the project root to
# sys.path ensures that `from app.xxx import yyy` works in this file.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── App Imports ───────────────────────────────────────────────────────────────
# Import settings FIRST (needs .env to be readable from project root).
from app.core.config import settings  # noqa: E402

# Import Base and ALL models.
# Importing the models registers them with Base.metadata.
# Without these imports, Alembic would see an empty metadata and think
# all tables need to be dropped and recreated!
from app.models.base import Base  # noqa: E402
from app.models import (  # noqa: E402, F401
    Student, StudentLogin,
    Instructor, InstructorLogin,
    Course, Module, Lesson,
    Enrollment, Progress, Certificate,
)

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

# Override the placeholder sqlalchemy.url in alembic.ini with the real URL
# built from our environment variables. Credentials stay in .env, not in ini.
config.set_main_option("sqlalchemy.url", settings.database_url)

# Configure Python's logging from the alembic.ini [loggers] section.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is the metadata object that Alembic compares against the live database.
# It contains the table definitions for ALL models imported above.
target_metadata = Base.metadata


# ── Migration Runners ─────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """
    Run migrations without a live database connection.

    Generates SQL scripts that can be reviewed and applied manually.
    Useful in CI/CD pipelines where the DB may not be accessible.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include ENUM types in comparison so Alembic detects ENUM changes.
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations with a live database connection.

    This is the normal workflow: connect to the DB and apply migrations.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        # NullPool: do not pool connections during migrations.
        # Each migration gets a fresh connection, which prevents
        # stale transaction issues during long migrations.
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Detect column type changes (e.g., String(100) → String(200)).
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ── Entry Point ───────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
