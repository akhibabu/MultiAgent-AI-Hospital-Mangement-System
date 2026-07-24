"""Hospital resources REST API."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.auth.dependencies import CurrentUser
from app.schemas.resource import (
    HospitalResourceCreate,
    HospitalResourceListResponse,
    HospitalResourceResponse,
    HospitalResourceUpdate,
    MessageResponse,
    ResourceStatus,
    ResourceType,
)
from app.services.resource_service import resource_service

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("", response_model=HospitalResourceListResponse)
def list_resources(
    _current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    resource_type: Optional[ResourceType] = Query(None),
    status: Optional[ResourceStatus] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
) -> HospitalResourceListResponse:
    return resource_service.list_resources(
        page=page,
        page_size=page_size,
        search=search,
        resource_type=resource_type,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{resource_id}", response_model=HospitalResourceResponse)
def get_resource(resource_id: UUID, _current_user: CurrentUser) -> HospitalResourceResponse:
    return resource_service.get_resource(resource_id)


@router.post("", response_model=HospitalResourceResponse, status_code=status.HTTP_201_CREATED)
def create_resource(
    body: HospitalResourceCreate, _current_user: CurrentUser
) -> HospitalResourceResponse:
    return resource_service.create_resource(body)


@router.put("/{resource_id}", response_model=HospitalResourceResponse)
def update_resource(
    resource_id: UUID, body: HospitalResourceUpdate, _current_user: CurrentUser
) -> HospitalResourceResponse:
    return resource_service.update_resource(resource_id, body)


@router.delete("/{resource_id}", response_model=MessageResponse)
def delete_resource(resource_id: UUID, _current_user: CurrentUser) -> MessageResponse:
    resource_service.delete_resource(resource_id)
    return MessageResponse(message="Resource deleted successfully")
