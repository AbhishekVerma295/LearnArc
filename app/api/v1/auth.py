from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.db.session import get_db
from app.schemas.auth import Token
from app.schemas.student import StudentCreate, StudentResponse
from app.schemas.instructor import InstructorCreate, InstructorResponse
from app.services.student_service import get_student_by_email, create_student
from app.services.instructor_service import get_instructor_by_email, create_instructor
from app.core.security import verify_password, create_access_token

router = APIRouter()

@router.post("/login/student", response_model=Token)
def login_student(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    student = get_student_by_email(db, email=form_data.username)
    if not student or not student.login or not verify_password(form_data.password, student.login.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(subject=student.email, user_type="student")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login/instructor", response_model=Token)
def login_instructor(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    instructor = get_instructor_by_email(db, email=form_data.username)
    if not instructor or not instructor.login or not verify_password(form_data.password, instructor.login.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(subject=instructor.email, user_type="instructor")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register/student", response_model=StudentResponse)
def register_student(
    student_in: StudentCreate,
    db: Session = Depends(get_db)
):
    student = get_student_by_email(db, email=student_in.email)
    if student:
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_student(db=db, student_in=student_in)

@router.post("/register/instructor", response_model=InstructorResponse)
def register_instructor(
    instructor_in: InstructorCreate,
    db: Session = Depends(get_db)
):
    instructor = get_instructor_by_email(db, email=instructor_in.email)
    if instructor:
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_instructor(db=db, instructor_in=instructor_in)
