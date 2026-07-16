from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timezone
from app.models.enrollment import Enrollment, Progress, Certificate, CourseStatusEnum
from app.models.course import Lesson, Module


def enroll_student(db: Session, student_id: int, course_id: int):
    # Check if already enrolled
    existing = db.execute(
        select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.course_id == course_id
        )
    ).scalar_one_or_none()

    if existing:
        return existing

    enrollment = Enrollment(
        student_id=student_id,
        course_id=course_id,
        enrollment_date=date.today(),
        course_status=CourseStatusEnum.active
    )
    db.add(enrollment)
    try:
        db.commit()
        db.refresh(enrollment)
    except IntegrityError:
        # Race condition: another request enrolled this student concurrently.
        # Roll back and return the existing enrollment.
        db.rollback()
        enrollment = db.execute(
            select(Enrollment).where(
                Enrollment.student_id == student_id,
                Enrollment.course_id == course_id
            )
        ).scalar_one()
    return enrollment


def record_progress(db: Session, student_id: int, lesson_id: int):
    # Check if already recorded
    existing = db.execute(
        select(Progress).where(
            Progress.student_id == student_id,
            Progress.lesson_id == lesson_id
        )
    ).scalar_one_or_none()

    if existing:
        progress = existing
    else:
        progress = Progress(
            student_id=student_id,
            lesson_id=lesson_id,
            progress_status="Completed",
            completed_timestamp=datetime.now(timezone.utc),
        )
        db.add(progress)
        try:
            db.commit()
            db.refresh(progress)
        except IntegrityError:
            # Race condition: same student marked same lesson concurrently.
            db.rollback()
            progress = db.execute(
                select(Progress).where(
                    Progress.student_id == student_id,
                    Progress.lesson_id == lesson_id
                )
            ).scalar_one()

    # Check if this lesson completion finishes the entire course
    lesson = db.get(Lesson, lesson_id)
    if lesson:
        module = db.get(Module, lesson.module_id)
        if module:
            course_id = module.course_id

            # Count total lessons in course
            total_lessons = db.execute(
                select(func.count(Lesson.lesson_id))
                .join(Module)
                .where(Module.course_id == course_id)
            ).scalar() or 0

            # Count completed lessons by student for this course
            completed_lessons = db.execute(
                select(func.count(Progress.progress_id))
                .join(Lesson)
                .join(Module)
                .where(
                    Progress.student_id == student_id,
                    Module.course_id == course_id,
                    Progress.progress_status == "Completed"
                )
            ).scalar() or 0

            if total_lessons > 0 and completed_lessons >= total_lessons:
                # Mark enrollment as completed; DB trigger auto-creates the Certificate.
                enrollment = db.execute(
                    select(Enrollment).where(
                        Enrollment.student_id == student_id,
                        Enrollment.course_id == course_id
                    )
                ).scalar_one_or_none()

                if enrollment and enrollment.course_status != CourseStatusEnum.completed:
                    enrollment.course_status = CourseStatusEnum.completed
                    db.add(enrollment)
                    db.commit()

    return progress


def get_student_certificates(db: Session, student_id: int):
    return db.execute(
        select(Certificate).where(Certificate.student_id == student_id)
    ).scalars().all()
