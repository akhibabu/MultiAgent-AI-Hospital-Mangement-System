"""Medical Report Agent API — professional hospital documentation generation."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser
from app.schemas.medical_report import (
    GeneratedMedicalReportOut,
    MedicalReportHistoryItemOut,
    MedicalReportStartRequest,
    MedicalReportStartResponse,
    MedicalReportStatusOut,
)
from app.services.medical_report_service import (
    MedicalReportService,
    get_medical_report_service,
)

router = APIRouter(prefix="/ai/report", tags=["medical-report-agent"])


@router.post(
    "/start",
    response_model=MedicalReportStartResponse,
    summary="Run the Medical Report Agent for a patient",
)
def start_medical_report(
    body: MedicalReportStartRequest,
    _current_user: CurrentUser,
    service: Annotated[MedicalReportService, Depends(get_medical_report_service)],
) -> MedicalReportStartResponse:
    """
    Clinical Summary -> Doctor Notes Generation -> Discharge Summary ->
    Referral Letter Creation -> Insurance Documentation -> Patient Report
    Generation.

    Consumes output from every previous AI Agent. Assists — never replaces
    — clinician review and sign-off before use in an official record.
    """
    return service.start(body)


@router.get("/status/{patient_id}", response_model=MedicalReportStatusOut)
def get_medical_report_status(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[MedicalReportService, Depends(get_medical_report_service)],
) -> MedicalReportStatusOut:
    return service.status(patient_id)


@router.get("/{patient_id}", response_model=GeneratedMedicalReportOut)
def get_latest_medical_report(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[MedicalReportService, Depends(get_medical_report_service)],
) -> GeneratedMedicalReportOut:
    return service.result(patient_id)


@router.get("/{patient_id}/history", response_model=list[MedicalReportHistoryItemOut])
def get_medical_report_history(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[MedicalReportService, Depends(get_medical_report_service)],
    limit: int = 20,
) -> list[MedicalReportHistoryItemOut]:
    return service.history(patient_id, limit=limit)
