"""
app/main.py — FastAPI Application Entry Point
==============================================

This is the heart of the FastAPI application. It:
  1. Creates the FastAPI app instance
  2. Configures CORS middleware
  3. Defines the application lifespan (startup / shutdown hooks)
  4. Registers all API routers
  5. Provides a /health endpoint for monitoring

PRODUCTION NOTES
-----------------
- CORS: Controlled via ALLOWED_ORIGINS env var (comma-separated origins).
        Defaults to localhost for development. Set to your frontend URL in prod.
- Health: /health checks real DB connectivity and returns 503 if the DB is down.
          This is what load balancers / deployment platforms rely on.
- Rate Limiting: Auth endpoints are rate-limited via slowapi to prevent brute force.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.db.session import check_db_connection

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Rate Limiter ──────────────────────────────────────────────────────────────
# Keyed by client IP address. Shared across the app via app.state.limiter.
limiter = Limiter(key_func=get_remote_address)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Runs once at startup (before `yield`) and once at shutdown (after `yield`).
    """
    # ── STARTUP ───────────────────────────────────────────────────────────────
    logger.info("LearnArc API starting up...")
    logger.info(
        "Connecting to database: %s@%s:%s/%s",
        settings.db_user,
        settings.db_host,
        settings.db_port,
        settings.db_name,
    )
    logger.info("CORS allowed origins: %s", settings.allowed_origins_list)

    if check_db_connection():
        logger.info("✓ Database connection OK")
    else:
        logger.error(
            "✗ Database connection FAILED. "
            "Check DB_HOST, DB_USER, DB_PASSWORD, DB_NAME in your .env file."
        )

    yield  # ← application runs here

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    logger.info("LearnArc API shutting down...")


# ── Application Instance ──────────────────────────────────────────────────────
app = FastAPI(
    title="LearnArc API",
    description=(
        "Online Course Progress & Analytics Platform — "
        "FastAPI modernization of the original Flask LMS.\n\n"
        "**Authentication:** Use the `/api/v1/auth/login/student` or "
        "`/api/v1/auth/login/instructor` endpoints to obtain a Bearer token, "
        "then click 'Authorize' above."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Rate Limiter State ────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Middleware ────────────────────────────────────────────────────────────────
# CORS (Cross-Origin Resource Sharing) allows a frontend (e.g. React on
# localhost:3000) to call this API (on localhost:8000) without the browser
# blocking the request with a CORS error.
#
# Origins are controlled via the ALLOWED_ORIGINS env var.
# In production, set: ALLOWED_ORIGINS=https://learnarc.yourdomain.com
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────
from app.api.v1 import auth, courses, students, instructors, enrollments

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(courses.router, prefix="/api/v1/courses", tags=["Courses"])
app.include_router(students.router, prefix="/api/v1/students", tags=["Students"])
app.include_router(instructors.router, prefix="/api/v1/instructors", tags=["Instructors"])
app.include_router(enrollments.router, prefix="/api/v1/enrollments", tags=["Enrollments"])


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check() -> dict:
    """
    Health check endpoint.

    Used by:
      - Docker HEALTHCHECK instruction
      - Deployment platforms (Railway, Render, etc.)
      - Monitoring tools (Uptime Robot, etc.)

    Returns HTTP 200 with {"status": "ok"} when the DB is reachable.
    Returns HTTP 503 with {"status": "degraded"} when the DB is unreachable.

    NOTE: Load balancers and hosting platforms rely on this endpoint to decide
    whether to route traffic to this pod. A false 200 when the DB is down
    would result in all requests silently failing.
    """
    db_ok = check_db_connection()
    if not db_ok:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "version": "2.0.0",
                "app": "LearnArc API",
                "database": "unreachable",
            },
        )
    return {
        "status": "ok",
        "version": "2.0.0",
        "app": "LearnArc API",
        "database": "connected",
    }
