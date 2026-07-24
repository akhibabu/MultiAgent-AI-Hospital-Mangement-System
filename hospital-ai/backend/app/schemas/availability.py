"""Doctor availability schemas (Scheduling Agent extension point)."""

from datetime import datetime, time
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class AvailabilityBase(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="0=Monday … 6=Sunday")
    start_time: time
    end_time: time
    slot_duration: int = Field(default=30, ge=5, le=240)
    is_available: bool = True

    @model_validator(mode="after")
    def validate_time_range(self) -> "AvailabilityBase":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class AvailabilityCreate(AvailabilityBase):
    doctor_id: UUID


class AvailabilitySlotCreate(AvailabilityBase):
    """Body for nested POST /doctors/{id}/availability (doctor_id from path)."""

    pass


class AvailabilityUpdate(BaseModel):
    day_of_week: Optional[int] = Field(default=None, ge=0, le=6)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    slot_duration: Optional[int] = Field(default=None, ge=5, le=240)
    is_available: Optional[bool] = None


class AvailabilityResponse(AvailabilityBase):
    id: UUID
    doctor_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AvailabilityListResponse(BaseModel):
    items: List[AvailabilityResponse]
    total: int
