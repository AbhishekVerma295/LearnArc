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

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_PLACEHOLDER = "please-change-this-to-a-real-secret-before-deploying"


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
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = "root"
    db_name: str = "course_platform"

    # When True, SQLAlchemy prints every SQL query to the console.
    # Useful for debugging, but noisy — keep False in production.
    db_echo: bool = False

    # ── JWT Authentication ────────────────────────────────────────────────────
    # The secret key is used to sign JWT tokens. Anyone who knows this key can
    # forge tokens, so it MUST be a long random string in production.
    # Generate one: python -c "import secrets; print(secrets.token_hex(32))"
    #
    # A validator below rejects the insecure placeholder at startup.
    secret_key: str = _INSECURE_PLACEHOLDER
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed frontend origins.
    # Example: "https://app.learnarc.com,https://www.learnarc.com"
    # Use "*" only for fully public, unauthenticated APIs.
    # Defaults to localhost for development convenience.
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    # ── Validators ────────────────────────────────────────────────────────────
    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_set(cls, v: str) -> str:
        """
        Reject the placeholder secret key at application startup.

        If SECRET_KEY is not set (or is still the unsafe placeholder),
        the app raises a clear ValueError immediately rather than starting
        with a dangerously predictable signing key that allows JWT forgery.

        To bypass this in development, generate a real key:
            python -c "import secrets; print(secrets.token_hex(32))"
        and add it to your .env file as:
            SECRET_KEY=<the generated value>
        """
        if v == _INSECURE_PLACEHOLDER:
            raise ValueError(
                "SECRET_KEY is set to the insecure placeholder value. "
                "Generate a real secret: "
                "python -c \"import secrets; print(secrets.token_hex(32))\" "
                "and set it in your .env file or deployment environment."
            )
        return v

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse the comma-separated ALLOWED_ORIGINS string into a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def database_url(self) -> str:
        """
        Assembles the full SQLAlchemy connection URL.

        Format: dialect+driver://user:password@host:port/database

        - `mysql`    → the database engine
        - `+pymysql` → the Python driver (PyMySQL, pure-Python, no C needed)
        - Everything else is standard connection info

        Example output:
            mysql+pymysql://root:root@localhost:3306/course_platform
        """
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


# Create a single, module-level instance.
# Every other file does:  from app.core.config import settings
# This ensures all modules share the same configuration object.
settings = Settings()
