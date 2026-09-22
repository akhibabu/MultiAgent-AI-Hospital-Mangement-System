"""Scheduling Agent — six-stage deterministic operations pipeline."""
from __future__ import annotations
from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import HTTPException
from app.core.logging import get_logger
from app.repositories.patient_context_repository import PatientClinicalContextRepository
from app.repositories.scheduling_repository import SchedulingDataRepository
from .models import SchedulingReport, DoctorWorkload
from .doctor_assignment import DoctorAssignmentEngine
from .appointment_scheduler import AppointmentSlotEngine
from .surgery_scheduler import SurgeryScheduler
from .follow_up import FollowUpPlanner
from .queue_optimizer import QueueOptimizer
from .workload_balancer import WorkloadBalancer

logger=get_logger("hospital_ai.scheduling.pipeline")

class SchedulingPipeline:
    def __init__(self, *, context_repo:Optional[PatientClinicalContextRepository]=None, data_repo:Optional[SchedulingDataRepository]=None)->None:
        self.context_repo=context_repo or PatientClinicalContextRepository(); self.data_repo=data_repo or SchedulingDataRepository()
        self.assigner=DoctorAssignmentEngine(); self.slot_engine=AppointmentSlotEngine(); self.surgery=SurgeryScheduler(); self.followup=FollowUpPlanner(); self.queue=QueueOptimizer(); self.balance=WorkloadBalancer()

    def run(self, *, patient_id:UUID, preferred_date:date, visit_type:str, reason_for_visit:str|None, department_id:UUID|None, preferred_doctor_id:UUID|None, surgery_required:bool, surgery_duration_minutes:int, follow_up_days:int)->SchedulingReport:
        context=self.context_repo.load(patient_id)
        if not context.patient_id: raise HTTPException(status_code=404,detail="Patient not found")
        warnings=list(context.validation_warnings); emergency_level="Routine"; emergency_priority=0.0
        try:
            emergency=self.data_repo.latest_emergency_priorities([str(patient_id)]).get(str(patient_id),{})
            emergency_level=str(emergency.get("priority_level") or "Routine"); emergency_priority=float(emergency.get("priority_score") or 0)
            if not emergency: warnings.append("No Emergency Agent priority result was found; Scheduling uses current request and clinical context only.")
        except Exception as exc: warnings.append(f"Emergency priority unavailable for scheduling: {exc}")
        clinical_text=" ".join([*context.conditions,*context.symptoms,*context.previous_diagnoses,reason_for_visit or ""])
        workload=self.data_repo.workload_counts(preferred_date,7)
        departments=self.data_repo.list_departments(); doctors=self.data_repo.list_doctors()
        assignment=self.assigner.assign(doctors=doctors,workload=workload,department_names=departments,preferred_doctor_id=str(preferred_doctor_id) if preferred_doctor_id else None,requested_department_id=str(department_id) if department_id else None,clinical_text=clinical_text,emergency_level=emergency_level,visit_type=visit_type)
        slots=[]
        if assignment.selected_doctor_id:
            slots=self.data_repo.open_slots(UUID(assignment.selected_doctor_id),preferred_date,14)
        appointment=self.slot_engine.recommend(slots=slots,doctor_id=assignment.selected_doctor_id or "",doctor_name=assignment.selected_doctor_name or "",priority_level=emergency_level)
        surgery_windows=[]
        if surgery_required and assignment.selected_doctor_id:
            surgery_windows=self.data_repo.open_window(UUID(assignment.selected_doctor_id),preferred_date,30,max(30,min(surgery_duration_minutes,480)))
        surgery=self.surgery.recommend(required=surgery_required,windows=surgery_windows,doctor_id=assignment.selected_doctor_id,doctor_name=assignment.selected_doctor_name,duration_minutes=surgery_duration_minutes)
        follow_date=date.fromisoformat(appointment.recommended_slot.appointment_date) if appointment.recommended_slot else preferred_date
        follow=self.followup.plan(appointment_date=follow_date,interval_days=follow_up_days,priority_level=emergency_level)
        queue_result=self.queue.optimize(doctor_id=assignment.selected_doctor_id,appointment_date=appointment.recommended_slot.appointment_date if appointment.recommended_slot else None,appointments=[],priority_by_patient={})
        loads=[]
        for d in doctors:
            did=str(d.get("id")); loads.append(DoctorWorkload(doctor_id=did,doctor_name=f"Dr. {d.get('first_name','')} {d.get('last_name','')}".strip(),active_appointments=int(workload.get(did,0)),workload_score=round(min(100.0,workload.get(did,0)/7*100),1),availability_status=str(d.get("availability_status") or "Available")))
        balancing=self.balance.balance(doctors=loads)
        if assignment.selected_doctor_id and appointment.recommended_slot:
            try:
                same_day=self.data_repo.list_active_appointments(start_date=follow_date,end_date=follow_date,doctor_id=UUID(assignment.selected_doctor_id))
                ids=[str(a.get("patient_id")) for a in same_day if a.get("patient_id")]
                names=self.data_repo.patient_names(ids); priorities=self.data_repo.latest_emergency_priorities(ids)
                for a in same_day: a["patient_name"]=names.get(str(a.get("patient_id")),"Patient")
                queue_result=self.queue.optimize(doctor_id=assignment.selected_doctor_id,appointment_date=follow_date.isoformat(),appointments=same_day,priority_by_patient=priorities)
            except Exception as exc: warnings.append(f"Queue optimization could not load existing priority data: {exc}")
        summary=(f"{context.patient_name}: Scheduling Agent assigned {assignment.selected_doctor_name or 'no doctor'} with a {assignment.selection_score}/100 assignment score, "
                 f"recommended {appointment.recommended_slot.appointment_date if appointment.recommended_slot else 'no open date'} "
                 f"{appointment.recommended_slot.start_time if appointment.recommended_slot else ''}, and produced queue/workload planning signals.")
        if emergency_priority: summary+=f" Emergency priority {emergency_level} ({emergency_priority}/100) was used."
        return SchedulingReport(patient_id=str(patient_id),patient_name=context.patient_name,emergency_priority_level=emergency_level,emergency_priority_score=emergency_priority,doctor_assignment=assignment,appointment_scheduling=appointment,surgery_scheduling=surgery,follow_up_planning=follow,queue_optimization=queue_result,workload_balancing=balancing,summary=summary,warnings=warnings)
