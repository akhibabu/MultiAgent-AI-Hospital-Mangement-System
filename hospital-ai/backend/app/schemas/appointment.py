"""Appointment domain schemas."""

from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class AppointmentStatus(str, Enum):
    SCHEDULED = "Scheduled"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    NO_SHOW = "No Show"
    RESCHEDULED = "Rescheduled"


class VisitType(str, Enum):
    CONSULTATION = "Consultation"
    FOLLOW_UP = "Follow Up"
    EMERGENCY = "Emergency"
    TELEMEDICINE = "Telemedicine"


ACTIVE_STATUSES = frozenset(
    {
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.RESCHEDULED,
    }
)


class AppointmentAIExtensions(BaseModel):
    """Extension points for future AI agents — currently unused."""

    predicted_wait_time: Optional[int] = None
    priority_score: Optional[Decimal] = None
    recommended_slot: Optional[Any] = None
    ai_notes: Optional[str] = None


class PatientBrief(BaseModel):
    id: UUID
    patient_number: str
    first_name: str
    last_name: str


class DoctorBrief(BaseModel):
    id: UUID
    doctor_number: str
    first_name: str
    last_name: str
    specialization: Optional[str] = None


class DepartmentBrief(BaseModel):
    id: UUID
    name: str


class AppointmentBase(BaseModel):
    patient_id: UUID
    doctor_id: UUID
    department_id: Optional[UUID] = None
    appointment_date: date
    start_time: time
    end_time: time
    visit_type: VisitType = VisitType.CONSULTATION
    reason_for_visit: Optional[str] = Field(default=None, max_length=2000)
    notes: Optional[str] = Field(default=None, max_length=5000)

    @field_validator("reason_for_visit", "notes")
    @classmethod
    def strip_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_times(self) -> "AppointmentBase":
        if self.end_time <= self.start_time:
            raise ValueError("End time must be after start time")
        start_m = self.start_time.hour * 60 + self.start_time.minute
        end_m = self.end_time.hour * 60 + self.end_time.minute
        duration = end_m - start_m
        if duration < 5:
            raise ValueError("Appointment must be at least 5 minutes")
        if duration > 480:
            raise ValueError("Appointment cannot exceed 8 hours")
        return self


class AppointmentCreate(AppointmentBase):
    status: AppointmentStatus = AppointmentStatus.SCHEDULED


class AppointmentUpdate(BaseModel):
    patient_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    appointment_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: Optional[AppointmentStatus] = None
    visit_type: Optional[VisitType] = None
    reason_for_visit: Optional[str] = Field(default=None, max_length=2000)
    notes: Optional[str] = Field(default=None, max_length=5000)

    @field_validator("reason_for_visit", "notes")
    @classmethod
    def strip_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class AppointmentReschedule(BaseModel):
    appointment_date: date
    start_time: time
    end_time: time
    notes: Optional[str] = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def validate_times(self) -> "AppointmentReschedule":
        if self.end_time <= self.start_time:
            raise ValueError("End time must be after start time")
        start_m = self.start_time.hour * 60 + self.start_time.minute
        end_m = self.end_time.hour * 60 + self.end_time.minute
        duration = end_m - start_m
        if duration < 5:
            raise ValueError("Appointment must be at least 5 minutes")
        if duration > 480:
            raise ValueError("Appointment cannot exceed 8 hours")
        return self


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus
    notes: Optional[str] = Field(default=None, max_length=5000)


class AppointmentResponse(AppointmentAIExtensions, AppointmentBase):
    id: UUID
    appointment_number: str
    status: AppointmentStatus
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    patient: Optional[PatientBrief] = None
    doctor: Optional[DoctorBrief] = None
    department: Optional[DepartmentBrief] = None


class AppointmentListResponse(BaseModel):
    items: List[AppointmentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AvailableSlot(BaseModel):
    start_time: time
    end_time: time


class AvailableSlotsResponse(BaseModel):
    doctor_id: UUID
    appointment_date: date
    day_of_week: int
    available_days: List[int]
    slots: List[AvailableSlot]
    message: Optional[str] = None


class MessageResponse(BaseModel):
    message: str
