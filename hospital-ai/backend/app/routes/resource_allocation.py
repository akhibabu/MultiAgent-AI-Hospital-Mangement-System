"""Resource Allocation Agent API routes."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser
from app.schemas.resource_allocation import (
    ResourceAllocationHistoryItemOut,
    ResourceAllocationResponse,
    ResourceAllocationStartRequest,
    ResourceAllocationStartResponse,
)
from app.services.resource_allocation_service import (
    ResourceAllocationService,
    get_resource_allocation_service,
)

router = APIRouter(prefix="/ai/resource-allocation", tags=["resource-allocation-agent"])


@router.post("/start", response_model=ResourceAllocationStartResponse)
def start_resource_allocation(
    body: ResourceAllocationStartRequest,
    _current_user: CurrentUser,
    service: Annotated[ResourceAllocationService, Depends(get_resource_allocation_service)],
) -> ResourceAllocationStartResponse:
    """Requirement detection -> availability -> priority allocation -> conflict detection."""
    return service.start(body)


@router.get("/{patient_id}", response_model=ResourceAllocationResponse)
def get_latest_resource_allocation(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ResourceAllocationService, Depends(get_resource_allocation_service)],
) -> ResourceAllocationResponse:
    return service.result(patient_id)


@router.get("/{patient_id}/history", response_model=list[ResourceAllocationHistoryItemOut])
def get_resource_allocation_history(
    patient_id: UUID,
    _current_user: CurrentUser,
    service: Annotated[ResourceAllocationService, Depends(get_resource_allocation_service)],
    limit: int = 20,
) -> list[ResourceAllocationHistoryItemOut]:
    return service.history(patient_id, limit=limit)
