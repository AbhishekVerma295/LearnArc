from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date
from app.models.course import CourseLevelEnum

class LessonBase(BaseModel):
    lesson_title: str
    lesson_number: int
    duration_minutes: Optional[int] = None
    content_url: Optional[str] = None

class LessonCreate(LessonBase):
    pass

class LessonUpdate(BaseModel):
    lesson_title: Optional[str] = None
    lesson_number: Optional[int] = None
    duration_minutes: Optional[int] = None
    content_url: Optional[str] = None

class LessonResponse(LessonBase):
    lesson_id: int
    module_id: int

    model_config = ConfigDict(from_attributes=True)


class ModuleBase(BaseModel):
    module_title: str
    module_order: int

class ModuleCreate(ModuleBase):
    pass

class ModuleUpdate(BaseModel):
    module_title: Optional[str] = None
    module_order: Optional[int] = None

class ModuleResponse(ModuleBase):
    module_id: int
    course_id: int
    lessons: List[LessonResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CourseBase(BaseModel):
    title: str
    description: Optional[str] = None
    level: Optional[CourseLevelEnum] = None

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    level: Optional[CourseLevelEnum] = None

class CourseResponse(CourseBase):
    course_id: int
    instructor_id: int
    created_date: Optional[date] = None
    modules: List[ModuleResponse] = []

    model_config = ConfigDict(from_attributes=True)
