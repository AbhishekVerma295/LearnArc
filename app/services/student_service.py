from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.student import Student, StudentLogin
from app.schemas.student import StudentCreate, StudentUpdate
from datetime import date
from app.core.security import get_password_hash

def get_student(db: Session, student_id: int):
    return db.get(Student, student_id)

def get_student_by_email(db: Session, email: str):
    return db.execute(select(Student).where(Student.email == email)).scalar_one_or_none()

def create_student(db: Session, student_in: StudentCreate):
    # Hash the password before saving
    student_login = StudentLogin(
        email=student_in.email,
        password=get_password_hash(student_in.password)
    )
    student = Student(
        first_name=student_in.first_name,
        last_name=student_in.last_name,
        email=student_in.email,
        phone=student_in.phone,
        reg_date=date.today(),
        login=student_login
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student

def update_student(db: Session, student_id: int, student_in: StudentUpdate):
    student = get_student(db, student_id)
    if not student:
        return None
    
    update_data = student_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student, field, value)
        
    db.add(student)
    db.commit()
    db.refresh(student)
    return student
