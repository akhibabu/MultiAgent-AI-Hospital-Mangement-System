"""Deterministic operational validation for Emergency, Scheduling, and Resource Allocation.

This suite is an engineering/behavioral validation layer for the three
deterministic agents. It intentionally does NOT claim clinical accuracy or
real-world operational performance because no clinician-labelled ground truth
dataset is supplied here.

Run from hospital-ai:
    python validation/pipeline/run_operational_validation.py
    python validation/pipeline/run_operational_validation.py --output validation/results/operational/report.json

The cases are synthetic verification fixtures derived from the agents'
documented contracts and implementation rules. They are used to check
thresholds, invariants, cross-stage behavior, and expected planning semantics.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@dataclass
class CheckResult:
    agent: str
    case_id: str
    check: str
    passed: bool
    details: str


def check(agent: str, case_id: str, name: str, condition: bool, details: str) -> CheckResult:
    return CheckResult(agent=agent, case_id=case_id, check=name, passed=bool(condition), details=details)


def emergency_checks() -> list[CheckResult]:
    from app.ai.emergency.alert_generator import EmergencyAlertGenerator
    from app.ai.emergency.critical_event_detector import CriticalEventDetector
    from app.ai.emergency.icu_predictor import ICURequirementPredictor
    from app.ai.emergency.priority_ranker import PatientPriorityRanker
    from app.ai.emergency.triage_classifier import EmergencyTriageClassifier
    from app.ai.emergency.vital_monitor import VitalMonitor

    monitor = VitalMonitor()
    detector = CriticalEventDetector()
    triage = EmergencyTriageClassifier()
    icu = ICURequirementPredictor()
    alerts = EmergencyAlertGenerator()
    ranker = PatientPriorityRanker()

    results: list[CheckResult] = []

    critical = monitor.monitor(
        [
            {"name": "SpO2", "value": "88", "unit": "%"},
            {"name": "Blood Pressure", "value": "185/122", "unit": "mmHg"},
            {"name": "Heart Rate", "value": "125", "unit": "bpm"},
        ]
    )
    results.extend(
        [
            check("Emergency", "EM-VITAL-CRITICAL", "critical_vitals_count", critical.critical_count == 3,
                  f"Expected 3 critical vitals, got {critical.critical_count}."),
            check("Emergency", "EM-VITAL-CRITICAL", "monitoring_status", critical.monitoring_status == "critical",
                  f"Expected critical monitoring status, got {critical.monitoring_status!r}."),
        ]
    )

    warning = monitor.monitor([{"name": "SpO2", "value": "92", "unit": "%"}])
    results.append(
        check("Emergency", "EM-VITAL-WARNING", "warning_threshold",
              warning.observations[0].severity == "warning",
              f"Expected SpO2 92 to be warning, got {warning.observations[0].severity!r}.")
    )

    stable = monitor.monitor(
        [
            {"name": "SpO2", "value": "98", "unit": "%"},
            {"name": "Blood Pressure", "value": "120/80", "unit": "mmHg"},
            {"name": "Heart Rate", "value": "72", "unit": "bpm"},
        ]
    )
    results.extend(
        [
            check("Emergency", "EM-VITAL-STABLE", "stable_status", stable.monitoring_status == "stable",
                  f"Expected stable status, got {stable.monitoring_status!r}."),
            check("Emergency", "EM-NO-DATA", "no_data_status", monitor.monitor([]).monitoring_status == "no_data",
                  "Empty input should produce no_data."),
        ]
    )

    events = detector.detect(
        conditions=["sepsis", "stroke"],
        symptoms=["chest pain", "shortness of breath"],
        monitoring=critical,
        risk_level="High",
        risk_alerts=[],
    )
    event_types = {event.event_type for event in events.events}
    results.extend(
        [
            check("Emergency", "EM-EVENTS", "sepsis_signal", "sepsis_signal" in event_types,
                  f"Observed event types: {sorted(event_types)}"),
            check("Emergency", "EM-EVENTS", "stroke_signal", "stroke_signal" in event_types,
                  f"Observed event types: {sorted(event_types)}"),
            check("Emergency", "EM-EVENTS", "cardiorespiratory_signal",
                  "cardiorespiratory_combination" in event_types,
                  f"Observed event types: {sorted(event_types)}"),
        ]
    )

    critical_triage = triage.classify(
        monitoring=critical,
        events=events,
        risk_score=85,
        risk_level="Critical",
    )
    results.extend(
        [
            check("Emergency", "EM-TRIAGE-CRITICAL", "critical_category",
                  critical_triage.category == "Critical",
                  f"Expected Critical, got {critical_triage.category!r}."),
            check("Emergency", "EM-TRIAGE-CRITICAL", "escalation_required",
                  critical_triage.escalation_required is True,
                  f"Expected escalation_required=True, got {critical_triage.escalation_required!r}."),
            check("Emergency", "EM-TRIAGE-CRITICAL", "score_bounded",
                  0 <= critical_triage.score <= 100,
                  f"Score was {critical_triage.score}."),
        ]
    )

    stable_events = detector.detect(
        conditions=[],
        symptoms=[],
        monitoring=stable,
        risk_level=None,
        risk_alerts=[],
    )
    stable_triage = triage.classify(
        monitoring=stable,
        events=stable_events,
        risk_score=0,
        risk_level=None,
    )
    results.append(
        check("Emergency", "EM-TRIAGE-STABLE", "routine_category",
              stable_triage.category == "Routine",
              f"Expected Routine, got {stable_triage.category!r}.")
    )

    critical_icu = icu.predict(
        monitoring=critical,
        events=events,
        risk_score=85,
        risk_level="Critical",
    )
    stable_icu = icu.predict(
        monitoring=stable,
        events=stable_events,
        risk_score=0,
        risk_level=None,
    )
    results.extend(
        [
            check("Emergency", "EM-ICU", "high_icu_signal", critical_icu.signal == "High",
                  f"Expected High, got {critical_icu.signal!r}."),
            check("Emergency", "EM-ICU", "stable_low_signal", stable_icu.signal == "Low",
                  f"Expected Low for stable case, got {stable_icu.signal!r}."),
        ]
    )

    critical_alerts = alerts.generate(
        monitoring=critical,
        triage=critical_triage,
        events=events,
        icu=critical_icu,
    )
    results.extend(
        [
            check("Emergency", "EM-ALERTS", "critical_alert_generated",
                  critical_alerts.alert_count >= 1,
                  f"Expected at least 1 alert, got {critical_alerts.alert_count}."),
            check("Emergency", "EM-ALERTS", "highest_severity",
                  critical_alerts.highest_severity == "critical",
                  f"Expected critical highest severity, got {critical_alerts.highest_severity!r}."),
        ]
    )

    priority = ranker.rank(
        triage=critical_triage,
        monitoring=critical,
        events=events,
        icu_signal=critical_icu.signal,
    )
    results.append(
        check("Emergency", "EM-PRIORITY", "priority_bounded_and_critical",
              0 <= priority.priority_score <= 100 and priority.priority_level == "Critical",
              f"Priority was {priority.priority_score}/{priority.priority_level}.")
    )
    return results


def scheduling_checks() -> list[CheckResult]:
    from app.ai.scheduling.appointment_scheduler import AppointmentSlotEngine
    from app.ai.scheduling.doctor_assignment import DoctorAssignmentEngine
    from app.ai.scheduling.follow_up import FollowUpPlanner
    from app.ai.scheduling.models import DoctorWorkload
    from app.ai.scheduling.queue_optimizer import QueueOptimizer
    from app.ai.scheduling.surgery_scheduler import SurgeryScheduler
    from app.ai.scheduling.workload_balancer import WorkloadBalancer

    results: list[CheckResult] = []

    doctors = [
        {
            "id": "doc-cardio",
            "first_name": "Asha",
            "last_name": "Rao",
            "specialization": "Cardiology",
            "availability_status": "Available",
            "experience_years": 10,
            "department_id": "cardio",
        },
        {
            "id": "doc-general",
            "first_name": "Ravi",
            "last_name": "Kumar",
            "specialization": "General Medicine",
            "availability_status": "Available",
            "experience_years": 12,
            "department_id": "general",
        },
        {
            "id": "doc-leave",
            "first_name": "Maya",
            "last_name": "Singh",
            "specialization": "Cardiology",
            "availability_status": "On Leave",
            "experience_years": 15,
            "department_id": "cardio",
        },
    ]
    assignment = DoctorAssignmentEngine().assign(
        doctors=doctors,
        workload={"doc-cardio": 0, "doc-general": 0, "doc-leave": 0},
        department_names={"cardio": "Cardiology", "general": "General Medicine"},
        clinical_text="chest pain and heart discomfort",
        emergency_level="Urgent",
        visit_type="Consultation",
    )
    results.extend(
        [
            check("Scheduling", "SCH-DOCTOR-MATCH", "specialty_match",
                  assignment.selected_doctor_id == "doc-cardio",
                  f"Expected doc-cardio, got {assignment.selected_doctor_id!r}."),
            check("Scheduling", "SCH-DOCTOR-MATCH", "leave_doctor_excluded",
                  all(c.doctor_id != "doc-leave" for c in assignment.candidates),
                  "On-leave doctors should not appear in normal bookable candidates."),
        ]
    )

    slot_engine = AppointmentSlotEngine()
    slots = [
        {"appointment_date": "2026-09-24", "start_time": "09:00:00", "end_time": "09:30:00"},
        {"appointment_date": "2026-09-24", "start_time": "09:30:00", "end_time": "10:00:00"},
    ]
    appointment = slot_engine.recommend(
        slots=slots,
        doctor_id="doc-cardio",
        doctor_name="Dr. Asha Rao",
        priority_level="Urgent",
    )
    results.append(
        check("Scheduling", "SCH-APPOINTMENT-EARLIEST", "earliest_slot",
              appointment.recommended_slot is not None
              and appointment.recommended_slot.start_time == "09:00:00",
              f"Recommended slot: {appointment.recommended_slot.start_time if appointment.recommended_slot else None}.")
    )

    no_slot = slot_engine.recommend(
        slots=[],
        doctor_id="doc-cardio",
        doctor_name="Dr. Asha Rao",
        priority_level="Routine",
    )
    results.append(
        check("Scheduling", "SCH-APPOINTMENT-NONE", "empty_slot_window",
              no_slot.recommended_slot is None,
              "No available windows should produce no recommended slot.")
    )

    surgery = SurgeryScheduler().recommend(
        required=True,
        procedure_names=["Angioplasty"],
        windows=[{"appointment_date": "2026-09-25", "start_time": "10:00:00", "end_time": "12:00:00"}],
        doctor_id="doc-cardio",
        doctor_name="Dr. Asha Rao",
        duration_minutes=90,
    )
    results.extend(
        [
            check("Scheduling", "SCH-SURGERY", "surgery_required_preserved",
                  surgery.required is True,
                  f"Expected required=True, got {surgery.required!r}."),
            check("Scheduling", "SCH-SURGERY", "duration_preserved",
                  surgery.duration_minutes == 90,
                  f"Expected 90 minutes, got {surgery.duration_minutes!r}."),
            check("Scheduling", "SCH-SURGERY", "slot_recommended",
                  surgery.recommended_slot is not None,
                  "A supplied doctor and surgery window should produce a planning slot."),
            check("Scheduling", "SCH-SURGERY", "resource_allocation_deferred",
                  surgery.resource_allocation_required is True,
                  "Surgery planning should require downstream resource validation."),
        ]
    )

    no_duration = SurgeryScheduler().recommend(
        required=True,
        procedure_names=["Procedure"],
        windows=[{"appointment_date": "2026-09-25", "start_time": "10:00:00", "end_time": "12:00:00"}],
        doctor_id="doc-cardio",
        doctor_name="Dr. Asha Rao",
        duration_minutes=0,
    )
    results.append(
        check("Scheduling", "SCH-SURGERY-NO-DURATION", "no_fabricated_slot",
              no_duration.recommended_slot is None,
              "Missing procedure duration should not fabricate a surgery slot.")
    )

    follow_up = FollowUpPlanner().plan(
        appointment_date=date(2026, 9, 24),
        interval_days=30,
        priority_level="Urgent",
    )
    results.extend(
        [
            check("Scheduling", "SCH-FOLLOW-UP", "urgent_interval_capped",
                  follow_up.interval_days == 7,
                  f"Expected 7 days, got {follow_up.interval_days}."),
            check("Scheduling", "SCH-FOLLOW-UP", "recommended_date",
                  follow_up.recommended_date == "2026-10-01",
                  f"Expected 2026-10-01, got {follow_up.recommended_date!r}."),
        ]
    )

    queue = QueueOptimizer().optimize(
        doctor_id="doc-cardio",
        appointment_date="2026-09-24",
        appointments=[
            {"id": "a1", "patient_id": "p1", "patient_name": "Routine Patient", "start_time": "09:00:00", "end_time": "09:30:00"},
            {"id": "a2", "patient_id": "p2", "patient_name": "Critical Patient", "start_time": "09:30:00", "end_time": "10:00:00"},
        ],
        priority_by_patient={
            "p1": {"priority_level": "Routine", "priority_score": 20},
            "p2": {"priority_level": "Critical", "priority_score": 95},
        },
    )
    results.extend(
        [
            check("Scheduling", "SCH-QUEUE", "critical_patient_first",
                  bool(queue.ordered_queue) and queue.ordered_queue[0].patient_id == "p2",
                  f"First queue patient: {queue.ordered_queue[0].patient_id if queue.ordered_queue else None}."),
            check("Scheduling", "SCH-QUEUE", "recommendation_not_mutation",
                  any("not changed automatically" in r.lower() for r in queue.rationale),
                  "Queue output should state that stored appointment order is not changed automatically."),
        ]
    )

    workload = WorkloadBalancer().balance(
        doctors=[
            DoctorWorkload(doctor_id="doc-a", doctor_name="Dr. A", active_appointments=2, workload_score=25.0),
            DoctorWorkload(doctor_id="doc-b", doctor_name="Dr. B", active_appointments=8, workload_score=80.0),
        ]
    )
    results.extend(
        [
            check("Scheduling", "SCH-WORKLOAD", "lower_load_first",
                  "Dr. A" in workload.recommendation,
                  f"Recommendation: {workload.recommendation}"),
            check("Scheduling", "SCH-WORKLOAD", "balance_gap",
                  workload.balance_gap == 55.0,
                  f"Expected gap 55.0, got {workload.balance_gap}."),
        ]
    )
    return results


def resource_checks() -> list[CheckResult]:
    from types import SimpleNamespace
    from uuid import UUID

    from app.ai.resource_allocation.availability_assessor import AvailabilityAssessor
    from app.ai.resource_allocation.conflict_detector import ConflictDetector
    from app.ai.resource_allocation.context import ResourceAllocationContext
    from app.ai.resource_allocation.models import ResourceRequirement
    from app.ai.resource_allocation.priority_allocator import PriorityAllocator
    from app.schemas.resource_allocation import ResourceAllocationStartRequest

    results: list[CheckResult] = []

    fields = set(ResourceAllocationStartRequest.model_fields)
    results.append(
        check("Resource Allocation", "RA-REQUEST", "patient_only_request",
              fields == {"patient_id"},
              f"Request fields: {sorted(fields)}.")
    )

    patient = SimpleNamespace(patient_id="patient-1", patient_name="Test Patient")
    derived = ResourceAllocationContext.derive(
        {
            "patient": patient,
            "scheduling": {
                "id": "s1",
                "emergency_priority_level": "Urgent",
                "emergency_priority_score": 86,
                "resource_requirements_json": ["ICU Bed", "Operating Theatre", "Specialist Staff"],
                "procedures_json": ["Angioplasty"],
                "surgery_scheduling_json": {"required": True},
                "derived_specialists_json": ["Cardiologist"],
            },
            "emergency": {"id": "e1", "icu_requirement_json": {"signal": "High"}},
        }
    )
    requirement_labels = [r.requirement for r in derived["requirements"]]
    results.extend(
        [
            check("Resource Allocation", "RA-CONTEXT", "scheduling_requirements_consumed",
                  requirement_labels[:3] == ["ICU Bed", "Operating Theatre", "Specialist Staff"],
                  f"Derived requirements: {requirement_labels}."),
            check("Resource Allocation", "RA-CONTEXT", "upstream_priority_consumed",
                  derived["priority_level"] == "Urgent" and derived["priority_score"] == 86,
                  f"Priority: {derived['priority_level']} {derived['priority_score']}."),
            check("Resource Allocation", "RA-CONTEXT", "provenance_ids",
                  derived["source_result_ids"] == {"scheduling": "s1", "emergency": "e1"},
                  f"Source IDs: {derived['source_result_ids']}."),
        ]
    )

    assessor = AvailabilityAssessor()
    full = assessor.assess(
        requirements=[
            ResourceRequirement(
                requirement="ICU Bed", resource_type="ICU Bed", required_quantity=1,
                source="Scheduling Agent", rationale="ICU required", priority=100,
            ),
            ResourceRequirement(
                requirement="Specialist Staff", resource_type=None, required_quantity=1,
                source="Scheduling Agent", rationale="Cardiologist needed", priority=85,
            ),
        ],
        resources=[
            {
                "id": "icu-1", "resource_name": "ICU-01", "resource_type": "ICU Bed",
                "available_quantity": 2, "status": "Available",
            }
        ],
        doctors=[
            {
                "id": "doc-1", "first_name": "Asha", "last_name": "Rao",
                "specialization": "Cardiology", "availability_status": "Available",
            }
        ],
        selected_doctor_id="doc-1",
        preferred_specialists=["Cardiologist"],
    )
    results.extend(
        [
            check("Resource Allocation", "RA-AVAILABILITY", "full_resource_allocation",
                  full[0].status == "Allocated" and full[0].allocated_quantity == 1,
                  f"ICU allocation: {full[0].status}/{full[0].allocated_quantity}."),
            check("Resource Allocation", "RA-AVAILABILITY", "specialist_match",
                  full[1].status == "Allocated" and full[1].matched_resources[0].resource_id == "doc-1",
                  "Expected selected available cardiologist to satisfy specialist staff."),
        ]
    )

    shortage_item = assessor.assess(
        requirements=[
            ResourceRequirement(
                requirement="Operating Theatre", resource_type="Operation Theatre",
                required_quantity=2, source="Scheduling Agent", rationale="Surgery", priority=90,
            )
        ],
        resources=[
            {
                "id": "ot-1", "resource_name": "OT-01", "resource_type": "Operation Theatre",
                "available_quantity": 1, "status": "Available",
            }
        ],
        doctors=[],
    )[0]
    conflicts = ConflictDetector().detect(
        allocations=[shortage_item],
        surgery_conflict=False,
        scheduling_available=True,
    )
    results.extend(
        [
            check("Resource Allocation", "RA-SHORTAGE", "partial_allocation",
                  shortage_item.status == "Partially Allocated" and shortage_item.shortage_quantity == 1,
                  f"Observed {shortage_item.status} with shortage {shortage_item.shortage_quantity}."),
            check("Resource Allocation", "RA-SHORTAGE", "shortage_conflict",
                  any(c.code == "RESOURCE_SHORTAGE" for c in conflicts),
                  f"Conflict codes: {[c.code for c in conflicts]}."),
        ]
    )

    surgery_conflicts = ConflictDetector().detect(
        allocations=[],
        surgery_conflict=True,
        scheduling_available=False,
    )
    conflict_codes = {c.code for c in surgery_conflicts}
    results.extend(
        [
            check("Resource Allocation", "RA-CONFLICTS", "upstream_surgery_conflict",
                  "UPSTREAM_SURGERY_CONFLICT" in conflict_codes,
                  f"Conflict codes: {sorted(conflict_codes)}."),
            check("Resource Allocation", "RA-CONFLICTS", "missing_scheduling_context",
                  "MISSING_SCHEDULING_CONTEXT" in conflict_codes,
                  f"Conflict codes: {sorted(conflict_codes)}."),
        ]
    )

    allocator = PriorityAllocator()
    low = ResourceRequirement(
        requirement="Bed", resource_type="Bed", required_quantity=1,
        source="Scheduling Agent", rationale="Bed", priority=40,
    )
    high = ResourceRequirement(
        requirement="ICU Bed", resource_type="ICU Bed", required_quantity=1,
        source="Scheduling Agent", rationale="ICU", priority=100,
    )
    items = assessor.assess(
        requirements=[low, high],
        resources=[
            {"id": "bed-1", "resource_name": "Bed 1", "resource_type": "Bed", "available_quantity": 1, "status": "Available"},
            {"id": "icu-1", "resource_name": "ICU 1", "resource_type": "ICU Bed", "available_quantity": 1, "status": "Available"},
        ],
        doctors=[],
    )
    ordered = allocator.order(items)
    results.extend(
        [
            check("Resource Allocation", "RA-PRIORITY", "higher_priority_first",
                  ordered[0].requirement == "ICU Bed",
                  f"First requirement: {ordered[0].requirement}."),
            check("Resource Allocation", "RA-PRIORITY", "full_allocation_score",
                  allocator.allocation_score(ordered) == 100.0,
                  f"Allocation score: {allocator.allocation_score(ordered)}."),
        ]
    )

    return results


def run_suite() -> list[CheckResult]:
    return emergency_checks() + scheduling_checks() + resource_checks()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic operational validation for three hospital agents.")
    parser.add_argument(
        "--output",
        default=None,
        help="Optional JSON output path. Without it, results are printed as JSON to stdout.",
    )
    args = parser.parse_args()

    checks = run_suite()
    passed = sum(item.passed for item in checks)
    failed = len(checks) - passed
    summary = {
        "validation_type": "deterministic_operational_verification",
        "scope": ["Emergency", "Scheduling", "Resource Allocation"],
        "clinical_accuracy_claim": False,
        "total_checks": len(checks),
        "passed": passed,
        "failed": failed,
        "pass_rate_percent": round((passed / len(checks)) * 100, 1) if checks else 0.0,
        "checks": [asdict(item) for item in checks],
    }
    serialized = json.dumps(summary, indent=2)

    print(serialized)

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized + "\n", encoding="utf-8")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
