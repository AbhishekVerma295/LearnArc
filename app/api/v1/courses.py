from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.schemas.course import (
    CourseResponse, CourseCreate, ModuleResponse, ModuleCreate, LessonResponse, LessonCreate
)
from app.models.instructor import Instructor
from app.dependencies.auth import get_current_instructor
from app.services.course_service import (
    get_course, get_courses, create_course, create_module, create_lesson
)

router = APIRouter()

@router.get("/", response_model=List[CourseResponse])
def list_courses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all courses (Public)"""
    return get_courses(db, skip=skip, limit=limit)

@router.get("/{course_id}", response_model=CourseResponse)
def retrieve_course(course_id: int, db: Session = Depends(get_db)):
    """Retrieve course details (Public)"""
    course = get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.post("/", response_model=CourseResponse)
def add_course(
    course_in: CourseCreate,
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor)
):
    """Create a new course (Instructor only)"""
    return create_course(db, instructor_id=current_instructor.instructor_id, course_in=course_in)

@router.post("/{course_id}/modules", response_model=ModuleResponse)
def add_module(
    course_id: int,
    module_in: ModuleCreate,
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor)
):
    """Add a module to a course (Instructor only)"""
    course = get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.instructor_id != current_instructor.instructor_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this course")
        
    return create_module(db, course_id=course_id, module_in=module_in)

@router.post("/modules/{module_id}/lessons", response_model=LessonResponse)
def add_lesson(
    module_id: int,
    lesson_in: LessonCreate,
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor)
):
    """Add a lesson to a module (Instructor only)"""
    from app.models.course import Module
    module = db.get(Module, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    course = get_course(db, module.course_id)
    if course.instructor_id != current_instructor.instructor_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this module")
        
    return create_lesson(db, module_id=module_id, lesson_in=lesson_in)
