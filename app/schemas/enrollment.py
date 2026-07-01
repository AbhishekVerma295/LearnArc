from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime
from app.models.enrollment import CourseStatusEnum

class EnrollmentCreate(BaseModel):
    course_id: int

class EnrollmentResponse(BaseModel):
    enrollment_id: int
    student_id: int
    course_id: int
    enrollment_date: Optional[date] = None
    course_status: Optional[CourseStatusEnum] = None

    model_config = ConfigDict(from_attributes=True)

class ProgressCreate(BaseModel):
    lesson_id: int

class ProgressResponse(BaseModel):
    progress_id: int
    student_id: int
    lesson_id: int
    progress_status: Optional[str] = None
    completed_timestamp: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class CertificateResponse(BaseModel):
    certificate_id: int
    student_id: int
    course_id: int
    issue_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)
