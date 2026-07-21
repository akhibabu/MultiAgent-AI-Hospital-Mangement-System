"""Patient domain schemas."""

from datetime import date, datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class PatientGender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class BloodGroup(str, Enum):
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"


class PatientBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    gender: PatientGender
    blood_group: Optional[BloodGroup] = None
    phone: str = Field(min_length=7, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(default=None, max_length=500)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default="India", max_length=100)
    emergency_contact_name: Optional[str] = Field(default=None, max_length=150)
    emergency_contact_phone: Optional[str] = Field(default=None, max_length=20)
    allergies: Optional[str] = Field(default=None, max_length=2000)
    medical_history: Optional[str] = Field(default=None, max_length=5000)
    current_medications: Optional[str] = Field(default=None, max_length=2000)
    insurance_provider: Optional[str] = Field(default=None, max_length=150)
    insurance_number: Optional[str] = Field(default=None, max_length=100)

    @field_validator("first_name", "last_name", "phone")
    @classmethod
    def strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Date of birth cannot be in the future")
        if value.year < 1900:
            raise ValueError("Date of birth is unrealistically old")
        return value


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[PatientGender] = None
    blood_group: Optional[BloodGroup] = None
    phone: Optional[str] = Field(default=None, min_length=7, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(default=None, max_length=500)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    emergency_contact_name: Optional[str] = Field(default=None, max_length=150)
    emergency_contact_phone: Optional[str] = Field(default=None, max_length=20)
    allergies: Optional[str] = Field(default=None, max_length=2000)
    medical_history: Optional[str] = Field(default=None, max_length=5000)
    current_medications: Optional[str] = Field(default=None, max_length=2000)
    insurance_provider: Optional[str] = Field(default=None, max_length=150)
    insurance_number: Optional[str] = Field(default=None, max_length=100)

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, value: Optional[date]) -> Optional[date]:
        if value is None:
            return value
        if value > date.today():
            raise ValueError("Date of birth cannot be in the future")
        if value.year < 1900:
            raise ValueError("Date of birth is unrealistically old")
        return value


class PatientAIExtensions(BaseModel):
    """
    Extension points for future AI agents.
    Always present on patient payloads; currently unused (null).
    """

    ai_context: Optional[Any] = None
    latest_diagnosis: Optional[str] = None
    latest_report: Optional[Any] = None
    prediction_history: Optional[Any] = None


class PatientResponse(PatientBase, PatientAIExtensions):
    id: UUID
    patient_number: str
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PatientListResponse(BaseModel):
    items: List[PatientResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    message: str
