"""
app/main.py — FastAPI Application Entry Point
==============================================

This is the heart of the FastAPI application. It:
  1. Creates the FastAPI app instance
  2. Configures CORS middleware
  3. Defines the application lifespan (startup / shutdown hooks)
  4. Registers all API routers (added in Phase 4)
  5. Provides a /health endpoint for monitoring

HOW FASTAPI DIFFERS FROM FLASK
-------------------------------
Flask:
    app = Flask(__name__)
    @app.route("/")
    def index(): ...

FastAPI:
    app = FastAPI()
    @app.get("/")
    def index(): ...

FastAPI is very similar to Flask for basic routes, but adds:
  - Automatic OpenAPI docs at /docs (Swagger UI) and /redoc
  - Automatic request/response validation via Pydantic
  - Dependency injection via Depends()
  - Type annotations that drive validation AND documentation

LIFESPAN (STARTUP / SHUTDOWN)
------------------------------
FastAPI uses a "lifespan" context manager for startup and shutdown logic.
This replaces the older @app.on_event("startup") decorator (which is
deprecated in modern FastAPI).

On startup, we verify the database is reachable so developers get an
immediate, clear error instead of a cryptic failure on the first request.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import check_db_connection

# ── Logging ───────────────────────────────────────────────────────────────────
# Configure basic logging so startup messages appear in the console.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Runs once at startup (before `yield`) and once at shutdown (after `yield`).

    Why asynccontextmanager?
    FastAPI's lifespan system requires an async context manager, even if
    our database code is synchronous. The `async def` / `yield` pattern
    is just the required signature — the actual DB operations are sync.
    """
    # ── STARTUP ───────────────────────────────────────────────────────────────
    logger.info("LearnArc API starting up...")
    logger.info("Connecting to database: %s@%s/%s", settings.db_user, settings.db_host, settings.db_name)

    if check_db_connection():
        logger.info("✓ Database connection OK")
    else:
        logger.error(
            "✗ Database connection FAILED. "
            "Check DB_HOST, DB_USER, DB_PASSWORD, DB_NAME in your .env file."
        )
        # We do not raise here — the app still starts but DB-dependent routes
        # will return 500 errors. Raising would crash the process entirely.

    yield  # ← application runs here

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    logger.info("LearnArc API shutting down...")


# ── Application Instance ──────────────────────────────────────────────────────
app = FastAPI(
    title="LearnArc API",
    description=(
        "Online Course Progress & Analytics Platform — "
        "FastAPI modernization of the original Flask LMS."
    ),
    version="2.0.0",
    # /docs → Swagger UI (interactive API explorer)
    docs_url="/docs",
    # /redoc → ReDoc (clean, read-only API documentation)
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── Middleware ────────────────────────────────────────────────────────────────
# CORS (Cross-Origin Resource Sharing) allows a frontend (e.g. React on
# localhost:3000) to call this API (on localhost:8000) without the browser
# blocking the request with a CORS error.
#
# allow_origins=["*"] means ANY origin is allowed.
# In production, replace with your specific frontend URL:
#   allow_origins=["https://learnarc.yourdomain.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────
# API routers are registered here as they are built in later phases.
from app.api.v1 import auth

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])

# Future (Phase 4):
#   from app.api.v1 import courses, students, instructors
#   app.include_router(courses.router,     prefix="/api/v1/courses",     tags=["Courses"])
#   app.include_router(students.router,    prefix="/api/v1/students",    tags=["Students"])
#   app.include_router(instructors.router, prefix="/api/v1/instructors", tags=["Instructors"])


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    """
    Health check endpoint.

    Used by:
      - Docker health checks (HEALTHCHECK in Dockerfile)
      - Deployment platforms (Railway, Render, etc.)
      - Monitoring tools (Uptime Robot, etc.)

    Returns a simple JSON response indicating the API is alive.
    The database status will be added in Phase 3.
    """
    return {
        "status": "ok",
        "version": "2.0.0",
        "app": "LearnArc API",
    }
