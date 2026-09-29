"""Deterministic hospital capacity and flow simulator."""
from __future__ import annotations

from typing import Dict, List

from app.ai.digital_twin.models import (
    BottleneckSignal,
    DigitalTwinScenario,
    DigitalTwinSimulation,
    FlowProjection,
    HospitalTwinState,
    ProjectionMetric,
)


class DigitalTwinSimulator:
    """Run what-if scenarios without changing live hospital data."""

    _RESOURCE_RULES = {
        "Bed": lambda s: s.emergency_arrivals + s.planned_admissions - s.expected_discharges,
        "ICU Bed": lambda s: s.icu_admissions - s.icu_discharges,
        "Ventilator": lambda s: s.ventilator_demand,
        "Operation Theatre": lambda s: s.additional_theatre_demand,
    }

    def run(self, state: HospitalTwinState, scenario: DigitalTwinScenario) -> DigitalTwinSimulation:
        projections: List[ProjectionMetric] = []
        bottlenecks: List[BottleneckSignal] = []

        for resource in state.resources:
            demand_delta = 0
            rule = self._RESOURCE_RULES.get(resource.resource_type)
            if rule:
                demand_delta = int(rule(scenario))
            projected_available = max(0, resource.available_quantity - demand_delta)
            if demand_delta < 0:
                projected_available = min(resource.total_quantity, resource.available_quantity - demand_delta)
            shortage = max(0, demand_delta - resource.available_quantity)
            projected_utilization = (
                ((resource.total_quantity - projected_available) / resource.total_quantity) * 100
                if resource.total_quantity else 0.0
            )
            projected_utilization = round(min(100.0, projected_utilization), 1)
            status = "Stable"
            if shortage > 0 or projected_utilization >= 100:
                status = "Critical"
            elif projected_utilization >= 85:
                status = "High Pressure"
            elif projected_utilization >= 70:
                status = "Elevated"
            projections.append(
                ProjectionMetric(
                    resource_type=resource.resource_type,
                    baseline_available=resource.available_quantity,
                    projected_available=projected_available,
                    projected_utilization_percent=projected_utilization,
                    shortage=shortage,
                    status=status,
                )
            )
            if status != "Stable":
                severity = "Critical" if status == "Critical" else "High"
                bottlenecks.append(
                    BottleneckSignal(
                        resource_type=resource.resource_type,
                        severity=severity,
                        message=(
                            f"{resource.resource_type} reaches {projected_utilization:.1f}% projected utilization"
                            + (f" with a modeled shortage of {shortage}." if shortage else ".")
                        ),
                        current_utilization_percent=resource.utilization_percent,
                        projected_utilization_percent=projected_utilization,
                        shortage=shortage,
                    )
                )

        projected_doctors = max(0, state.staff.available_doctors - scenario.staff_absent)
        staff_shortage = max(0, scenario.staff_absent - state.staff.available_doctors)
        staff_utilization = (
            ((state.staff.total_doctors - projected_doctors) / state.staff.total_doctors) * 100
            if state.staff.total_doctors else 0.0
        )
        if staff_shortage or staff_utilization >= 85:
            bottlenecks.append(
                BottleneckSignal(
                    resource_type="Clinical Staff",
                    severity="Critical" if staff_shortage else "High",
                    message=(
                        f"{projected_doctors} doctors remain available for the modeled horizon"
                        + (f"; shortage of {staff_shortage}." if staff_shortage else ".")
                    ),
                    current_utilization_percent=state.staff.utilization_percent,
                    projected_utilization_percent=round(min(100.0, staff_utilization), 1),
                    shortage=staff_shortage,
                )
            )

        net_admissions = scenario.emergency_arrivals + scenario.planned_admissions - scenario.expected_discharges
        projected_appointments = state.flow.appointments_next_24h + scenario.additional_appointments
        current_pressure = state.operational_pressure
        bottleneck_pressure = max(
            [b.projected_utilization_percent for b in bottlenecks], default=current_pressure
        )
        flow_pressure = min(100.0, current_pressure + scenario.emergency_arrivals * 3.0 + scenario.additional_appointments * 0.5)
        projected_pressure = round(min(100.0, max(flow_pressure, bottleneck_pressure)), 1)

        flow_projection = FlowProjection(
            projected_appointments=projected_appointments,
            projected_emergency_arrivals=scenario.emergency_arrivals,
            net_admissions=net_admissions,
            projected_operational_pressure=projected_pressure,
        )

        feedback = self._feedback(bottlenecks, state, scenario)
        summary = self._summary(state, scenario, projections, flow_projection, bottlenecks)
        notes = [
            "Simulation is planning-only and does not reserve, mutate, or cancel hospital resources or appointments.",
            "Projected values are deterministic what-if estimates based on the current database snapshot and scenario assumptions.",
            "Feedback signals are advisory inputs for Emergency, Scheduling, and Resource Allocation workflows; they do not trigger those agents automatically.",
        ]
        return DigitalTwinSimulation(
            scenario=scenario,
            resource_projections=projections,
            flow_projection=flow_projection,
            bottlenecks=bottlenecks,
            feedback_signals=feedback,
            summary=summary,
            safety_notes=notes,
        )

    def _feedback(self, bottlenecks: List[BottleneckSignal], state: HospitalTwinState, scenario: DigitalTwinScenario):
        signals = []
        for b in bottlenecks:
            action = "Review capacity and rebalance resources."
            target = "resource_allocation"
            if b.resource_type in {"Bed", "ICU Bed", "Ventilator"}:
                target = "resource_allocation"
                action = f"Prioritize {b.resource_type} demand and review available inventory before the modeled horizon."
            elif b.resource_type == "Clinical Staff":
                target = "scheduling"
                action = "Rebalance clinician workload and appointment slots before the modeled horizon."
            elif b.resource_type == "Operation Theatre":
                target = "scheduling"
                action = "Re-evaluate theatre scheduling and procedure sequencing."
            signals.append({
                "target_agent": target,
                "signal": b.message,
                "recommended_action": action,
                "severity": b.severity,
            })

        emergency_pressure = state.flow.high_or_critical_emergencies + scenario.emergency_arrivals
        if emergency_pressure > 0:
            signals.append({
                "target_agent": "emergency",
                "signal": f"{emergency_pressure} high-priority emergency signal(s) are present or modeled.",
                "recommended_action": "Review triage queue, ICU readiness, and escalation thresholds.",
                "severity": "High" if emergency_pressure >= 3 else "Moderate",
            })
        return signals

    @staticmethod
    def _summary(state, scenario, projections, flow, bottlenecks) -> str:
        critical = sum(1 for b in bottlenecks if b.severity == "Critical")
        high = sum(1 for b in bottlenecks if b.severity == "High")
        if not bottlenecks:
            headline = "No modeled bottlenecks detected."
        else:
            headline = f"{critical} critical and {high} high-pressure bottleneck(s) detected."
        return (
            f"Digital Twin simulation over {scenario.horizon_hours} hour(s): "
            f"{headline} Projected appointments: {flow.projected_appointments}; "
            f"net admissions: {flow.net_admissions}; operational pressure: {flow.projected_operational_pressure:.1f}/100."
        )
