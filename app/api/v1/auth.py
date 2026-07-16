from fastapi import APIRouter, Depends, HTTPException, Request, status
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
from app.main import limiter

router = APIRouter()

@router.post("/login/student", response_model=Token)
@limiter.limit("5/minute")
def login_student(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """Login as a student and receive a JWT Bearer token. (Rate limited: 5/min per IP)"""
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
@limiter.limit("5/minute")
def login_instructor(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """Login as an instructor and receive a JWT Bearer token. (Rate limited: 5/min per IP)"""
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
@limiter.limit("10/minute")
def register_student(
    request: Request,
    student_in: StudentCreate,
    db: Session = Depends(get_db)
):
    """Register a new student account. (Rate limited: 10/min per IP)"""
    student = get_student_by_email(db, email=student_in.email)
    if student:
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_student(db=db, student_in=student_in)

@router.post("/register/instructor", response_model=InstructorResponse)
@limiter.limit("10/minute")
def register_instructor(
    request: Request,
    instructor_in: InstructorCreate,
    db: Session = Depends(get_db)
):
    """Register a new instructor account. (Rate limited: 10/min per IP)"""
    instructor = get_instructor_by_email(db, email=instructor_in.email)
    if instructor:
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_instructor(db=db, instructor_in=instructor_in)
