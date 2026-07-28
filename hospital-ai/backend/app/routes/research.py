"""Research Agent API — validates and enriches Diagnosis Agent output with evidence."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser
from app.schemas.research import (
    ResearchHistoryItemOut,
    ResearchResultOut,
    ResearchStartRequest,
    ResearchStartResponse,
)
from app.services.research_service import ResearchService, get_research_service

router = APIRouter(prefix="/ai/research", tags=["research-agent"])


@router.post(
    "/start",
    response_model=ResearchStartResponse,
    summary="Run the Research Agent for a patient",
)
def start_research(
    body: ResearchStartRequest,
    _current_user: CurrentUser,
    service: Annotated[ResearchService, Depends(get_research_service)],
) -> ResearchStartResponse:
    """
    PubMed Search -> Clinical Trial Search -> Treatment Guideline Retrieval ->
    Drug Efficacy Analysis -> Evidence Ranking -> Recommendation Generation.

    Validates and enriches the latest Diagnosis Agent result with evidence.
    Never invents medical information; never prescribes medication.
    """
    return service.start(body)


@router.get("/{patient_id}", response_model=ResearchResultOut)
def get_latest_research(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ResearchService, Depends(get_research_service)],
) -> ResearchResultOut:
    return service.result(patient_id)


@router.get("/{patient_id}/history", response_model=list[ResearchHistoryItemOut])
def get_research_history(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ResearchService, Depends(get_research_service)],
    limit: int = 20,
) -> list[ResearchHistoryItemOut]:
    return service.history(patient_id, limit=limit)
