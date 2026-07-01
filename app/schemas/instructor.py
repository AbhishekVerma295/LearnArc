from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional

class InstructorBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    bio: Optional[str] = None

class InstructorCreate(InstructorBase):
    email: EmailStr
    password: str

class InstructorUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None

class InstructorResponse(InstructorBase):
    instructor_id: int

    model_config = ConfigDict(from_attributes=True)
