from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List
from datetime import date
from app.models.course import Course, Module, Lesson
from app.schemas.course import CourseCreate, CourseUpdate, ModuleCreate, ModuleUpdate, LessonCreate, LessonUpdate

def get_course(db: Session, course_id: int):
    return db.get(Course, course_id)

def get_courses(db: Session, skip: int = 0, limit: int = 100):
    return db.execute(select(Course).offset(skip).limit(limit)).scalars().all()

def create_course(db: Session, instructor_id: int, course_in: CourseCreate):
    course = Course(
        title=course_in.title,
        description=course_in.description,
        level=course_in.level,
        created_date=date.today(),
        instructor_id=instructor_id
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course

def update_course(db: Session, course_id: int, course_in: CourseUpdate):
    course = get_course(db, course_id)
    if not course:
        return None
    
    update_data = course_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)
        
    db.add(course)
    db.commit()
    db.refresh(course)
    return course

def create_module(db: Session, course_id: int, module_in: ModuleCreate):
    module = Module(
        course_id=course_id,
        module_title=module_in.module_title,
        module_order=module_in.module_order
    )
    db.add(module)
    db.commit()
    db.refresh(module)
    return module

def create_lesson(db: Session, module_id: int, lesson_in: LessonCreate):
    lesson = Lesson(
        module_id=module_id,
        lesson_title=lesson_in.lesson_title,
        lesson_number=lesson_in.lesson_number,
        duration_minutes=lesson_in.duration_minutes,
        content_url=lesson_in.content_url
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson
