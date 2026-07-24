"""Appointments REST API."""

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.auth.dependencies import CurrentUser
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentReschedule,
    AppointmentResponse,
    AppointmentStatus,
    AppointmentStatusUpdate,
    AppointmentUpdate,
    AvailableSlotsResponse,
    MessageResponse,
    VisitType,
)
from app.services.appointment_service import appointment_service

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("/slots", response_model=AvailableSlotsResponse)
def get_available_slots(
    _current_user: CurrentUser,
    doctor_id: UUID = Query(...),
    appointment_date: date = Query(...),
) -> AvailableSlotsResponse:
    return appointment_service.get_available_slots(doctor_id, appointment_date)


@router.get("", response_model=AppointmentListResponse)
def list_appointments(
    _current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    doctor_id: Optional[UUID] = Query(None),
    patient_id: Optional[UUID] = Query(None),
    department_id: Optional[UUID] = Query(None),
    status: Optional[AppointmentStatus] = Query(None),
    visit_type: Optional[VisitType] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    sort_by: str = Query("appointment_date"),
    sort_order: str = Query("desc"),
) -> AppointmentListResponse:
    return appointment_service.list_appointments(
        page=page,
        page_size=page_size,
        search=search,
        doctor_id=doctor_id,
        patient_id=patient_id,
        department_id=department_id,
        status_filter=status,
        visit_type=visit_type,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: UUID, _current_user: CurrentUser
) -> AppointmentResponse:
    return appointment_service.get_appointment(appointment_id)


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    body: AppointmentCreate, current_user: CurrentUser
) -> AppointmentResponse:
    return appointment_service.create_appointment(body, created_by=current_user.id)


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: UUID, body: AppointmentUpdate, _current_user: CurrentUser
) -> AppointmentResponse:
    return appointment_service.update_appointment(appointment_id, body)


@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
def reschedule_appointment(
    appointment_id: UUID, body: AppointmentReschedule, _current_user: CurrentUser
) -> AppointmentResponse:
    return appointment_service.reschedule_appointment(appointment_id, body)


@router.post("/{appointment_id}/status", response_model=AppointmentResponse)
def update_appointment_status(
    appointment_id: UUID, body: AppointmentStatusUpdate, _current_user: CurrentUser
) -> AppointmentResponse:
    return appointment_service.update_status(appointment_id, body)


@router.delete("/{appointment_id}", response_model=MessageResponse)
def delete_appointment(
    appointment_id: UUID, _current_user: CurrentUser
) -> MessageResponse:
    appointment_service.delete_appointment(appointment_id)
    return MessageResponse(message="Appointment deleted successfully")
