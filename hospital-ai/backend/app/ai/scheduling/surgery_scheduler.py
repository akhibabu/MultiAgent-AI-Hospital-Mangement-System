"""Scheduling Agent Stage 3: surgery/procedure planning."""
from __future__ import annotations

from typing import Dict, List

from .models import SlotRecommendation, SurgerySchedulingResult


class SurgeryScheduler:
    def recommend(
        self,
        *,
        required: bool,
        procedure_names: List[str],
        windows: List[Dict[str, str]],
        doctor_id: str | None,
        doctor_name: str | None,
        duration_minutes: int,
    ) -> SurgerySchedulingResult:
        if not required:
            return SurgerySchedulingResult(
                required=False,
                procedure_names=procedure_names,
                duration_minutes=duration_minutes or None,
                resource_allocation_required=False,
                notes=[
                    "No upstream agent has indicated surgery or operative procedure planning."
                ],
            )

        if not doctor_id or not doctor_name:
            return SurgerySchedulingResult(
                required=True,
                procedure_names=procedure_names,
                duration_minutes=duration_minutes or None,
                resource_allocation_required=True,
                notes=[
                    "Upstream agents indicate surgery/procedure planning, "
                    "but no assigned doctor is available."
                ],
            )

        if not duration_minutes:
            return SurgerySchedulingResult(
                required=True,
                procedure_names=procedure_names,
                duration_minutes=None,
                resource_allocation_required=True,
                notes=[
                    "An upstream procedure recommendation exists, but no procedure "
                    "duration was supplied. No surgery slot is fabricated.",
                    "A future Resource Allocation Agent or upstream clinical output "
                    "must supply the duration before an operating window can be planned.",
                ],
            )

        if not windows:
            return SurgerySchedulingResult(
                required=True,
                procedure_names=procedure_names,
                duration_minutes=duration_minutes,
                resource_allocation_required=True,
                notes=[
                    "No open surgery planning window was found in the planning horizon.",
                ],
            )

        window = windows[0]
        slot = SlotRecommendation(
            doctor_id=doctor_id,
            doctor_name=doctor_name,
            appointment_date=window["appointment_date"],
            start_time=window["start_time"],
            end_time=window["end_time"],
            score=100.0,
            reasons=[
                f"Open doctor window supports the upstream {duration_minutes}-minute "
                "procedure duration.",
                "Operating theatre/resource availability is deferred to the "
                "Resource Allocation Agent.",
            ],
        )

        return SurgerySchedulingResult(
            required=True,
            procedure_names=procedure_names,
            duration_minutes=duration_minutes,
            recommended_slot=slot,
            resource_allocation_required=True,
            notes=[
                "Planning recommendation only. No operating theatre is reserved.",
                "Resource Allocation Agent must validate theatre, staff, equipment, "
                "and bed requirements downstream.",
            ],
        )
