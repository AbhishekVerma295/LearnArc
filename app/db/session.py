"""
app/db/session.py — Database Engine and Session Factory
=========================================================

WHY THIS FILE EXISTS
--------------------
In the Flask app, every route created a brand new database connection:
    db = mysql.connector.connect(**DB_CONFIG)
    cur = db.cursor(dictionary=True)

This is inefficient — opening a TCP connection to MySQL takes time.
SQLAlchemy solves this with a **connection pool**: a set of pre-opened
connections that are reused across requests.

KEY CONCEPTS
------------
engine
    The connection pool. Created ONCE when the app starts. SQLAlchemy
    keeps several database connections alive and hands them out as needed.

SessionLocal
    A factory (blueprint) for creating Session objects. When you call
    SessionLocal(), you get a fresh Session tied to one connection from
    the pool.

Session
    The "unit of work" for one request. It tracks all database objects
    you load or create, and either commits or rolls back them together.
    After the request, the session is closed and the connection returns
    to the pool.

get_db()
    A FastAPI "dependency" (explained in Phase 3). Every route that needs
    the database declares `db: Session = Depends(get_db)`. FastAPI will
    call get_db(), give the yielded session to the route, then call the
    cleanup code (db.close()) automatically when the request finishes —
    even if an exception occurred.
"""

from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
# The engine is created once at module import time (i.e. at startup).
# It manages a pool of database connections.
engine = create_engine(
    settings.database_url,
    # Echo every SQL query to the console when DB_ECHO=true in .env.
    echo=settings.db_echo,
    # Before using a connection from the pool, send a lightweight "SELECT 1"
    # to check it is still alive. This prevents errors after the DB server
    # drops idle connections (common after 8 hours in MySQL).
    pool_pre_ping=True,
    # Automatically close and replace pool connections older than 1 hour.
    # Prevents "MySQL server has gone away" errors on long-running apps.
    pool_recycle=3600,
)

# ── Session Factory ───────────────────────────────────────────────────────────
# SessionLocal is NOT a session — it is a class that creates sessions.
# Think of it like a cookie cutter: the cutter itself is SessionLocal,
# and each cookie (session) is created by calling SessionLocal().
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,  # We commit manually — no accidental partial saves.
    autoflush=False,   # We flush manually — gives us more control.
)


# ── Database Dependency ───────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides one database session per request.

    How a FastAPI dependency works:
        1. FastAPI sees that a route needs `db: Session = Depends(get_db)`.
        2. It calls get_db() which opens a new Session.
        3. The `yield` pauses the function and gives the Session to the route.
        4. The route runs (using the session to query the database).
        5. After the route finishes (or crashes), FastAPI resumes get_db()
           after the yield — running the `finally` block which closes the session.

    The `try/finally` guarantees the session is ALWAYS closed, even on errors.
    This prevents connection leaks.

    Usage in a route:
        @router.get("/something")
        def my_route(db: Session = Depends(get_db)):
            result = db.execute(select(MyModel)).scalars().all()
            return result
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """
    Attempts a simple SELECT 1 to verify the database is reachable.
    Returns True on success, False on failure.

    Called at startup in main.py to give an immediate error message
    if the database configuration is wrong.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
