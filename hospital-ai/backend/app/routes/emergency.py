"""Emergency Agent API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser
from app.schemas.emergency import (
    EmergencyHistoryItemOut,
    EmergencyResultOut,
    EmergencyStartRequest,
    EmergencyStartResponse,
)
from app.services.emergency_service import EmergencyService, get_emergency_service

router = APIRouter(prefix="/ai/emergency", tags=["emergency-agent"])


@router.post(
    "/start",
    response_model=EmergencyStartResponse,
    summary="Run the Emergency Agent for a patient",
)
def start_emergency(
    body: EmergencyStartRequest,
    _current_user: CurrentUser,
    service: Annotated[EmergencyService, Depends(get_emergency_service)],
) -> EmergencyStartResponse:
    """
    Vital Monitoring -> Triage Classification -> Critical Event Detection ->
    ICU Requirement Prediction -> Emergency Alert Generation ->
    Patient Priority Ranking.

    Clinical decision-support only. The agent analyzes the latest structured
    patient context available in Intake and does not replace bedside monitoring
    or local emergency protocols.
    """
    return service.start(body)


@router.get("/{patient_id}", response_model=EmergencyResultOut)
def get_latest_emergency(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[EmergencyService, Depends(get_emergency_service)],
) -> EmergencyResultOut:
    return service.result(patient_id)


@router.get("/{patient_id}/history", response_model=list[EmergencyHistoryItemOut])
def get_emergency_history(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[EmergencyService, Depends(get_emergency_service)],
    limit: int = 20,
) -> list[EmergencyHistoryItemOut]:
    return service.history(patient_id, limit=limit)
