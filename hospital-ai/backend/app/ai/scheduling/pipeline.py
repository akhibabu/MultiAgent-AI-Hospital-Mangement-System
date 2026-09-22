"""Scheduling Agent — six-stage deterministic operations pipeline driven by prior agents."""
from __future__ import annotations
from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import HTTPException
from app.core.logging import get_logger
from app.repositories.patient_context_repository import PatientClinicalContextRepository
from app.repositories.scheduling_repository import SchedulingDataRepository
from .context import SchedulingSourceContext
from .models import SchedulingReport, DoctorWorkload
from .doctor_assignment import DoctorAssignmentEngine
from .appointment_scheduler import AppointmentSlotEngine
from .surgery_scheduler import SurgeryScheduler
from .follow_up import FollowUpPlanner
from .queue_optimizer import QueueOptimizer
from .workload_balancer import WorkloadBalancer

logger=get_logger("hospital_ai.scheduling.pipeline")

class SchedulingPipeline:
    def __init__(self, *, context_repo:Optional[PatientClinicalContextRepository]=None, data_repo:Optional[SchedulingDataRepository]=None, source_context:Optional[SchedulingSourceContext]=None)->None:
        self.context_repo=context_repo or PatientClinicalContextRepository()
        self.data_repo=data_repo or SchedulingDataRepository()
        self.source_context=source_context or SchedulingSourceContext()
        self.assigner=DoctorAssignmentEngine()
        self.slot_engine=AppointmentSlotEngine()
        self.surgery=SurgeryScheduler()
        self.followup=FollowUpPlanner()
        self.queue=QueueOptimizer()
        self.balance=WorkloadBalancer()

    def run(self, *, patient_id:UUID, preferred_date:date)->SchedulingReport:
        context=self.context_repo.load(patient_id)
        if not context.patient_id:
            raise HTTPException(status_code=404,detail="Patient not found")

        source=self.source_context.load(patient_id)
        derived=self.source_context.derive(source)
        warnings=list(context.validation_warnings)

        for name,available in derived["sources_available"].items():
            if not available:
                warnings.append(f"No {name.replace('_',' ').title()} Agent result is available; Scheduling will use the remaining sources.")

        clinical_text=derived["clinical_text"] or "General clinical scheduling"
        workload=self.data_repo.workload_counts(preferred_date,7)
        departments=self.data_repo.list_departments()
        doctors=self.data_repo.list_doctors()

        assignment=self.assigner.assign(
            doctors=doctors,
            workload=workload,
            department_names=departments,
            preferred_doctor_id=None,
            requested_department_id=None,
            requested_department_name=derived["department"],
            preferred_specialists=derived["specialists"],
            clinical_text=clinical_text,
            emergency_level=derived["emergency_priority_level"],
            visit_type=derived["visit_type"],
        )

        slots=[]
        if assignment.selected_doctor_id:
            slots=self.data_repo.open_slots(UUID(assignment.selected_doctor_id),preferred_date,14)
        appointment=self.slot_engine.recommend(
            slots=slots,
            doctor_id=assignment.selected_doctor_id or "",
            doctor_name=assignment.selected_doctor_name or "",
            priority_level=derived["emergency_priority_level"],
        )

        surgery_duration=int(derived["surgery_duration_minutes"] or 0)
        surgery_windows=[]
        if derived["surgery_required"] and assignment.selected_doctor_id and surgery_duration:
            surgery_windows=self.data_repo.open_window(
                UUID(assignment.selected_doctor_id),preferred_date,30,surgery_duration
            )
        surgery=self.surgery.recommend(
            required=derived["surgery_required"],
            windows=surgery_windows,
            doctor_id=assignment.selected_doctor_id,
            doctor_name=assignment.selected_doctor_name,
            duration_minutes=surgery_duration or 120,
        )
        if derived["surgery_required"] and surgery_duration == 120:
            warnings.append("Upstream agents explicitly indicated surgery/procedure planning, but no procedure duration was provided. A 120-minute planning window is used only to find a candidate slot; clinical staff must confirm duration.")

        follow_days=_follow_up_days(derived["follow_up_text"], default=14)
        if not derived["follow_up_text"]:
            warnings.append("No explicit follow-up interval was found in prior agent results; a 14-day planning interval is used.")
        follow_date=date.fromisoformat(appointment.recommended_slot.appointment_date) if appointment.recommended_slot else preferred_date
        follow=self.followup.plan(appointment_date=follow_date,interval_days=follow_days,priority_level=derived["emergency_priority_level"])

        queue_result=self.queue.optimize(
            doctor_id=assignment.selected_doctor_id,
            appointment_date=appointment.recommended_slot.appointment_date if appointment.recommended_slot else None,
            appointments=[],
            priority_by_patient={},
        )

        loads=[]
        for d in doctors:
            did=str(d.get("id"))
            loads.append(DoctorWorkload(
                doctor_id=did,
                doctor_name=f"Dr. {d.get('first_name','')} {d.get('last_name','')}".strip(),
                active_appointments=int(workload.get(did,0)),
                workload_score=round(min(100.0,workload.get(did,0)/7*100),1),
                availability_status=str(d.get("availability_status") or "Available"),
            ))
        balancing=self.balance.balance(doctors=loads)

        if assignment.selected_doctor_id and appointment.recommended_slot:
            try:
                same_day=self.data_repo.list_active_appointments(
                    start_date=follow_date,end_date=follow_date,
                    doctor_id=UUID(assignment.selected_doctor_id)
                )
                ids=[str(a.get("patient_id")) for a in same_day if a.get("patient_id")]
                names=self.data_repo.patient_names(ids)
                priorities=self.data_repo.latest_emergency_priorities(ids)
                for a in same_day:
                    a["patient_name"]=names.get(str(a.get("patient_id")),"Patient")
                queue_result=self.queue.optimize(
                    doctor_id=assignment.selected_doctor_id,
                    appointment_date=follow_date.isoformat(),
                    appointments=same_day,
                    priority_by_patient=priorities,
                )
            except Exception as exc:
                warnings.append(f"Queue optimization could not load existing priority data: {exc}")

        if derived["surgery_evidence"]:
            warnings.append("Surgery/procedure planning was triggered only from explicit recommendation language found in prior agent outputs.")

        summary=(
            f"{context.patient_name}: Scheduling Agent used prior Diagnosis, Emergency, "
            f"Prescription, and Medical Report outputs to derive a {derived['visit_type']} "
            f"visit, select {assignment.selected_doctor_name or 'no doctor'}, and recommend "
            f"{appointment.recommended_slot.appointment_date if appointment.recommended_slot else 'no open date'} "
            f"{appointment.recommended_slot.start_time if appointment.recommended_slot else ''}. "
            f"Surgery planning={'required' if derived['surgery_required'] else 'not indicated from prior recommendations'}."
        )
        return SchedulingReport(
            patient_id=str(patient_id),
            patient_name=context.patient_name,
            emergency_priority_level=derived["emergency_priority_level"],
            emergency_priority_score=derived["emergency_priority_score"],
            visit_type=derived["visit_type"],
            derived_department=derived["department"],
            derived_specialists=derived["specialists"],
            surgery_recommendation=derived["surgery_evidence"],
            source_result_ids=derived["source_ids"],
            source_availability=derived["sources_available"],
            doctor_assignment=assignment,
            appointment_scheduling=appointment,
            surgery_scheduling=surgery,
            follow_up_planning=follow,
            queue_optimization=queue_result,
            workload_balancing=balancing,
            summary=summary,
            warnings=warnings,
        )

def _follow_up_days(text:str, default:int=14)->int:
    import re
    matches=re.findall(r"\\b(\\d{1,3})\\s*(?:day|days|week|weeks|month|months)\\b",text.lower())
    if not matches:
        return default
    value=int(matches[0])
    if "week" in text.lower(): value*=7
    elif "month" in text.lower(): value*=30
    return max(1,min(value,180))
