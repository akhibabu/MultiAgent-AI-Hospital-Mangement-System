"""Medical record domain schemas + AI / RAG extension points."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class MedicalRecordType(str, Enum):
    CONSULTATION = "Consultation"
    PRESCRIPTION = "Prescription"
    LAB_REPORT = "Lab Report"
    X_RAY = "X-Ray"
    MRI = "MRI"
    CT_SCAN = "CT Scan"
    ULTRASOUND = "Ultrasound"
    DISCHARGE_SUMMARY = "Discharge Summary"
    VACCINATION = "Vaccination"
    OTHER = "Other"


class MedicalAuditAction(str, Enum):
    CREATED = "Created"
    UPDATED = "Updated"
    DELETED = "Deleted"
    UPLOADED_FILE = "Uploaded File"
    DELETED_FILE = "Deleted File"


class MedicalRecordAIExtensions(BaseModel):
    """Extension points for future AI / RAG agents — currently unused."""

    ai_summary: Optional[str] = None
    detected_conditions: Optional[Any] = None
    risk_score: Optional[Decimal] = None
    recommended_tests: Optional[Any] = None
    embedding_id: Optional[str] = None
    vector_status: Optional[str] = None
    ocr_status: Optional[str] = None


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


class AppointmentBrief(BaseModel):
    id: UUID
    appointment_number: str
    appointment_date: Optional[str] = None


class MedicalRecordBase(BaseModel):
    patient_id: UUID
    appointment_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    record_type: MedicalRecordType = MedicalRecordType.CONSULTATION
    title: str = Field(min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=5000)
    diagnosis: Optional[str] = Field(default=None, max_length=5000)
    treatment: Optional[str] = Field(default=None, max_length=5000)
    notes: Optional[str] = Field(default=None, max_length=5000)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Title cannot be empty")
        return cleaned

    @field_validator("description", "diagnosis", "treatment", "notes")
    @classmethod
    def strip_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class MedicalRecordCreate(MedicalRecordBase):
    pass


class MedicalRecordUpdate(BaseModel):
    patient_id: Optional[UUID] = None
    appointment_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    record_type: Optional[MedicalRecordType] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=5000)
    diagnosis: Optional[str] = Field(default=None, max_length=5000)
    treatment: Optional[str] = Field(default=None, max_length=5000)
    notes: Optional[str] = Field(default=None, max_length=5000)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Title cannot be empty")
        return cleaned


class MedicalDocumentResponse(BaseModel):
    id: UUID
    medical_record_id: UUID
    file_name: str
    file_url: str
    storage_path: str
    file_type: str
    file_size: int
    uploaded_by: Optional[UUID] = None
    created_at: datetime
    signed_url: Optional[str] = None


class MedicalRecordResponse(MedicalRecordAIExtensions, MedicalRecordBase):
    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    patient: Optional[PatientBrief] = None
    doctor: Optional[DoctorBrief] = None
    appointment: Optional[AppointmentBrief] = None
    documents: List[MedicalDocumentResponse] = Field(default_factory=list)


class MedicalRecordListResponse(BaseModel):
    items: List[MedicalRecordResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MedicalRecordAuditResponse(BaseModel):
    id: UUID
    record_id: Optional[UUID] = None
    document_id: Optional[UUID] = None
    action: MedicalAuditAction
    performed_by: Optional[UUID] = None
    details: Optional[Any] = None
    timestamp: datetime


class MedicalRecordAuditListResponse(BaseModel):
    items: List[MedicalRecordAuditResponse]
    total: int


class MessageResponse(BaseModel):
    message: str
