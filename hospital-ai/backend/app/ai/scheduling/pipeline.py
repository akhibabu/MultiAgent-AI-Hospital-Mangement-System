"""Scheduling Agent six-stage pipeline driven by upstream agent outputs."""
from __future__ import annotations

import re
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.scheduling.appointment_scheduler import AppointmentSlotEngine
from app.ai.scheduling.context import SchedulingSourceContext
from app.ai.scheduling.doctor_assignment import DoctorAssignmentEngine
from app.ai.scheduling.follow_up import FollowUpPlanner
from app.ai.scheduling.models import DoctorWorkload, SchedulingReport
from app.ai.scheduling.queue_optimizer import QueueOptimizer
from app.ai.scheduling.surgery_scheduler import SurgeryScheduler
from app.ai.scheduling.workload_balancer import WorkloadBalancer
from app.core.logging import get_logger
from app.repositories.patient_context_repository import PatientClinicalContextRepository
from app.repositories.scheduling_repository import SchedulingDataRepository

logger = get_logger("hospital_ai.scheduling.pipeline")


class SchedulingPipeline:
    def __init__(
        self,
        *,
        context_repo: Optional[PatientClinicalContextRepository] = None,
        data_repo: Optional[SchedulingDataRepository] = None,
        source_context: Optional[SchedulingSourceContext] = None,
    ) -> None:
        self.context_repo = context_repo or PatientClinicalContextRepository()
        self.data_repo = data_repo or SchedulingDataRepository()
        self.source_context = source_context or SchedulingSourceContext()
        self.assigner = DoctorAssignmentEngine()
        self.slot_engine = AppointmentSlotEngine()
        self.surgery = SurgeryScheduler()
        self.followup = FollowUpPlanner()
        self.queue = QueueOptimizer()
        self.balance = WorkloadBalancer()

    def run(self, *, patient_id: UUID, preferred_date: date) -> SchedulingReport:
        context = self.context_repo.load(patient_id)
        if not context.patient_id:
            raise HTTPException(status_code=404, detail="Patient not found")

        upstream = self.source_context.load(patient_id)
        derived = self.source_context.derive(upstream)
        warnings = list(context.validation_warnings)

        for name, available in derived["sources_available"].items():
            if not available:
                warnings.append(
                    f"No {name.replace('_', ' ').title()} Agent result is available; "
                    "Scheduling will use the remaining context."
                )

        if derived["surgery_conflict"]:
            warnings.append(
                "Diagnosis and Prescription Agent surgery recommendations disagree. "
                "Surgery planning is flagged for clinician review."
            )

        if derived["surgery_required"] and not derived["surgery_duration_minutes"]:
            warnings.append(
                "An upstream agent recommended surgery/procedure planning, but no "
                "procedure duration is available. No surgery slot is fabricated."
            )

        if not derived["follow_up_text"]:
            warnings.append(
                "No explicit follow-up interval was found in upstream results; "
                "a 14-day planning interval is used."
            )

        workload = self.data_repo.workload_counts(preferred_date, 7)
        departments = self.data_repo.list_departments()
        doctors = self.data_repo.list_doctors()

        assignment = self.assigner.assign(
            doctors=doctors,
            workload=workload,
            department_names=departments,
            preferred_doctor_id=None,
            requested_department_id=None,
            requested_department_name=derived["department"],
            preferred_specialists=derived["specialists"],
            clinical_text=derived["clinical_text"] or "General clinical scheduling",
            emergency_level=derived["emergency_priority_level"],
            visit_type=derived["visit_type"],
        )

        open_slots = (
            self.data_repo.open_slots(
                UUID(assignment.selected_doctor_id), preferred_date, 14
            )
            if assignment.selected_doctor_id
            else []
        )

        appointment = self.slot_engine.recommend(
            slots=open_slots,
            doctor_id=assignment.selected_doctor_id or "",
            doctor_name=assignment.selected_doctor_name or "",
            priority_level=derived["emergency_priority_level"],
        )

        surgery_windows = []
        if (
            derived["surgery_required"]
            and assignment.selected_doctor_id
            and derived["surgery_duration_minutes"]
        ):
            surgery_windows = self.data_repo.open_window(
                UUID(assignment.selected_doctor_id),
                preferred_date,
                30,
                derived["surgery_duration_minutes"],
            )

        surgery = self.surgery.recommend(
            required=derived["surgery_required"],
            procedure_names=derived["procedures"],
            windows=surgery_windows,
            doctor_id=assignment.selected_doctor_id,
            doctor_name=assignment.selected_doctor_name,
            duration_minutes=derived["surgery_duration_minutes"],
        )

        follow_days = _follow_up_days(derived["follow_up_text"], default=14)
        follow_date = (
            date.fromisoformat(appointment.recommended_slot.appointment_date)
            if appointment.recommended_slot
            else preferred_date
        )
        follow = self.followup.plan(
            appointment_date=follow_date,
            interval_days=follow_days,
            priority_level=derived["emergency_priority_level"],
        )

        queue_result = self.queue.optimize(
            doctor_id=assignment.selected_doctor_id,
            appointment_date=(
                appointment.recommended_slot.appointment_date
                if appointment.recommended_slot
                else None
            ),
            appointments=[],
            priority_by_patient={},
        )

        loads = [
            DoctorWorkload(
                doctor_id=str(doctor.get("id")),
                doctor_name=f"Dr. {doctor.get('first_name', '')} {doctor.get('last_name', '')}".strip(),
                active_appointments=int(workload.get(str(doctor.get("id")), 0)),
                workload_score=round(
                    min(100.0, workload.get(str(doctor.get("id")), 0) / 7 * 100), 1
                ),
                availability_status=str(doctor.get("availability_status") or "Available"),
            )
            for doctor in doctors
            if doctor.get("id")
        ]
        balancing = self.balance.balance(doctors=loads)

        if assignment.selected_doctor_id and follow_date:
            try:
                existing = self.data_repo.list_active_appointments(
                    start_date=follow_date,
                    end_date=follow_date,
                    doctor_id=UUID(assignment.selected_doctor_id),
                )
                patient_ids = [
                    str(row.get("patient_id"))
                    for row in existing
                    if row.get("patient_id")
                ]
                names = self.data_repo.patient_names(patient_ids)
                priorities = self.data_repo.latest_emergency_priorities(patient_ids)
                for row in existing:
                    row["patient_name"] = names.get(
                        str(row.get("patient_id")), "Patient"
                    )
                queue_result = self.queue.optimize(
                    doctor_id=assignment.selected_doctor_id,
                    appointment_date=follow_date.isoformat(),
                    appointments=existing,
                    priority_by_patient=priorities,
                )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Queue optimization could not load current queue: {exc}")

        summary = (
            f"{context.patient_name}: Scheduling combined the latest Diagnosis, "
            f"Emergency, Prescription, and Medical Report outputs. It derived a "
            f"{derived['visit_type']} visit, recommended {assignment.selected_doctor_name or 'no doctor'}, "
            f"and produced appointment, surgery, follow-up, queue, and workload plans."
        )

        return SchedulingReport(
            patient_id=str(patient_id),
            patient_name=context.patient_name,
            emergency_priority_level=derived["emergency_priority_level"],
            emergency_priority_score=derived["emergency_priority_score"],
            visit_type=derived["visit_type"],
            derived_department=derived["department"],
            derived_specialists=derived["specialists"],
            procedures=derived["procedures"],
            surgery_recommendation=derived["surgery_evidence"],
            surgery_sources=derived["surgery_sources"],
            surgery_conflict=derived["surgery_conflict"],
            recommended_tests=derived["recommended_tests"],
            recommended_imaging=derived["recommended_imaging"],
            recommended_medications=derived["medications"],
            treatment_modes=derived["treatment_modes"],
            treatment_validation_status=derived["validation_status"],
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


def _follow_up_days(text: str, default: int = 14) -> int:
    matches = re.findall(
        r"\b(\d{1,3})\s*(?:day|days|week|weeks|month|months)\b",
        text.lower(),
    )
    if not matches:
        return default
    value = int(matches[0])
    lower = text.lower()
    if "week" in lower:
        value *= 7
    elif "month" in lower:
        value *= 30
    return max(1, min(value, 180))
