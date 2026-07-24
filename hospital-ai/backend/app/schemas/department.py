"""Department schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DepartmentBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=2000)
    floor_number: Optional[int] = Field(default=None, ge=-5, le=200)
    head_doctor_id: Optional[UUID] = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=2000)
    floor_number: Optional[int] = Field(default=None, ge=-5, le=200)
    head_doctor_id: Optional[UUID] = None


class DepartmentResponse(DepartmentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    doctors_count: int = 0
    # Future placeholder — always 0 for now
    patients_count: int = 0
    head_doctor_name: Optional[str] = None

    model_config = {"from_attributes": True}


class DepartmentListResponse(BaseModel):
    items: list[DepartmentResponse]
    total: int
