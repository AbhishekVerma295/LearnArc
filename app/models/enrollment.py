"""
app/models/enrollment.py — Enrollment, Progress, and Certificate ORM Models
============================================================================

These models track student activity:

    Student ──enrolls in──► Course    (ENROLLMENT table)
    Student ──completes──► Lesson     (PROGRESS table)
    Student ──earns──────► Certificate (CERTIFICATE table)

UNIQUE CONSTRAINTS
------------------
The original schema has:
    UNIQUE(StudentID, CourseID)  on ENROLLMENT
    UNIQUE(StudentID, LessonID)  on PROGRESS
    UNIQUE(StudentID, CourseID)  on CERTIFICATE

These are preserved in the models using UniqueConstraint in
__table_args__. Alembic reads this to validate the DB schema matches.
SQLAlchemy also uses it to raise IntegrityError on duplicate inserts
(e.g., a student trying to enroll in the same course twice).

THE AUTO-CERTIFICATE TRIGGER
-----------------------------
The MySQL database has a TRIGGER that automatically inserts a
CERTIFICATE row when a student's ENROLLMENT.CourseStatus changes
to 'Completed'. We do NOT replicate trigger logic in Python — we
simply update the enrollment status and let MySQL handle the rest.
This is documented in the service layer (Phase 3).
"""

import enum
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.student import Student
    from app.models.course import Course, Lesson


class CourseStatusEnum(str, enum.Enum):
    """Enrollment status — mirrors ENROLLMENT.CourseStatus ENUM."""
    active = "Active"
    completed = "Completed"


class Enrollment(Base):
    """
    Maps to the ENROLLMENT table.

    Records which student is enrolled in which course, when they enrolled,
    and whether they have completed the course.

    Business rules (enforced in the service layer):
      - A student cannot enroll in the same course twice (UNIQUE constraint).
      - When CourseStatus changes to 'Completed', the DB trigger
        auto-creates a Certificate row.
    """

    __tablename__ = "ENROLLMENT"
    __table_args__ = (
        # Mirrors UNIQUE(StudentID, CourseID) from the existing schema.
        UniqueConstraint("StudentID", "CourseID", name="uq_enrollment_student_course"),
    )

    # ── Columns ───────────────────────────────────────────────────────────────
    enrollment_id: Mapped[int] = mapped_column(
        "EnrollmentID", Integer, primary_key=True, autoincrement=True
    )
    student_id: Mapped[Optional[int]] = mapped_column(
        "StudentID", Integer, ForeignKey("STUDENT.StudentID"), nullable=True
    )
    course_id: Mapped[Optional[int]] = mapped_column(
        "CourseID", Integer, ForeignKey("COURSE.CourseID"), nullable=True
    )
    enrollment_date: Mapped[Optional[date]] = mapped_column(
        "EnrollmentDate", Date, nullable=True
    )
    course_status: Mapped[Optional[str]] = mapped_column(
        "CourseStatus",
        SAEnum("Active", "Completed", name="enrollment_status"),
        nullable=True,
        default="Active",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    student: Mapped[Optional["Student"]] = relationship(
        "Student", back_populates="enrollments"
    )
    course: Mapped[Optional["Course"]] = relationship(
        "Course", back_populates="enrollments"
    )

    def __repr__(self) -> str:
        return (
            f"<Enrollment student={self.student_id} "
            f"course={self.course_id} status={self.course_status!r}>"
        )


class Progress(Base):
    """
    Maps to the PROGRESS table.

    Records which lessons a student has completed and when.

    One row = one student completed one lesson.
    The UNIQUE(StudentID, LessonID) constraint means marking a lesson
    complete twice is a no-op (using INSERT IGNORE in raw SQL, or
    catching IntegrityError in the service layer).
    """

    __tablename__ = "PROGRESS"
    __table_args__ = (
        UniqueConstraint("StudentID", "LessonID", name="uq_progress_student_lesson"),
    )

    # ── Columns ───────────────────────────────────────────────────────────────
    progress_id: Mapped[int] = mapped_column(
        "ProgressID", Integer, primary_key=True, autoincrement=True
    )
    student_id: Mapped[Optional[int]] = mapped_column(
        "StudentID", Integer, ForeignKey("STUDENT.StudentID"), nullable=True
    )
    lesson_id: Mapped[Optional[int]] = mapped_column(
        "LessonID", Integer, ForeignKey("LESSON.LessonID"), nullable=True
    )
    # Currently only "Completed" is a valid status (as per the original schema).
    # This column exists for future extensibility (e.g., "In Progress").
    progress_status: Mapped[Optional[str]] = mapped_column(
        "ProgressStatus",
        SAEnum("Completed", name="progress_status_enum"),
        nullable=True,
        default="Completed",
    )
    completed_timestamp: Mapped[Optional[datetime]] = mapped_column(
        "CompletedTimestamp", DateTime, nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    student: Mapped[Optional["Student"]] = relationship("Student")
    lesson: Mapped[Optional["Lesson"]] = relationship(
        "Lesson", back_populates="progress_records"
    )

    def __repr__(self) -> str:
        return (
            f"<Progress student={self.student_id} "
            f"lesson={self.lesson_id} at={self.completed_timestamp}>"
        )


class Certificate(Base):
    """
    Maps to the CERTIFICATE table.

    A certificate is automatically created by a MySQL TRIGGER when a
    student's enrollment status changes to 'Completed'. The application
    code does NOT insert into this table directly — it only reads from it.

    The service layer simply reads certificates for display on the dashboard.
    """

    __tablename__ = "CERTIFICATE"
    __table_args__ = (
        UniqueConstraint("StudentID", "CourseID", name="uq_certificate_student_course"),
    )

    # ── Columns ───────────────────────────────────────────────────────────────
    certificate_id: Mapped[int] = mapped_column(
        "CertificateID", Integer, primary_key=True, autoincrement=True
    )
    student_id: Mapped[Optional[int]] = mapped_column(
        "StudentID", Integer, ForeignKey("STUDENT.StudentID"), nullable=True
    )
    course_id: Mapped[Optional[int]] = mapped_column(
        "CourseID", Integer, ForeignKey("COURSE.CourseID"), nullable=True
    )
    issue_date: Mapped[Optional[date]] = mapped_column(
        "IssueDate", Date, nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    student: Mapped[Optional["Student"]] = relationship("Student")
    course: Mapped[Optional["Course"]] = relationship("Course")

    def __repr__(self) -> str:
        return (
            f"<Certificate student={self.student_id} "
            f"course={self.course_id} issued={self.issue_date}>"
        )
