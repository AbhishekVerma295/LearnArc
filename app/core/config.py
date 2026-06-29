"""
app/core/config.py — Application Configuration
================================================

WHY THIS FILE EXISTS
--------------------
In the Flask app, settings were scattered throughout app.py using
`os.environ.get("DB_HOST", "localhost")` calls. That works, but it:
  - Has no type validation (a mis-spelled env var gives a silent wrong value)
  - Has no central place to see all settings at once
  - Has no documentation of what each setting means

WHAT PYDANTIC SETTINGS DOES
----------------------------
`BaseSettings` reads values from environment variables (or a .env file)
and validates their types automatically. If DB_ECHO is set to "banana"
instead of "true/false", the app will fail immediately with a clear error
instead of silently misbehaving later.

HOW ENV VARIABLE NAMES MAP TO FIELD NAMES
------------------------------------------
Pydantic Settings automatically converts field names to UPPERCASE when
looking up environment variables:
  - field `db_host`  →  env var  `DB_HOST`
  - field `db_user`  →  env var  `DB_USER`
  - field `secret_key` → env var `SECRET_KEY`

This means your .env file can use ALL_CAPS (which is the convention)
and the Python fields use snake_case (which is the Python convention).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All application settings in one place.

    Values are loaded from:
      1. Environment variables (highest priority)
      2. The .env file in the project root

    Any value not found uses the default specified here.
    """

    model_config = SettingsConfigDict(
        # Look for a .env file in the current working directory.
        env_file=".env",
        env_file_encoding="utf-8",
        # Ignore any extra env vars that don't match a field.
        # This prevents errors if the system has unrelated env vars.
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    # These mirror the same values used by the original Flask app.
    db_host: str = "localhost"
    db_user: str = "root"
    db_password: str = "root"
    db_name: str = "course_platform"

    # When True, SQLAlchemy prints every SQL query to the console.
    # Useful for debugging, but noisy — keep False in production.
    db_echo: bool = False

    # ── JWT Authentication (used from Phase 3 onwards) ────────────────────────
    # The secret key is used to sign JWT tokens. Anyone who knows this key can
    # forge tokens, so it MUST be a long random string in production.
    # Generate one: python -c "import secrets; print(secrets.token_hex(32))"
    secret_key: str = "please-change-this-to-a-real-secret-before-deploying"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    @property
    def database_url(self) -> str:
        """
        Assembles the full SQLAlchemy connection URL.

        Format: dialect+driver://user:password@host/database

        - `mysql`    → the database engine
        - `+pymysql` → the Python driver (PyMySQL, pure-Python, no C needed)
        - Everything else is standard connection info

        Example output:
            mysql+pymysql://root:root@localhost/course_platform
        """
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}/{self.db_name}"
        )


# Create a single, module-level instance.
# Every other file does:  from app.core.config import settings
# This ensures all modules share the same configuration object.
settings = Settings()
