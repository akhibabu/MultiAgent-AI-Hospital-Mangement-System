"""Scheduling Agent Stage 6: workload balancing."""
from __future__ import annotations
from typing import List
from .models import DoctorWorkload, WorkloadBalancingResult

class WorkloadBalancer:
    def balance(self, *, doctors: List[DoctorWorkload], horizon_days: int = 7) -> WorkloadBalancingResult:
        ordered=sorted(doctors,key=lambda d:(d.workload_score,d.active_appointments))
        loads=[d.workload_score for d in ordered if d.availability_status!="On Leave"]
        gap=round(max(loads)-min(loads),1) if loads else 0.0
        rec=(f"Route new non-urgent work toward {ordered[0].doctor_name} first within availability constraints." if ordered else "No doctor workload data available.")
        return WorkloadBalancingResult(horizon_days=horizon_days,doctor_loads=ordered,balance_gap=gap,recommendation=rec)
