"""Scheduling Agent Stage 5: queue optimization."""
from __future__ import annotations
from datetime import time
from typing import Any, Dict, List
from .models import QueueItem, QueueOptimizationResult

LEVELS={"Critical":4,"Urgent":3,"Semi-Urgent":2,"Routine":1}
class QueueOptimizer:
    def optimize(self, *, doctor_id: str | None, appointment_date: str | None, appointments: List[Dict[str,Any]], priority_by_patient: Dict[str,Dict[str,Any]]) -> QueueOptimizationResult:
        items=[]
        for a in appointments:
            pid=str(a.get("patient_id")); p=priority_by_patient.get(pid,{})
            items.append(QueueItem(appointment_id=str(a.get("id")),patient_id=pid,patient_name=str(a.get("patient_name") or "Patient"),start_time=str(a.get("start_time") or ""),end_time=str(a.get("end_time") or ""),priority_level=str(p.get("priority_level") or "Routine"),priority_score=float(p.get("priority_score") or 0)))
        original=sorted(items,key=lambda x:x.start_time)
        ordered=sorted(items,key=lambda x:(-LEVELS.get(x.priority_level,1),-x.priority_score,x.start_time))
        for i,item in enumerate(ordered,1): item.position=i
        changed=sum(1 for a,b in zip(original,ordered) if a.appointment_id!=b.appointment_id)
        return QueueOptimizationResult(doctor_id=doctor_id,appointment_date=appointment_date,ordered_queue=ordered,changed_order_count=changed,rationale=["Emergency priority scores are used only as a decision-support queue recommendation.","The stored appointment order is not changed automatically."])
