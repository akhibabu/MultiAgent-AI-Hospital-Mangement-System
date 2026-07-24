"""Doctors REST API."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.auth.dependencies import CurrentUser
from app.schemas.availability import (
    AvailabilityListResponse,
    AvailabilityResponse,
    AvailabilitySlotCreate,
)
from app.schemas.doctor import (
    AvailabilityStatus,
    DoctorCreate,
    DoctorListResponse,
    DoctorResponse,
    DoctorUpdate,
    MessageResponse,
)
from app.services.availability_service import availability_service
from app.services.doctor_service import doctor_service

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.get("", response_model=DoctorListResponse)
def list_doctors(
    _current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    department_id: Optional[UUID] = Query(None),
    availability_status: Optional[AvailabilityStatus] = Query(None),
    min_experience: Optional[int] = Query(None, ge=0),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
) -> DoctorListResponse:
    return doctor_service.list_doctors(
        page=page,
        page_size=page_size,
        search=search,
        department_id=department_id,
        availability_status=availability_status,
        min_experience=min_experience,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(doctor_id: UUID, _current_user: CurrentUser) -> DoctorResponse:
    return doctor_service.get_doctor(doctor_id)


@router.post("", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
def create_doctor(body: DoctorCreate, current_user: CurrentUser) -> DoctorResponse:
    return doctor_service.create_doctor(body, created_by=current_user.id)


@router.put("/{doctor_id}", response_model=DoctorResponse)
def update_doctor(
    doctor_id: UUID, body: DoctorUpdate, _current_user: CurrentUser
) -> DoctorResponse:
    return doctor_service.update_doctor(doctor_id, body)


@router.delete("/{doctor_id}", response_model=MessageResponse)
def delete_doctor(doctor_id: UUID, _current_user: CurrentUser) -> MessageResponse:
    doctor_service.delete_doctor(doctor_id)
    return MessageResponse(message="Doctor deleted successfully")


@router.get("/{doctor_id}/availability", response_model=AvailabilityListResponse)
def list_doctor_availability(
    doctor_id: UUID, _current_user: CurrentUser
) -> AvailabilityListResponse:
    doctor_service.get_doctor(doctor_id)
    return availability_service.list_for_doctor(doctor_id)


@router.post(
    "/{doctor_id}/availability",
    response_model=AvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_doctor_availability(
    doctor_id: UUID,
    body: AvailabilitySlotCreate,
    _current_user: CurrentUser,
) -> AvailabilityResponse:
    from app.schemas.availability import AvailabilityCreate

    doctor_service.get_doctor(doctor_id)
    payload = AvailabilityCreate(doctor_id=doctor_id, **body.model_dump())
    return availability_service.create(payload)
