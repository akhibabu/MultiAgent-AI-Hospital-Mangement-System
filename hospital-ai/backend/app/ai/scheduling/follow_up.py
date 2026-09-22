"""Scheduling Agent Stage 4: follow-up planning."""
from __future__ import annotations
from datetime import date, timedelta
from .models import FollowUpPlan

class FollowUpPlanner:
    def plan(self, *, appointment_date: date, interval_days: int, priority_level: str) -> FollowUpPlan:
        interval=max(1,min(interval_days,180))
        if priority_level=="Critical": interval=min(interval,3)
        elif priority_level=="Urgent": interval=min(interval,7)
        return FollowUpPlan(recommended_date=(appointment_date+timedelta(days=interval)).isoformat(),interval_days=interval,reason=f"Planning interval adjusted for {priority_level} priority.",planning_only=True)
