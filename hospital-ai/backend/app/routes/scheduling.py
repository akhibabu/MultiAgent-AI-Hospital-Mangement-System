"""Scheduling Agent API routes."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends
from app.auth.dependencies import CurrentUser
from app.schemas.scheduling import SchedulingStartRequest,SchedulingStartResponse,SchedulingResultOut
from app.services.scheduling_service import SchedulingService,get_scheduling_service
router=APIRouter(prefix="/ai/scheduling",tags=["scheduling-agent"])
@router.post("/start",response_model=SchedulingStartResponse,summary="Run the Scheduling Agent")
def start_scheduling(body:SchedulingStartRequest,_current_user:CurrentUser,service:Annotated[SchedulingService,Depends(get_scheduling_service)])->SchedulingStartResponse:
    """Doctor Assignment -> Appointment Scheduling -> Surgery Scheduling -> Follow-Up Planning -> Queue Optimization -> Workload Balancing."""
    return service.start(body)
@router.get("/{patient_id}",response_model=SchedulingResultOut)
def get_latest_scheduling(patient_id:UUID,_current_user:CurrentUser,service:Annotated[SchedulingService,Depends(get_scheduling_service)])->SchedulingResultOut:
    return service.result(patient_id)
