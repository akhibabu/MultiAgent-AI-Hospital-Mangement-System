"""Doctor domain schemas."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.patient import PatientGender


class AvailabilityStatus(str, Enum):
    AVAILABLE = "Available"
    BUSY = "Busy"
    ON_LEAVE = "On Leave"


class DoctorAIExtensions(BaseModel):
    """Extension points for future AI agents — currently unused."""

    ai_summary: Optional[str] = None
    performance_metrics: Optional[Any] = None
    predicted_workload: Optional[Any] = None
    recommended_schedule: Optional[Any] = None
    schedule_score: Optional[Any] = None


class DoctorBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)
    gender: PatientGender
    date_of_birth: Optional[date] = None
    department_id: Optional[UUID] = None
    specialization: str = Field(min_length=1, max_length=150)
    qualification: Optional[str] = Field(default=None, max_length=300)
    experience_years: int = Field(default=0, ge=0, le=80)
    license_number: Optional[str] = Field(default=None, max_length=100)
    consultation_fee: Decimal = Field(default=Decimal("0"), ge=0)
    availability_status: AvailabilityStatus = AvailabilityStatus.AVAILABLE
    profile_photo_url: Optional[str] = Field(default=None, max_length=1000)
    bio: Optional[str] = Field(default=None, max_length=5000)

    @field_validator("first_name", "last_name", "phone", "specialization")
    @classmethod
    def strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, value: Optional[date]) -> Optional[date]:
        if value is None:
            return value
        if value > date.today():
            raise ValueError("Date of birth cannot be in the future")
        if value.year < 1930:
            raise ValueError("Date of birth is unrealistically old")
        return value


class DoctorCreate(DoctorBase):
    pass


class DoctorUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, min_length=7, max_length=20)
    gender: Optional[PatientGender] = None
    date_of_birth: Optional[date] = None
    department_id: Optional[UUID] = None
    specialization: Optional[str] = Field(default=None, min_length=1, max_length=150)
    qualification: Optional[str] = Field(default=None, max_length=300)
    experience_years: Optional[int] = Field(default=None, ge=0, le=80)
    license_number: Optional[str] = Field(default=None, max_length=100)
    consultation_fee: Optional[Decimal] = Field(default=None, ge=0)
    availability_status: Optional[AvailabilityStatus] = None
    profile_photo_url: Optional[str] = Field(default=None, max_length=1000)
    bio: Optional[str] = Field(default=None, max_length=5000)


class DepartmentBrief(BaseModel):
    id: UUID
    name: str


class DoctorResponse(DoctorBase, DoctorAIExtensions):
    id: UUID
    doctor_number: str
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    department: Optional[DepartmentBrief] = None

    model_config = {"from_attributes": True}


class DoctorListResponse(BaseModel):
    items: List[DoctorResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    message: str
