"""Insurance Agent API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser
from app.schemas.insurance import (
    InsuranceHistoryItemOut,
    InsuranceResultOut,
    InsuranceStartRequest,
    InsuranceStartResponse,
)
from app.services.insurance_service import InsuranceService, get_insurance_service

router = APIRouter(prefix="/ai/insurance", tags=["insurance-agent"])


@router.post(
    "/start",
    response_model=InsuranceStartResponse,
    summary="Run the Insurance Agent for a patient",
)
def start_insurance(
    body: InsuranceStartRequest,
    _current_user: CurrentUser,
    service: Annotated[InsuranceService, Depends(get_insurance_service)],
) -> InsuranceStartResponse:
    """Policy verification -> coverage estimate -> claim draft -> fraud screening -> preauthorization."""
    return service.start(body)


@router.get("/{patient_id}", response_model=InsuranceResultOut)
def get_latest_insurance(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[InsuranceService, Depends(get_insurance_service)],
) -> InsuranceResultOut:
    return service.result(patient_id)


@router.get("/{patient_id}/history", response_model=list[InsuranceHistoryItemOut])
def get_insurance_history(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[InsuranceService, Depends(get_insurance_service)],
    limit: int = 20,
) -> list[InsuranceHistoryItemOut]:
    return service.history(patient_id, limit=limit)
