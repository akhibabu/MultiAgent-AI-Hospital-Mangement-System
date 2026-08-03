"""Prescription Agent API — physician-review treatment recommendations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser
from app.schemas.prescription import (
    PrescriptionHistoryItemOut,
    PrescriptionResultOut,
    PrescriptionStartRequest,
    PrescriptionStartResponse,
    PrescriptionStatusOut,
)
from app.services.prescription_service import PrescriptionService, get_prescription_service

router = APIRouter(prefix="/ai/prescription", tags=["prescription-agent"])


@router.post(
    "/start",
    response_model=PrescriptionStartResponse,
    summary="Run the Prescription Agent for a patient",
)
def start_prescription(
    body: PrescriptionStartRequest,
    _current_user: CurrentUser,
    service: Annotated[PrescriptionService, Depends(get_prescription_service)],
) -> PrescriptionStartResponse:
    """
    Medication Selection -> Drug Interaction Check -> Allergy Verification ->
    Dosage Optimization -> Treatment Plan Creation -> Prescription Validation.

    Consumes Diagnosis Agent results, Research Agent evidence, and Patient
    Context. Never a final prescription — never replaces a physician.
    """
    return service.start(body)


@router.get("/status/{patient_id}", response_model=PrescriptionStatusOut)
def get_prescription_status(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[PrescriptionService, Depends(get_prescription_service)],
) -> PrescriptionStatusOut:
    return service.status(patient_id)


@router.get("/{patient_id}", response_model=PrescriptionResultOut)
def get_latest_prescription(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[PrescriptionService, Depends(get_prescription_service)],
) -> PrescriptionResultOut:
    return service.result(patient_id)


@router.get("/{patient_id}/history", response_model=list[PrescriptionHistoryItemOut])
def get_prescription_history(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[PrescriptionService, Depends(get_prescription_service)],
    limit: int = 20,
) -> list[PrescriptionHistoryItemOut]:
    return service.history(patient_id, limit=limit)
