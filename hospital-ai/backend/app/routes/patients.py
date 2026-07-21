"""Patients REST API."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.auth.dependencies import CurrentUser
from app.core.logging import get_logger
from app.schemas.patient import (
    BloodGroup,
    MessageResponse,
    PatientCreate,
    PatientGender,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)
from app.services.patient_service import patient_service

logger = get_logger("hospital_ai.routes.patients")

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get(
    "",
    response_model=PatientListResponse,
    summary="List patients with search, filters, pagination",
)
def list_patients(
    _current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, description="Name, patient number, or phone"),
    gender: Optional[PatientGender] = Query(None),
    blood_group: Optional[BloodGroup] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
) -> PatientListResponse:
    return patient_service.list_patients(
        page=page,
        page_size=page_size,
        search=search,
        gender=gender,
        blood_group=blood_group,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Get a patient by id",
)
def get_patient(patient_id: UUID, _current_user: CurrentUser) -> PatientResponse:
    return patient_service.get_patient(patient_id)


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient",
)
def create_patient(
    body: PatientCreate,
    current_user: CurrentUser,
) -> PatientResponse:
    return patient_service.create_patient(body, created_by=current_user.id)


@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Update patient details",
)
def update_patient(
    patient_id: UUID,
    body: PatientUpdate,
    _current_user: CurrentUser,
) -> PatientResponse:
    return patient_service.update_patient(patient_id, body)


@router.delete(
    "/{patient_id}",
    response_model=MessageResponse,
    summary="Delete a patient",
)
def delete_patient(patient_id: UUID, _current_user: CurrentUser) -> MessageResponse:
    patient_service.delete_patient(patient_id)
    return MessageResponse(message="Patient deleted successfully")
