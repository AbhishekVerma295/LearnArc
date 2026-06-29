"""
app/models/__init__.py — Model Package Exports
===============================================

WHY THIS FILE MATTERS FOR ALEMBIC
-----------------------------------
Alembic needs to "see" all models to auto-generate migrations.
It does this by inspecting `Base.metadata` — the registry of all
tables defined by classes that inherit from Base.

But a class only registers itself with Base when its module is imported.
If a model file is never imported, Alembic won't know it exists and
will NOT include it in migrations.

This __init__.py imports every model, so that:
    1. Importing `app.models` automatically registers all tables.
    2. `from app.models import Student` works cleanly.
    3. Alembic's env.py only needs one import: `from app import models`.

ORDER OF IMPORTS MATTERS
-------------------------
enrollment.py references Course and Lesson (foreign keys / relationships).
course.py references Progress (late import at bottom of file).
We import student and instructor first (no dependencies), then course,
then enrollment, which prevents any circular import issues.
"""

from app.models.student import Student, StudentLogin
from app.models.instructor import Instructor, InstructorLogin
from app.models.course import Course, Module, Lesson
from app.models.enrollment import Enrollment, Progress, Certificate

__all__ = [
    "Student",
    "StudentLogin",
    "Instructor",
    "InstructorLogin",
    "Course",
    "Module",
    "Lesson",
    "Enrollment",
    "Progress",
    "Certificate",
]
