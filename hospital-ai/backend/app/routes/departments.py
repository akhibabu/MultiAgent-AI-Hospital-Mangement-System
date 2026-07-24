"""Departments REST API."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.auth.dependencies import CurrentUser
from app.schemas.department import (
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.schemas.doctor import MessageResponse
from app.services.department_service import department_service

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=DepartmentListResponse)
def list_departments(
    _current_user: CurrentUser,
    search: Optional[str] = Query(None),
) -> DepartmentListResponse:
    return department_service.list_departments(search=search)


@router.get("/{department_id}", response_model=DepartmentResponse)
def get_department(
    department_id: UUID, _current_user: CurrentUser
) -> DepartmentResponse:
    return department_service.get_department(department_id)


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    body: DepartmentCreate, _current_user: CurrentUser
) -> DepartmentResponse:
    return department_service.create_department(body)


@router.put("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: UUID,
    body: DepartmentUpdate,
    _current_user: CurrentUser,
) -> DepartmentResponse:
    return department_service.update_department(department_id, body)


@router.delete("/{department_id}", response_model=MessageResponse)
def delete_department(
    department_id: UUID, _current_user: CurrentUser
) -> MessageResponse:
    department_service.delete_department(department_id)
    return MessageResponse(message="Department deleted successfully")
