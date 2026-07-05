# LearnArc API — FastAPI Edition

> A modernized Learning Management System backend built with **FastAPI**, **SQLAlchemy 2.0**, **Alembic**, and **JWT Authentication**.

Originally a Flask monolith, refactored into a clean layered architecture suitable for a software engineering portfolio.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 (synchronous) |
| Database | MySQL (existing schema reused) |
| Driver | PyMySQL |
| Migrations | Alembic |
| Auth | JWT via python-jose |
| Config | Pydantic Settings v2 |
| Server | Uvicorn |

---

## Project Structure

```
learnarc/
├── app/
│   ├── main.py              ← FastAPI app + middleware + health endpoint
│   ├── core/
│   │   └── config.py        ← Pydantic Settings (reads .env)
│   ├── db/
│   │   └── session.py       ← SQLAlchemy engine + get_db() dependency
│   ├── models/              ← SQLAlchemy ORM models (one file per domain)
│   ├── schemas/             ← Pydantic v2 request/response schemas [Phase 2]
│   ├── services/            ← Business logic layer [Phase 2+]
│   ├── dependencies/        ← FastAPI auth dependencies [Phase 3]
│   ├── api/v1/              ← REST API route handlers [Phase 4]
│   └── utils/               ← Shared utilities [Phase 3+]
├── alembic/                 ← Database migrations
├── alembic.ini
├── requirements.txt
└── .env                     ← Never commit this!
```

---

## Quick Start

### 1. Configure environment

```bash
# .env is already populated — update DB credentials if needed
notepad .env
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up Alembic (first time only)

```bash
# If the database already exists from the Flask app:
alembic stamp head

# For a fresh database, generate and apply initial migration:
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

### 4. Run the development server

```bash
uvicorn app.main:app --reload
```

### 5. Open API documentation

- **Swagger UI** → http://localhost:8000/docs
- **ReDoc** → http://localhost:8000/redoc
- **Health check** → http://localhost:8000/health

---

## Architecture

```
Client
  ↓
FastAPI Router (api/v1/)
  ↓
Dependencies (Auth / DB Session)
  ↓
Service Layer (business logic)
  ↓
SQLAlchemy Models
  ↓
MySQL Database
```

---

## Development Phases

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Done | Scaffold + SQLAlchemy models + Alembic |
| 2 | ✅ Done | Pydantic schemas + Service layer |
| 3 | ✅ Done | JWT auth + Auth endpoints |
| 4 | ✅ Done | Full REST API endpoints |
| 5 | 🔲 | Docker + Tests + CI |

---

## Database

This project uses the **existing `course_platform` MySQL database** created by the original Flask app. No schema changes in Phase 1 — all tables, views, and triggers are preserved.

See `../files/setup.sql` for the original schema.
