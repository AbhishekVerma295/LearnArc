from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.instructor import Instructor, InstructorLogin
from app.schemas.instructor import InstructorCreate, InstructorUpdate

def get_instructor(db: Session, instructor_id: int):
    return db.get(Instructor, instructor_id)

def get_instructor_by_email(db: Session, email: str):
    return db.execute(select(Instructor).where(Instructor.email == email)).scalar_one_or_none()

def create_instructor(db: Session, instructor_in: InstructorCreate):
    instructor_login = InstructorLogin(
        email=instructor_in.email,
        password=instructor_in.password  # TODO: Hash password in Phase 3
    )
    instructor = Instructor(
        first_name=instructor_in.first_name,
        last_name=instructor_in.last_name,
        email=instructor_in.email,
        bio=instructor_in.bio,
        login=instructor_login
    )
    db.add(instructor)
    db.commit()
    db.refresh(instructor)
    return instructor

def update_instructor(db: Session, instructor_id: int, instructor_in: InstructorUpdate):
    instructor = get_instructor(db, instructor_id)
    if not instructor:
        return None
    
    update_data = instructor_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(instructor, field, value)
        
    db.add(instructor)
    db.commit()
    db.refresh(instructor)
    return instructor
