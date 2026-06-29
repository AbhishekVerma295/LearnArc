"""
app/models/course.py — Course, Module, and Lesson ORM Models
=============================================================

These three models represent the core content structure of the LMS:

    Instructor (1) ──► Course (many)
    Course (1)     ──► Module (many)   [ordered by module_order]
    Module (1)     ──► Lesson (many)   [ordered by lesson_number]

ABOUT ENUMS IN SQLALCHEMY
--------------------------
The COURSE table has a Level column defined as:
    ENUM('Beginner', 'Intermediate', 'Advanced')

We represent this in two ways:
  1. As a Python `enum.Enum` class (CourseLevelEnum) for type safety in code.
  2. As `sqlalchemy.Enum` for the database column type.

The Python enum is what you use in service and route code.
The SQLAlchemy Enum is what gets stored in MySQL.

WHY ORDER_BY IN RELATIONSHIP?
------------------------------
    modules: Mapped[list["Module"]] = relationship(
        "Module", order_by="Module.module_order", ...
    )

When you access `course.modules`, SQLAlchemy will automatically ORDER BY
module_order. This means the modules always come back in the correct
display order without having to add .order_by() every time.
"""

import enum
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.instructor import Instructor
    from app.models.enrollment import Enrollment


class CourseLevelEnum(str, enum.Enum):
    """
    Python enum for course difficulty levels.

    Inheriting from `str` means the enum values behave like strings:
        CourseLevelEnum.beginner == "Beginner"  # True
        CourseLevelEnum.beginner.value          # "Beginner"

    This is important for JSON serialization — the API will return
    "Beginner" (the string) not "CourseLevelEnum.beginner".

    Used in:
        - The Course SQLAlchemy model (column type)
        - Pydantic schemas (Phase 2) for input validation
        - Service layer for comparisons
    """
    beginner = "Beginner"
    intermediate = "Intermediate"
    advanced = "Advanced"


class Course(Base):
    """
    Maps to the COURSE table.

    A course is the top-level content container.
    It belongs to one Instructor and contains many Modules.
    Students enroll in courses (via the ENROLLMENT table).
    """

    __tablename__ = "COURSE"

    # ── Columns ───────────────────────────────────────────────────────────────
    course_id: Mapped[int] = mapped_column(
        "CourseID", Integer, primary_key=True, autoincrement=True
    )
    title: Mapped[Optional[str]] = mapped_column(
        "Title", String(200), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(
        "Description", Text, nullable=True
    )
    # SAEnum tells SQLAlchemy this is a MySQL ENUM column.
    # The values must exactly match those in the CREATE TABLE statement.
    level: Mapped[Optional[str]] = mapped_column(
        "Level",
        SAEnum("Beginner", "Intermediate", "Advanced", name="course_level"),
        nullable=True,
    )
    created_date: Mapped[Optional[date]] = mapped_column(
        "CreatedDate", Date, nullable=True
    )
    instructor_id: Mapped[Optional[int]] = mapped_column(
        "InstructorID", Integer, ForeignKey("INSTRUCTOR.InstructorID"), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    instructor: Mapped[Optional["Instructor"]] = relationship(
        "Instructor", back_populates="courses"
    )
    # Modules are ordered by their display position.
    modules: Mapped[list["Module"]] = relationship(
        "Module",
        back_populates="course",
        order_by="Module.module_order",
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment", back_populates="course"
    )

    def __repr__(self) -> str:
        return f"<Course id={self.course_id} title={self.title!r}>"


class Module(Base):
    """
    Maps to the MODULE table.

    A module is a chapter or section within a course.
    One course has many modules, ordered by module_order.
    Each module contains many lessons.
    """

    __tablename__ = "MODULE"

    # ── Columns ───────────────────────────────────────────────────────────────
    module_id: Mapped[int] = mapped_column(
        "ModuleID", Integer, primary_key=True, autoincrement=True
    )
    course_id: Mapped[Optional[int]] = mapped_column(
        "CourseID", Integer, ForeignKey("COURSE.CourseID"), nullable=True
    )
    module_title: Mapped[Optional[str]] = mapped_column(
        "ModuleTitle", String(200), nullable=True
    )
    module_order: Mapped[Optional[int]] = mapped_column(
        "ModuleOrder", Integer, nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    course: Mapped[Optional["Course"]] = relationship(
        "Course", back_populates="modules"
    )
    # Lessons are ordered by their position within the module.
    lessons: Mapped[list["Lesson"]] = relationship(
        "Lesson",
        back_populates="module",
        order_by="Lesson.lesson_number",
    )

    def __repr__(self) -> str:
        return f"<Module id={self.module_id} title={self.module_title!r}>"


class Lesson(Base):
    """
    Maps to the LESSON table.

    A lesson is an individual piece of content (video, article, etc.)
    within a module. Students mark lessons as complete, which drives
    the course progress tracking.
    """

    __tablename__ = "LESSON"

    # ── Columns ───────────────────────────────────────────────────────────────
    lesson_id: Mapped[int] = mapped_column(
        "LessonID", Integer, primary_key=True, autoincrement=True
    )
    module_id: Mapped[Optional[int]] = mapped_column(
        "ModuleID", Integer, ForeignKey("MODULE.ModuleID"), nullable=True
    )
    lesson_title: Mapped[Optional[str]] = mapped_column(
        "LessonTitle", String(200), nullable=True
    )
    lesson_number: Mapped[Optional[int]] = mapped_column(
        "LessonNumber", Integer, nullable=True
    )
    duration_minutes: Mapped[Optional[int]] = mapped_column(
        "DurationMinutes", Integer, nullable=True
    )
    content_url: Mapped[Optional[str]] = mapped_column(
        "ContentURL", String(500), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    module: Mapped[Optional["Module"]] = relationship(
        "Module", back_populates="lessons"
    )
    # Progress records that reference this lesson.
    progress_records: Mapped[list["Progress"]] = relationship(  # type: ignore[name-defined]
        "Progress", back_populates="lesson"
    )

    def __repr__(self) -> str:
        return f"<Lesson id={self.lesson_id} title={self.lesson_title!r}>"
    # Note: the "Progress" string in progress_records relationship above is
    # resolved lazily at runtime by SQLAlchemy — no import needed here.
