"""Scheduling Agent Stage 2: appointment slot recommendation."""
from __future__ import annotations
from typing import Any, Dict, List
from .models import SlotRecommendation, AppointmentSchedulingResult

class AppointmentSlotEngine:
    def recommend(self, *, slots: List[Dict[str,str]], doctor_id: str, doctor_name: str, priority_level: str, max_results: int = 6) -> AppointmentSchedulingResult:
        if not slots:
            return AppointmentSchedulingResult(rationale=["No open appointment slot was found in the requested planning window."])
        weight={"Critical":1000,"Urgent":600,"Semi-Urgent":300,"Routine":100}.get(priority_level,100)
        recs=[]
        for idx,s in enumerate(slots):
            score=weight - idx
            reasons=["Slot is within the doctor's configured availability and has no active appointment conflict."]
            if idx == 0: reasons.append("Earliest available slot is preferred for the current priority level.")
            recs.append(SlotRecommendation(doctor_id=doctor_id,doctor_name=doctor_name,appointment_date=s["appointment_date"],start_time=s["start_time"],end_time=s["end_time"],score=round(float(score),1),reasons=reasons))
        recs.sort(key=lambda x:(-x.score,x.appointment_date,x.start_time))
        return AppointmentSchedulingResult(recommended_slot=recs[0], alternatives=recs[1:max_results], rationale=["Recommendation only. Existing appointment booking validation remains the final conflict check."])
