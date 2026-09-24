"""Scheduling Agent Stage 6: workload balancing."""
from __future__ import annotations
from typing import List
from .models import DoctorWorkload, WorkloadBalancingResult

class WorkloadBalancer:
    def balance(self, *, doctors: List[DoctorWorkload], horizon_days: int = 7) -> WorkloadBalancingResult:
        eligible=[d for d in doctors if d.availability_status != "On Leave"]
        ordered=sorted(
            doctors,
            key=lambda d:(d.workload_score,d.active_appointments),
        )
        eligible_ordered=sorted(
            eligible,
            key=lambda d:(d.workload_score,d.active_appointments),
        )
        loads=[d.workload_score for d in eligible_ordered]
        gap=round(max(loads)-min(loads),1) if loads else 0.0
        if eligible_ordered:
            rec=f"Route new non-urgent work toward {eligible_ordered[0].doctor_name} first within availability constraints."
        else:
            rec="No available doctor workload data available."
        return WorkloadBalancingResult(
            horizon_days=horizon_days,
            doctor_loads=ordered,
            balance_gap=gap,
            recommendation=rec,
        )
