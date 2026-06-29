"""
app/models/base.py — SQLAlchemy Declarative Base
=================================================

WHY THIS FILE EXISTS
--------------------
Every SQLAlchemy ORM model (Student, Course, Lesson, etc.) must inherit
from a single shared `Base` class. The Base class:

  1. Keeps a registry of ALL models — so SQLAlchemy knows which Python
     classes map to which database tables.

  2. Enables `Base.metadata.create_all()` — which can create all tables
     at once from the model definitions.

  3. Enables Alembic's autogenerate — Alembic compares `Base.metadata`
     (the models you defined) against the live database to find
     differences and generate migrations automatically.

WHY A SEPARATE FILE?
--------------------
If we defined `Base` inside one of the model files (e.g. student.py),
we would have a circular import problem: other models that need to
reference Student would import from student.py, which would force
that file to be evaluated first, causing errors.

By putting Base in its own file, all models import from one neutral
location with no circular dependency risk.

SQLAlchemy 2.0 vs 1.x
----------------------
Old (SQLAlchemy 1.x):
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()

New (SQLAlchemy 2.0):
    from sqlalchemy.orm import DeclarativeBase
    class Base(DeclarativeBase): pass

The new style is preferred because it works with Python type checkers
(like mypy and pyright) and allows typed column definitions.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models in LearnArc.

    Every model (Student, Course, etc.) inherits from this class.
    No columns or logic are added here — it is purely a shared
    registry and metadata container.
    """
    pass
