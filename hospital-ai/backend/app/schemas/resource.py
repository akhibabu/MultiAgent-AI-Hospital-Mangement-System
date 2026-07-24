"""Hospital resource schemas."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class ResourceType(str, Enum):
    BED = "Bed"
    ICU_BED = "ICU Bed"
    OPERATION_THEATRE = "Operation Theatre"
    VENTILATOR = "Ventilator"
    AMBULANCE = "Ambulance"
    WHEELCHAIR = "Wheelchair"
    MEDICAL_EQUIPMENT = "Medical Equipment"
    LABORATORY = "Laboratory"
    PHARMACY = "Pharmacy"


class ResourceStatus(str, Enum):
    AVAILABLE = "Available"
    IN_USE = "In Use"
    MAINTENANCE = "Maintenance"
    OUT_OF_SERVICE = "Out of Service"


class HospitalResourceBase(BaseModel):
    resource_name: str = Field(min_length=1, max_length=200)
    resource_type: ResourceType
    quantity: int = Field(ge=0, default=1)
    available_quantity: int = Field(ge=0, default=0)
    status: ResourceStatus = ResourceStatus.AVAILABLE
    location: Optional[str] = Field(default=None, max_length=300)
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("resource_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Resource name cannot be empty")
        return cleaned

    @model_validator(mode="after")
    def check_quantities(self) -> "HospitalResourceBase":
        if self.available_quantity > self.quantity:
            raise ValueError("Available quantity cannot exceed total quantity")
        return self


class HospitalResourceCreate(HospitalResourceBase):
    pass


class HospitalResourceUpdate(BaseModel):
    resource_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    resource_type: Optional[ResourceType] = None
    quantity: Optional[int] = Field(default=None, ge=0)
    available_quantity: Optional[int] = Field(default=None, ge=0)
    status: Optional[ResourceStatus] = None
    location: Optional[str] = Field(default=None, max_length=300)
    notes: Optional[str] = Field(default=None, max_length=2000)


class HospitalResourceResponse(HospitalResourceBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class HospitalResourceListResponse(BaseModel):
    items: List[HospitalResourceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ResourceSummaryItem(BaseModel):
    resource_type: str
    total_quantity: int
    available_quantity: int
    in_use: int


class MessageResponse(BaseModel):
    message: str
