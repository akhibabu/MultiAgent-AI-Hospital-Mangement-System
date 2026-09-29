"""Hospital Digital Twin API routes."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import CurrentUser
from app.schemas.digital_twin import (
    DigitalTwinHistoryItemOut,
    DigitalTwinRunOut,
    DigitalTwinScenarioRequest,
    DigitalTwinStateResponse,
)
from app.services.digital_twin_service import DigitalTwinService

router = APIRouter(prefix="/ai/digital-twin", tags=["digital-twin"])


def get_digital_twin_service() -> DigitalTwinService:
    return DigitalTwinService()


@router.get("/state", response_model=DigitalTwinStateResponse, summary="Read the live hospital Digital Twin state")
def get_digital_twin_state(
    _current_user: CurrentUser,
    service: Annotated[DigitalTwinService, Depends(get_digital_twin_service)],
) -> DigitalTwinStateResponse:
    """Build a read-only mirror from Resources, Scheduling, Emergency, and staff data."""
    return service.state()


@router.post("/simulate", response_model=DigitalTwinRunOut, summary="Run a hospital what-if simulation")
def simulate_digital_twin(
    body: DigitalTwinScenarioRequest,
    _current_user: CurrentUser,
    service: Annotated[DigitalTwinService, Depends(get_digital_twin_service)],
) -> DigitalTwinRunOut:
    """Simulate capacity and flow changes without mutating source tables."""
    return service.simulate(body)


@router.get("/latest", response_model=DigitalTwinRunOut, summary="Get the latest Digital Twin simulation")
def get_latest_digital_twin(
    _current_user: CurrentUser,
    service: Annotated[DigitalTwinService, Depends(get_digital_twin_service)],
) -> DigitalTwinRunOut:
    return service.latest()


@router.get("/history", response_model=list[DigitalTwinHistoryItemOut], summary="List recent Digital Twin simulations")
def get_digital_twin_history(
    _current_user: CurrentUser,
    service: Annotated[DigitalTwinService, Depends(get_digital_twin_service)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[DigitalTwinHistoryItemOut]:
    return service.history(limit=limit)
