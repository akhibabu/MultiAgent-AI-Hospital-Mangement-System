"""Scheduling Agent service facade."""
from __future__ import annotations
import time
from typing import Optional
from uuid import UUID
from fastapi import HTTPException
from app.ai.scheduling.pipeline import SchedulingPipeline
from app.ai.scheduling.models import SchedulingReport
from app.repositories.scheduling_result_repository import SchedulingResultRepository
from app.repositories.intake_repositories import DocumentProcessingJobRepository
from app.schemas.scheduling import SchedulingStartRequest,SchedulingStartResponse,SchedulingResultOut
from app.core.logging import get_logger

logger=get_logger("hospital_ai.scheduling.service")
class SchedulingService:
    def __init__(self,pipeline:Optional[SchedulingPipeline]=None,results:Optional[SchedulingResultRepository]=None)->None:
        self._pipeline=pipeline or SchedulingPipeline(); self._results=results or SchedulingResultRepository()
    def start(self,request:SchedulingStartRequest)->SchedulingStartResponse:
        started=time.perf_counter()
        try:
            report:SchedulingReport=self._pipeline.run(patient_id=request.patient_id,preferred_date=request.preferred_date)
        except HTTPException: raise
        except Exception as exc:
            logger.exception("Scheduling pipeline failed patient=%s",request.patient_id)
            raise HTTPException(status_code=500,detail=f"Scheduling Agent failed: {exc}") from exc
        elapsed=int((time.perf_counter()-started)*1000)
        latest_job=DocumentProcessingJobRepository().latest_for_patient(request.patient_id)
        row=self._results.create({"patient_id":str(request.patient_id),"processing_job_id":str(latest_job["id"]) if latest_job else None,"doctor_assignment_json":report.doctor_assignment.model_dump(mode="json"),"appointment_scheduling_json":report.appointment_scheduling.model_dump(mode="json"),"surgery_scheduling_json":report.surgery_scheduling.model_dump(mode="json"),"follow_up_planning_json":report.follow_up_planning.model_dump(mode="json"),"queue_optimization_json":report.queue_optimization.model_dump(mode="json"),"workload_balancing_json":report.workload_balancing.model_dump(mode="json"),"summary":report.summary,"engine":report.engine,"emergency_priority_level":report.emergency_priority_level,"emergency_priority_score":report.emergency_priority_score,"visit_type":report.visit_type,"derived_department":report.derived_department,"derived_specialists":report.derived_specialists,"surgery_recommendation_json":report.surgery_recommendation,"source_result_ids_json":report.source_result_ids,"source_availability_json":report.source_availability,"recommended_tests_json":report.recommended_tests,"recommended_imaging_json":report.recommended_imaging,"recommended_medications_json":report.recommended_medications,"treatment_validation_status":report.treatment_validation_status,"status":"Completed","warnings_json":report.warnings,"processing_time_ms":elapsed})
        return SchedulingStartResponse(patient_id=request.patient_id,status="Completed",processing_time_ms=elapsed,summary=report.summary,engine=report.engine,emergency_priority_level=report.emergency_priority_level,emergency_priority_score=report.emergency_priority_score,visit_type=report.visit_type,derived_department=report.derived_department,derived_specialists=report.derived_specialists,surgery_recommendation=report.surgery_recommendation,source_result_ids=report.source_result_ids,source_availability=report.source_availability,recommended_tests=report.recommended_tests,recommended_imaging=report.recommended_imaging,recommended_medications=report.recommended_medications,treatment_validation_status=report.treatment_validation_status,warnings=report.warnings,doctor_assignment=report.doctor_assignment,appointment_scheduling=report.appointment_scheduling,surgery_scheduling=report.surgery_scheduling,follow_up_planning=report.follow_up_planning,queue_optimization=report.queue_optimization,workload_balancing=report.workload_balancing,scheduling_result=SchedulingResultOut.model_validate(row))
    def result(self,patient_id:UUID)->SchedulingResultOut:
        row=self._results.get_latest_for_patient(patient_id)
        if not row: raise HTTPException(status_code=404,detail="No Scheduling Agent result found for this patient. Run the Scheduling Agent first.")
        return SchedulingResultOut.model_validate(row)

def get_scheduling_service()->SchedulingService: return SchedulingService()
