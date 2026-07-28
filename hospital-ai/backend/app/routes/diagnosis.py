"""Diagnosis Agent API — Clinical Decision Support (assists, never replaces, a physician)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser
from app.schemas.diagnosis import (
    DiagnosisHistoryItemOut,
    DiagnosisResultOut,
    DiagnosisStartRequest,
    DiagnosisStartResponse,
)
from app.services.diagnosis_service import DiagnosisService, get_diagnosis_service

router = APIRouter(prefix="/ai/diagnosis", tags=["diagnosis-agent"])


@router.post(
    "/start",
    response_model=DiagnosisStartResponse,
    summary="Run the Diagnosis Agent for a patient",
)
def start_diagnosis(
    body: DiagnosisStartRequest,
    _current_user: CurrentUser,
    service: Annotated[DiagnosisService, Depends(get_diagnosis_service)],
) -> DiagnosisStartResponse:
    """
    Symptom Analysis -> Differential Diagnosis -> Disease Probability Scoring ->
    Severity Prediction -> Treatment Path Recommendation -> Clinical Decision Support.

    Consumes only the Intake Agent's Patient Context and Knowledge Graph.
    Clinical decision-support only — never a diagnosis of certainty, never
    prescribes medication, never replaces a physician.
    """
    return service.start(body)


@router.get("/{patient_id}", response_model=DiagnosisResultOut)
def get_latest_diagnosis(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[DiagnosisService, Depends(get_diagnosis_service)],
) -> DiagnosisResultOut:
    return service.result(patient_id)


@router.get("/{patient_id}/history", response_model=list[DiagnosisHistoryItemOut])
def get_diagnosis_history(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[DiagnosisService, Depends(get_diagnosis_service)],
    limit: int = 20,
) -> list[DiagnosisHistoryItemOut]:
    return service.history(patient_id, limit=limit)
