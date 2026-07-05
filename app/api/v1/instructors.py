from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.instructor import InstructorResponse, InstructorUpdate
from app.models.instructor import Instructor
from app.dependencies.auth import get_current_instructor
from app.services.instructor_service import update_instructor

router = APIRouter()

@router.get("/me", response_model=InstructorResponse)
def get_instructor_me(
    current_instructor: Instructor = Depends(get_current_instructor)
):
    """Get current instructor profile"""
    return current_instructor

@router.put("/me", response_model=InstructorResponse)
def update_instructor_me(
    instructor_in: InstructorUpdate,
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor)
):
    """Update current instructor profile"""
    updated = update_instructor(db, instructor_id=current_instructor.instructor_id, instructor_in=instructor_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Instructor not found")
    return updated
