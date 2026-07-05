from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.student import StudentResponse, StudentUpdate
from app.models.student import Student
from app.dependencies.auth import get_current_student
from app.services.student_service import update_student

router = APIRouter()

@router.get("/me", response_model=StudentResponse)
def get_student_me(
    current_student: Student = Depends(get_current_student)
):
    """Get current student profile"""
    return current_student

@router.put("/me", response_model=StudentResponse)
def update_student_me(
    student_in: StudentUpdate,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student)
):
    """Update current student profile"""
    updated = update_student(db, student_id=current_student.student_id, student_in=student_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Student not found")
    return updated
