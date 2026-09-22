"""Scheduling Agent Stage 3: surgery planning recommendation."""
from __future__ import annotations
from typing import Dict, List
from .models import SlotRecommendation, SurgerySchedulingResult

class SurgeryScheduler:
    def recommend(self, *, required: bool, windows: List[Dict[str,str]], doctor_id: str | None, doctor_name: str | None, duration_minutes: int) -> SurgerySchedulingResult:
        if not required:
            return SurgerySchedulingResult(required=False, notes=["No surgery was requested for this scheduling run."])
        if not doctor_id or not doctor_name:
            return SurgerySchedulingResult(required=True, notes=["No assigned doctor is available for surgery planning."])
        if not windows:
            return SurgerySchedulingResult(required=True, notes=["No open surgery planning window was found in the planning horizon."])
        w=windows[0]
        slot=SlotRecommendation(doctor_id=doctor_id,doctor_name=doctor_name,appointment_date=w["appointment_date"],start_time=w["start_time"],end_time=w["end_time"],score=100.0,reasons=[f"Open doctor window supports the requested {duration_minutes}-minute planning duration.","Operating theatre/resource availability is intentionally deferred to the Resource Allocation Agent."])
        return SurgerySchedulingResult(required=True,recommended_slot=slot,notes=["Planning recommendation only — no operating theatre is reserved.","Resource Allocation Agent must validate theatre, staff, equipment, and bed requirements downstream."])
