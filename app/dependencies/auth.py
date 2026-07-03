from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.schemas.auth import TokenData
from app.models.student import Student
from app.models.instructor import Instructor
from app.services.student_service import get_student_by_email
from app.services.instructor_service import get_instructor_by_email

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login/student",
    scheme_name="JWT"
)

def get_current_user_data(token: str = Depends(reusable_oauth2)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        email: str = payload.get("sub")
        user_type: str = payload.get("user_type")
        if email is None or user_type is None:
            raise credentials_exception
        token_data = TokenData(email=email, user_type=user_type)
    except JWTError:
        raise credentials_exception
    return token_data

def get_current_student(
    token_data: TokenData = Depends(get_current_user_data),
    db: Session = Depends(get_db)
) -> Student:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token_data.user_type != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions (requires student access)"
        )
    student = get_student_by_email(db, email=token_data.email)
    if student is None:
        raise credentials_exception
    return student

def get_current_instructor(
    token_data: TokenData = Depends(get_current_user_data),
    db: Session = Depends(get_db)
) -> Instructor:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token_data.user_type != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions (requires instructor access)"
        )
    instructor = get_instructor_by_email(db, email=token_data.email)
    if instructor is None:
        raise credentials_exception
    return instructor
