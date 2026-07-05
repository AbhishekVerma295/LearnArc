from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.schemas.enrollment import EnrollmentResponse, ProgressResponse, CertificateResponse
from app.models.student import Student
from app.dependencies.auth import get_current_student
from app.services.enrollment_service import enroll_student, record_progress, get_student_certificates
from app.services.course_service import get_course

router = APIRouter()

@router.post("/courses/{course_id}", response_model=EnrollmentResponse)
def enroll_in_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    """Enroll in a course (Student only)"""
    course = get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    return enroll_student(db, student_id=current_student.student_id, course_id=course_id)

@router.post("/progress/lessons/{lesson_id}", response_model=ProgressResponse)
def complete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    """Mark a lesson as complete (Student only)"""
    from app.models.course import Lesson
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    return record_progress(db, student_id=current_student.student_id, lesson_id=lesson_id)

@router.get("/certificates", response_model=List[CertificateResponse])
def list_certificates(
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    """List earned certificates (Student only)"""
    return get_student_certificates(db, student_id=current_student.student_id)
