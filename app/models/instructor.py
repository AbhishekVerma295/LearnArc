"""
app/models/instructor.py — Instructor and InstructorLogin ORM Models
=====================================================================

Mirrors the INSTRUCTOR and INSTRUCTOR_LOGIN tables.
Same design philosophy as student.py: profile data and auth credentials
are stored in separate tables (matching the existing schema).

See student.py for detailed explanations of the ORM patterns used here.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.course import Course


class Instructor(Base):
    """
    Maps to the INSTRUCTOR table.

    Stores profile information for an instructor (teacher/content creator).
    An instructor can own many courses.
    """

    __tablename__ = "INSTRUCTOR"

    # ── Columns ───────────────────────────────────────────────────────────────
    instructor_id: Mapped[int] = mapped_column(
        "InstructorID", Integer, primary_key=True, autoincrement=True
    )
    first_name: Mapped[Optional[str]] = mapped_column(
        "FirstName", String(100), nullable=True
    )
    last_name: Mapped[Optional[str]] = mapped_column(
        "LastName", String(100), nullable=True
    )
    email: Mapped[Optional[str]] = mapped_column(
        "Email", String(150), unique=True, nullable=True
    )
    # Bio is TEXT in MySQL — no length limit (up to 65,535 bytes).
    bio: Mapped[Optional[str]] = mapped_column(
        "Bio", Text, nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    login: Mapped[Optional["InstructorLogin"]] = relationship(
        "InstructorLogin", back_populates="instructor", uselist=False
    )
    # An instructor can create many courses.
    courses: Mapped[list["Course"]] = relationship(
        "Course", back_populates="instructor"
    )

    def __repr__(self) -> str:
        return f"<Instructor id={self.instructor_id} email={self.email!r}>"


class InstructorLogin(Base):
    """
    Maps to the INSTRUCTOR_LOGIN table.

    Stores authentication credentials for instructors.
    Same pattern as StudentLogin — credentials separate from profile.
    """

    __tablename__ = "INSTRUCTOR_LOGIN"

    # ── Columns ───────────────────────────────────────────────────────────────
    instructor_login_id: Mapped[int] = mapped_column(
        "InstructorLoginID", Integer, primary_key=True, autoincrement=True
    )
    instructor_id: Mapped[Optional[int]] = mapped_column(
        "InstructorID", Integer, ForeignKey("INSTRUCTOR.InstructorID"), nullable=True
    )
    email: Mapped[Optional[str]] = mapped_column(
        "Email", String(150), nullable=True
    )
    password: Mapped[Optional[str]] = mapped_column(
        "Password", String(255), nullable=True
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        "LastLogin", DateTime, nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    instructor: Mapped[Optional["Instructor"]] = relationship(
        "Instructor", back_populates="login"
    )

    def __repr__(self) -> str:
        return f"<InstructorLogin id={self.instructor_login_id} email={self.email!r}>"
