"""Scheduling Agent Stage 3: surgery planning recommendation."""
from __future__ import annotations
from typing import Dict, List
from .models import SlotRecommendation, SurgerySchedulingResult

class SurgeryScheduler:
    def recommend(self, *, required: bool, procedure_names: List[str], windows: List[Dict[str,str]], doctor_id: str | None, doctor_name: str | None, duration_minutes: int) -> SurgerySchedulingResult:
        if not required:
            return SurgerySchedulingResult(required=False, procedure_names=procedure_names, duration_minutes=duration_minutes or None, notes=["No upstream agent has indicated surgery or operative procedure planning."])
        if not doctor_id or not doctor_name:
            return SurgerySchedulingResult(required=True, procedure_names=procedure_names, duration_minutes=duration_minutes or None, notes=["Upstream agents indicate surgery/procedure planning, but no assigned doctor is available."])
        if not windows:
            note = ("An upstream procedure recommendation exists, but no procedure duration is available. No surgery slot is fabricated; Resource Allocation or a clinical agent must provide the duration." if not duration_minutes else "No open surgery planning window was found in the planning horizon.")
            return SurgerySchedulingResult(required=True, procedure_names=procedure_names, duration_minutes=duration_minutes or None, notes=[note])
        w=windows[0]
        slot=SlotRecommendation(doctor_id=doctor_id,doctor_name=doctor_name,appointment_date=w["appointment_date"],start_time=w["start_time"],end_time=w["end_time"],score=100.0,reasons=[f"Open doctor window supports the requested {duration_minutes}-minute planning duration.","Operating theatre/resource availability is intentionally deferred to the Resource Allocation Agent."])
        return SurgerySchedulingResult(required=True, procedure_names=procedure_names, duration_minutes=duration_minutes, recommended_slot=slot, notes=["Planning recommendation only — no operating theatre is reserved.","Resource Allocation Agent must validate theatre, staff, equipment, and bed requirements downstream."])
