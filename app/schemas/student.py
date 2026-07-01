from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import date

class StudentBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class StudentCreate(StudentBase):
    email: EmailStr
    password: str

class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

class StudentResponse(StudentBase):
    student_id: int
    reg_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)
