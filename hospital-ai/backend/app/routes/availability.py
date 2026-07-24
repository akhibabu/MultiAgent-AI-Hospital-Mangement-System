"""Doctor availability REST API (flat update/delete by slot id)."""

from uuid import UUID

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser
from app.schemas.availability import AvailabilityResponse, AvailabilityUpdate
from app.schemas.doctor import MessageResponse
from app.services.availability_service import availability_service

router = APIRouter(prefix="/availability", tags=["availability"])


@router.put("/{slot_id}", response_model=AvailabilityResponse)
def update_availability(
    slot_id: UUID,
    body: AvailabilityUpdate,
    _current_user: CurrentUser,
) -> AvailabilityResponse:
    return availability_service.update(slot_id, body)


@router.delete("/{slot_id}", response_model=MessageResponse)
def delete_availability(slot_id: UUID, _current_user: CurrentUser) -> MessageResponse:
    availability_service.delete(slot_id)
    return MessageResponse(message="Availability slot deleted successfully")
