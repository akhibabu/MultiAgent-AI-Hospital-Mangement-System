"""Dataset-grounded functional validation for the six Scheduling Agent tasks.

The public AISmithLab benchmark supplies labelled appointment-slot tasks. Its
published six easy + eight hard cases are replayed where compatible. To reach
25 cases per task for the project review, the remaining cases are generated
from the benchmark snapshot as a clearly-labelled project synthetic extension.
For the five non-slot stages, the benchmark extension is synthetic and stores
explicit ground-truth expectations alongside each case.

This is operational/functionality validation, not clinical accuracy.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.ai.scheduling.appointment_scheduler import AppointmentSlotEngine
from app.ai.scheduling.doctor_assignment import DoctorAssignmentEngine
from app.ai.scheduling.follow_up import FollowUpPlanner
from app.ai.scheduling.queue_optimizer import QueueOptimizer
from app.ai.scheduling.surgery_scheduler import SurgeryScheduler
from app.ai.scheduling.workload_balancer import WorkloadBalancer
from app.ai.scheduling.models import DoctorWorkload


TASK_IDS = [
    "scheduling_doctor_assignment",
    "scheduling_appointment_scheduling",
    "scheduling_surgery_scheduling",
    "scheduling_follow_up_planning",
    "scheduling_queue_optimization",
    "scheduling_workload_balancing",
]


def pct(n: float) -> float:
    return round(n * 100.0, 4)


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_cases(root: Path, task_id: str, cases: List[Dict[str, Any]], metrics: Dict[str, Any], dataset: str, note: str) -> None:
    task_dir = root / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "cases.jsonl").write_text(
        "".join(json.dumps(case) + "\n" for case in cases),
        encoding="utf-8",
    )
    payload = {
        "task_id": task_id,
        "dataset": dataset,
        "cases_evaluated": len(cases),
        "clinical_accuracy_claim": False,
        "note": note,
        **metrics,
    }
    headline_metric = metrics.get("headline_metric")
    headline_value = metrics.get("headline_value")
    if headline_metric is not None:
        payload["headline_metric"] = headline_metric
    if headline_value is not None:
        payload["headline_value"] = headline_value
    (task_dir / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def score_accuracy(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    matches = [bool(c["metrics"].get("match")) for c in cases]
    acc = sum(matches) / len(matches) if matches else 0.0
    return {"accuracy": acc, "headline_metric": "Accuracy", "headline_value": acc}


def build_doctor_cases(doctors: List[Dict[str, Any]], count: int = 25) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    engine = DoctorAssignmentEngine()
    patterns = [
        ("cardiology", "chest pain and heart discomfort", "Urgent"),
        ("neurology", "stroke symptoms and severe weakness", "Critical"),
        ("pulmonology", "shortness of breath and respiratory symptoms", "Urgent"),
        ("orthopedics", "fracture and joint pain", "Routine"),
        ("dermatology", "skin rash and eczema", "Routine"),
    ]
    available = [
        d for d in doctors
        if str(d.get("availability_status") or "Available") != "On Leave"
    ]
    if len(available) < 2:
        raise SystemExit("Need at least two doctors in benchmark fixture.")

    cases: List[Dict[str, Any]] = []
    for idx in range(count):
        target_specialty, clinical_text, level = patterns[idx % len(patterns)]
        target = next(
            (d for d in available if target_specialty in str(d.get("specialization") or "").lower()),
            available[idx % len(available)],
        )
        # Ground truth is explicitly labelled in the synthetic case and is
        # based on the intended specialty match, not by calling the engine.
        expected_id = str(target["id"])
        fixture_doctors = []
        for d in available[: min(len(available), 6)]:
            fixture_doctors.append(dict(d))
        if not any(str(d["id"]) == expected_id for d in fixture_doctors):
            fixture_doctors.append(dict(target))
        workload = {str(d["id"]): ((idx + j) % 3) for j, d in enumerate(fixture_doctors)}
        result = engine.assign(
            doctors=fixture_doctors,
            workload=workload,
            department_names={},
            requested_department_name=None,
            preferred_specialists=[target_specialty],
            clinical_text=clinical_text,
            emergency_level=level,
            visit_type="Emergency" if level in {"Critical", "Urgent"} else "Consultation",
        )
        match = result.selected_doctor_id == expected_id
        cases.append({
            "case_id": f"SCH-DOCTOR-{idx+1:03d}",
            "task_id": "scheduling_doctor_assignment",
            "status": "SCORED",
            "input": {
                "clinical_text": clinical_text,
                "emergency_level": level,
                "preferred_specialty": target_specialty,
                "doctor_ids": [str(d["id"]) for d in fixture_doctors],
                "workload": workload,
            },
            "prediction": {"selected_doctor_id": result.selected_doctor_id},
            "ground_truth": {"selected_doctor_id": expected_id},
            "metrics": {"match": match},
        })
    return cases, score_accuracy(cases)


def valid_snapshot_slots(snapshot: Dict[str, Any], task: Dict[str, Any]) -> List[Dict[str, Any]]:
    c = task.get("constraints", {})
    appt = next(
        x for x in task["initial_ledger"]["appointments"]
        if x["appointment_id"] == task["appointment_id"]
    )
    patient = next(x for x in snapshot["patients"] if x["patient_id"] == appt["patient_id"])
    providers = {x["provider_id"]: x for x in snapshot["providers"]}
    result = []
    for slot in snapshot["slots"]:
        if not slot.get("available"):
            continue
        start = datetime.fromisoformat(slot["start"])
        provider = providers[slot["provider_id"]]
        if c.get("date") and start.date().isoformat() != c["date"]:
            continue
        if c.get("min_hour") is not None and start.hour < c["min_hour"]:
            continue
        if c.get("max_hour") is not None and start.hour >= c["max_hour"]:
            continue
        if c.get("same_provider", True) and slot["provider_id"] != appt["provider_id"]:
            continue
        if c.get("required_specialty") and provider["specialty"] != c["required_specialty"]:
            continue
        if c.get("required_location") and provider.get("location") != c["required_location"]:
            continue
        if c.get("insurance_required") and patient["insurance"] not in provider.get("accepted_insurance", []):
            continue
        if c.get("pediatric_policy") and patient.get("age", 999) < 18 and not provider.get("pediatric_eligible", False):
            continue
        result.append(slot)
    return sorted(result, key=lambda x: x["start"])


def build_appointment_cases(snapshot: Dict[str, Any], tasks: List[Dict[str, Any]], count: int = 25) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    engine = AppointmentSlotEngine()
    public = [t for t in tasks if t.get("suite") in {"easy", "hard"}]
    chosen = public[:14]
    synthetic_needed = max(0, count - len(chosen))
    synthetic = []
    available_slots = [s for s in snapshot["slots"] if s.get("available")]
    for i in range(synthetic_needed):
        base = available_slots[i % len(available_slots)]
        start = datetime.fromisoformat(base["start"])
        synthetic.append({
            "id": f"EXT-{i+1:03d}",
            "name": f"Project extension earliest valid slot {i+1}",
            "suite": "project_extension",
            "appointment_id": "A001",
            "constraints": {
                "date": start.date().isoformat(),
                "min_hour": max(0, start.hour - (1 if i % 2 else 0)),
                "max_hour": None,
                "same_provider": True,
                "required_specialty": "dermatology",
                "insurance_required": True,
            },
            "objective": "earliest",
            "initial_ledger": {"appointments": [{
                "appointment_id": "A001",
                "patient_id": "P001",
                "provider_id": base["provider_id"],
            }]},
        })
    cases: List[Dict[str, Any]] = []
    for task in chosen + synthetic:
        candidates = valid_snapshot_slots(snapshot, task)
        appt = task["initial_ledger"]["appointments"][0]
        provider_id = str(appt["provider_id"])
        chosen_provider = next((p for p in snapshot["providers"] if p["provider_id"] == provider_id), None)
        provider_name = chosen_provider["name"] if chosen_provider else "Benchmark Provider"
        if candidates:
            slot_rows = []
            for c in candidates:
                st = datetime.fromisoformat(c["start"])
                end = st + timedelta(minutes=30)
                slot_rows.append({
                    "appointment_date": st.date().isoformat(),
                    "start_time": st.strftime("%H:%M:%S"),
                    "end_time": end.strftime("%H:%M:%S"),
                })
            result = engine.recommend(
                slots=slot_rows,
                doctor_id=provider_id,
                doctor_name=provider_name,
                priority_level="Routine",
            )
            predicted_start = (
                f"{result.recommended_slot.appointment_date}T{result.recommended_slot.start_time}"
                if result.recommended_slot
                else None
            )
            predicted = next((s for s in candidates if s["start"].startswith(predicted_start or "")), None)
            predicted_id = predicted["slot_id"] if predicted else None
            expected_id = candidates[0]["slot_id"]
        else:
            result = engine.recommend(
                slots=[],
                doctor_id=provider_id,
                doctor_name=provider_name,
                priority_level="Routine",
            )
            predicted_id = None
            expected_id = None
        cases.append({
            "case_id": f"SCH-APPOINTMENT-{task.get('id','EXT'):>7}",
            "task_id": "scheduling_appointment_scheduling",
            "status": "SCORED",
            "input": {"task": task.get("name"), "constraints": task.get("constraints", {}), "candidate_count": len(candidates)},
            "prediction": {"slot_id": predicted_id},
            "ground_truth": {"slot_id": expected_id},
            "metrics": {"match": predicted_id == expected_id},
        })
    return cases, score_accuracy(cases)


def build_surgery_cases(count: int = 25) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    engine = SurgeryScheduler()
    cases = []
    for i in range(count):
        required = i % 5 != 0
        duration = 60 + (i % 4) * 30
        windows = [] if i % 7 == 0 else [{
            "appointment_date": f"2026-10-{10 + (i % 10):02d}",
            "start_time": "09:00:00",
            "end_time": "12:00:00",
        }]
        doctor_id = "D-SYNTH"
        doctor_name = "Dr. Synthetic"
        if i % 11 == 0:
            doctor_id = None
            doctor_name = None
        if i % 13 == 0:
            duration = 0
        result = engine.recommend(
            required=required,
            procedure_names=["Procedure A"],
            windows=windows,
            doctor_id=doctor_id,
            doctor_name=doctor_name,
            duration_minutes=duration,
        )
        expected_slot = None
        expected_required = required
        if required and doctor_id and doctor_name and duration and windows:
            expected_slot = windows[0]["start_time"]
        predicted_slot = result.recommended_slot.start_time if result.recommended_slot else None
        cases.append({
            "case_id": f"SCH-SURGERY-{i+1:03d}",
            "task_id": "scheduling_surgery_scheduling",
            "status": "SCORED",
            "input": {"required": required, "duration_minutes": duration, "windows": windows},
            "prediction": {"required": result.required, "start_time": predicted_slot},
            "ground_truth": {"required": expected_required, "start_time": expected_slot},
            "metrics": {"match": result.required == expected_required and predicted_slot == expected_slot},
        })
    return cases, score_accuracy(cases)


def build_followup_cases(count: int = 25) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    planner = FollowUpPlanner()
    cases = []
    priorities = ["Routine", "Semi-Urgent", "Urgent", "Critical"]
    for i in range(count):
        priority = priorities[i % len(priorities)]
        requested = [1, 7, 14, 30, 90][i % 5]
        appointment_date = date(2026, 9, 1) + timedelta(days=i)
        if priority == "Critical":
            expected = min(max(requested, 1), 3)
        elif priority == "Urgent":
            expected = min(max(requested, 1), 7)
        else:
            expected = min(max(requested, 1), 180)
        result = planner.plan(
            appointment_date=appointment_date,
            interval_days=requested,
            priority_level=priority,
        )
        cases.append({
            "case_id": f"SCH-FOLLOWUP-{i+1:03d}",
            "task_id": "scheduling_follow_up_planning",
            "status": "SCORED",
            "input": {"appointment_date": appointment_date.isoformat(), "requested_interval_days": requested, "priority_level": priority},
            "prediction": {"interval_days": result.interval_days, "recommended_date": result.recommended_date},
            "ground_truth": {"interval_days": expected, "recommended_date": (appointment_date + timedelta(days=expected)).isoformat()},
            "metrics": {"match": result.interval_days == expected},
        })
    return cases, score_accuracy(cases)


def build_queue_cases(count: int = 25) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    optimizer = QueueOptimizer()
    levels = ["Routine", "Semi-Urgent", "Urgent", "Critical"]
    cases = []
    for i in range(count):
        appointments = []
        priorities = {}
        for j in range(4):
            pid = f"P{i+1:03d}-{j}"
            level = levels[(i + j) % len(levels)]
            score = float((j + 1) * 10 + (i % 7))
            aid = f"A{i+1:03d}-{j}"
            appointments.append({
                "id": aid,
                "patient_id": pid,
                "patient_name": pid,
                "start_time": f"{9 + j:02d}:00:00",
                "end_time": f"{9 + j:02d}:30:00",
            })
            priorities[pid] = {"priority_level": level, "priority_score": score}
        result = optimizer.optimize(
            doctor_id="D-SYNTH",
            appointment_date="2026-10-01",
            appointments=appointments,
            priority_by_patient=priorities,
        )
        # Independent expected order follows the documented queue policy:
        # Critical > Urgent > Semi-Urgent > Routine, then score, then start.
        rank = {"Critical": 4, "Urgent": 3, "Semi-Urgent": 2, "Routine": 1}
        expected = sorted(
            appointments,
            key=lambda a: (
                -rank[priorities[a["patient_id"]]["priority_level"]],
                -priorities[a["patient_id"]]["priority_score"],
                a["start_time"],
            ),
        )
        pred_ids = [x.appointment_id for x in result.ordered_queue]
        expected_ids = [x["id"] for x in expected]
        cases.append({
            "case_id": f"SCH-QUEUE-{i+1:03d}",
            "task_id": "scheduling_queue_optimization",
            "status": "SCORED",
            "input": {"appointments": appointments, "priority_by_patient": priorities},
            "prediction": {"ordered_appointment_ids": pred_ids},
            "ground_truth": {"ordered_appointment_ids": expected_ids},
            "metrics": {"match": pred_ids == expected_ids},
        })
    return cases, score_accuracy(cases)


def build_workload_cases(count: int = 25) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    balancer = WorkloadBalancer()
    cases = []
    for i in range(count):
        doctors = [
            DoctorWorkload("D-A", "Dr. A", 2 + (i % 3), 20 + (i % 7) * 2, "Available"),
            DoctorWorkload("D-B", "Dr. B", 7 + (i % 2), 70 + (i % 5) * 3, "Available"),
            DoctorWorkload("D-C", "Dr. C", 4 + (i % 4), 40 + (i % 4) * 3, "Available"),
        ]
        if i % 8 == 0:
            doctors.append(DoctorWorkload("D-L", "Dr. Leave", 0, 0, "On Leave"))
        result = balancer.balance(doctors=doctors)
        expected = min(
            [d for d in doctors if d.availability_status != "On Leave"],
            key=lambda d: (d.workload_score, d.active_appointments),
        ).doctor_name
        cases.append({
            "case_id": f"SCH-WORKLOAD-{i+1:03d}",
            "task_id": "scheduling_workload_balancing",
            "status": "SCORED",
            "input": {"doctors": [d.model_dump() for d in doctors]},
            "prediction": {"recommended_doctor": result.recommendation.split(" toward ")[-1].split(" first")[0] if " toward " in result.recommendation else result.recommendation},
            "ground_truth": {"recommended_doctor": expected},
            "metrics": {"match": expected in result.recommendation},
        })
    return cases, score_accuracy(cases)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", required=True, help="AISmithLab tasks.json")
    ap.add_argument("--snapshot", required=True, help="AISmithLab snapshot.json")
    ap.add_argument("--max-cases-per-task", type=int, default=25)
    ap.add_argument("--output", default="validation/results/dataset/scheduling_project")
    args = ap.parse_args()

    snapshot = load_json(args.snapshot)
    tasks = load_json(args.tasks).get("tasks", [])
    count = args.max_cases_per_task
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    providers = snapshot.get("providers", [])
    doctors = [
        {
            "id": p["provider_id"],
            "first_name": str(p["name"]).replace("Dr. ", "").split(" ")[0],
            "last_name": " ".join(str(p["name"]).replace("Dr. ", "").split(" ")[1:]),
            "specialization": p["specialty"].replace("_", " ").title(),
            "availability_status": "Available",
            "experience_years": 10 + (idx % 8),
            "department_id": None,
        }
        for idx, p in enumerate(providers)
    ]

    builders = [
        ("scheduling_doctor_assignment", lambda: build_doctor_cases(doctors, count)),
        ("scheduling_appointment_scheduling", lambda: build_appointment_cases(snapshot, tasks, count)),
        ("scheduling_surgery_scheduling", lambda: build_surgery_cases(count)),
        ("scheduling_follow_up_planning", lambda: build_followup_cases(count)),
        ("scheduling_queue_optimization", lambda: build_queue_cases(count)),
        ("scheduling_workload_balancing", lambda: build_workload_cases(count)),
    ]

    all_cases: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, Any]] = {}
    for task_id, builder in builders:
        cases, metrics = builder()
        dataset = (
            "AISmithLab Appointment Scheduling Benchmark + Project Synthetic Functional Extension"
            if task_id == "scheduling_appointment_scheduling"
            else "Project Synthetic Scheduling Functional Benchmark v1"
        )
        note = (
            "14 public benchmark cases plus project-labelled synthetic extension to 25 cases."
            if task_id == "scheduling_appointment_scheduling"
            else "Synthetic labelled functional benchmark; not historical hospital performance."
        )
        write_cases(output, task_id, cases, metrics, dataset, note)
        all_cases.extend(cases)
        summaries[task_id] = {"dataset": dataset, "cases_evaluated": len(cases), **metrics}

    (output / "cases.jsonl").write_text(
        "".join(json.dumps(case) + "\n" for case in all_cases),
        encoding="utf-8",
    )
    summary = {
        "dataset": "Scheduling Agent benchmark suite",
        "cases_per_task": count,
        "task_summaries": summaries,
        "clinical_accuracy_claim": False,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
