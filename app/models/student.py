"""
app/models/student.py — Student and StudentLogin ORM Models
============================================================

WHY ORM MODELS?
---------------
In the Flask app, every database interaction was raw SQL:
    cur.execute("SELECT * FROM STUDENT WHERE StudentID=%s", (id,))
    student = cur.fetchone()  # returns a plain dict

With SQLAlchemy ORM models:
    student = db.get(Student, id)  # returns a Student *object*

The object approach gives you:
  - Autocompletion (your editor knows `student.first_name` exists)
  - Type safety (mypy can catch errors at analysis time)
  - Relationships (access `student.enrollments` without writing a JOIN query)
  - Reusability (the model is defined once; used everywhere)

HOW MAPPED[] ANNOTATIONS WORK (SQLAlchemy 2.0)
-----------------------------------------------
Old style:  class Student(Base):
                student_id = Column(Integer, primary_key=True)

New style:  class Student(Base):
                student_id: Mapped[int] = mapped_column(...)

The `Mapped[int]` tells:
  - Python type checkers: student_id is an int
  - SQLAlchemy:           this column is NOT NULL (int, not Optional[int])

`Mapped[Optional[int]]` means the column is NULLABLE.

TABLE NAME MAPPING
------------------
The existing MySQL tables use ALL_CAPS names (STUDENT, STUDENT_LOGIN).
We tell SQLAlchemy about this with __tablename__ = "STUDENT".

COLUMN NAME MAPPING
-------------------
The DB uses PascalCase (StudentID, FirstName). We map these to
Pythonic snake_case attributes (student_id, first_name) by passing
the DB column name as the first argument to mapped_column():
    student_id: Mapped[int] = mapped_column("StudentID", ...)

This keeps the code Pythonic while preserving the existing DB schema.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# TYPE_CHECKING is a special flag — it is True only when a type checker
# (like mypy) is running, not at runtime. We use it for imports that
# would cause circular imports if done at runtime.
if TYPE_CHECKING:
    from app.models.enrollment import Enrollment


class Student(Base):
    """
    Maps to the STUDENT table.

    Stores personal information for a student user.
    Authentication data (email + password) lives in StudentLogin.
    """

    __tablename__ = "STUDENT"

    # ── Columns ───────────────────────────────────────────────────────────────
    student_id: Mapped[int] = mapped_column(
        "StudentID", Integer, primary_key=True, autoincrement=True
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
    phone: Mapped[Optional[str]] = mapped_column(
        "Phone", String(20), nullable=True
    )
    reg_date: Mapped[Optional[date]] = mapped_column(
        "RegDate", nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    # `uselist=False` means "this is a one-to-one relationship, not one-to-many"
    login: Mapped[Optional["StudentLogin"]] = relationship(
        "StudentLogin", back_populates="student", uselist=False
    )
    # A student can be enrolled in many courses.
    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment", back_populates="student"
    )

    def __repr__(self) -> str:
        return f"<Student id={self.student_id} email={self.email!r}>"


class StudentLogin(Base):
    """
    Maps to the STUDENT_LOGIN table.

    Stores authentication credentials (email + bcrypt password hash)
    separately from profile data. This mirrors the existing schema design.

    WHY TWO TABLES?
    ---------------
    The original schema separated profile (STUDENT) from credentials
    (STUDENT_LOGIN). We preserve this design to maintain compatibility.
    In a greenfield project, these might be merged into one table.
    """

    __tablename__ = "STUDENT_LOGIN"

    # ── Columns ───────────────────────────────────────────────────────────────
    student_login_id: Mapped[int] = mapped_column(
        "StudentLoginID", Integer, primary_key=True, autoincrement=True
    )
    student_id: Mapped[Optional[int]] = mapped_column(
        "StudentID", Integer, ForeignKey("STUDENT.StudentID"), nullable=True
    )
    email: Mapped[Optional[str]] = mapped_column(
        "Email", String(150), nullable=True
    )
    # bcrypt hash — always 60 characters, but VARCHAR(255) gives headroom.
    password: Mapped[Optional[str]] = mapped_column(
        "Password", String(255), nullable=True
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        "LastLogin", DateTime, nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    student: Mapped[Optional["Student"]] = relationship(
        "Student", back_populates="login"
    )

    def __repr__(self) -> str:
        return f"<StudentLogin id={self.student_login_id} email={self.email!r}>"
