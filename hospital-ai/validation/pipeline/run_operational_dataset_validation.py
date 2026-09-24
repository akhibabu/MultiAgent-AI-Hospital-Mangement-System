"""Dataset-grounded benchmark runner for Emergency, Scheduling and Resource Allocation.

Each benchmark case contains:
    dataset input -> agent component output -> explicit reference ground truth
    -> task-specific metric -> per-case JSONL result + task summary.

The benchmark is synthetic/reference data derived from the project's deterministic
rule/constraint contract. It is NOT clinician-labelled clinical ground truth and
must not be presented as clinical accuracy evidence.

Run from hospital-ai/:
    python validation/pipeline/run_operational_dataset_validation.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
BENCHMARK_PATH = PROJECT_ROOT / "validation" / "benchmarks" / "operational_agents_v1.json"
RESULT_ROOT = PROJECT_ROOT / "validation" / "results" / "dataset" / "operational_agents_v1"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


# ---------------------------------------------------------------------------
# Generic metrics
# ---------------------------------------------------------------------------

def accuracy(items: Iterable[bool]) -> float:
    values = list(items)
    return sum(1 for x in values if x) / len(values) if values else 0.0


def precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def macro_f1(y_true: list[str], y_pred: list[str]) -> float:
    labels = sorted(set(y_true) | set(y_pred))
    values = []
    for label in labels:
        tp = sum(a == label and b == label for a, b in zip(y_true, y_pred))
        fp = sum(a != label and b == label for a, b in zip(y_true, y_pred))
        fn = sum(a == label and b != label for a, b in zip(y_true, y_pred))
        _, _, f1 = precision_recall_f1(tp, fp, fn)
        values.append(f1)
    return sum(values) / len(values) if values else 0.0


def micro_set_metrics(true_sets: list[set[str]], pred_sets: list[set[str]]) -> tuple[float, float, float]:
    tp = fp = fn = 0
    for truth, pred in zip(true_sets, pred_sets):
        tp += len(truth & pred)
        fp += len(pred - truth)
        fn += len(truth - pred)
    return precision_recall_f1(tp, fp, fn)


def exact_score(matches: list[bool]) -> dict[str, float]:
    value = accuracy(matches)
    return {
        "accuracy": value,
        "precision": value,
        "recall": value,
        "f1_score": value,
    }


def write_task_results(task_id: str, records: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    (RESULT_ROOT / f"{task_id}.jsonl").write_text(
        "".join(json.dumps(record, separators=(",", ":")) + "\n" for record in records),
        encoding="utf-8",
    )
    (RESULT_ROOT / f"{task_id}.summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )


def case_result(
    *,
    agent: str,
    task_id: str,
    case_id: str,
    prediction: Any,
    ground_truth: Any,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "task_id": task_id,
        "agent": agent,
        "status": "SCORED",
        "prediction": prediction,
        "ground_truth": ground_truth,
        "metrics": metrics,
        "benchmark_type": "synthetic_project_reference",
    }


def base_summary(
    *,
    task_id: str,
    task: str,
    metric: str,
    value: float,
    cases: int,
    note: str = "",
    **extra: Any,
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "task": task,
        "status": "VALIDATED",
        "cases_evaluated": cases,
        "cases_in_benchmark": cases,
        "headline_metric": metric,
        "headline_value": value,
        "dataset": "HOS-OPS-REF-25-v1 (synthetic project reference)",
        "note": note,
        **extra,
    }


# ---------------------------------------------------------------------------
# Emergency
# ---------------------------------------------------------------------------

def run_emergency(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    from app.ai.emergency.alert_generator import EmergencyAlertGenerator
    from app.ai.emergency.critical_event_detector import CriticalEventDetector
    from app.ai.emergency.icu_predictor import ICURequirementPredictor
    from app.ai.emergency.models import (
        CriticalEventDetectionResult,
        EmergencyAlertGenerationResult,
        ICURequirementResult,
        TriageClassification,
        VitalMonitoringResult,
    )
    from app.ai.emergency.priority_ranker import PatientPriorityRanker
    from app.ai.emergency.triage_classifier import EmergencyTriageClassifier
    from app.ai.emergency.vital_monitor import VitalMonitor

    monitor = VitalMonitor()
    detector = CriticalEventDetector()
    triage_engine = EmergencyTriageClassifier()
    icu_engine = ICURequirementPredictor()
    alert_engine = EmergencyAlertGenerator()
    priority_engine = PatientPriorityRanker()

    bundles = []
    for item in cases:
        inp = item["input"]
        monitoring = monitor.monitor(inp.get("vitals") or [])
        events = detector.detect(
            conditions=inp.get("conditions") or [],
            symptoms=inp.get("symptoms") or [],
            monitoring=monitoring,
            risk_level=inp.get("risk_level"),
            risk_alerts=[],
        )
        triage = triage_engine.classify(
            monitoring=monitoring,
            events=events,
            risk_score=inp.get("risk_score"),
            risk_level=inp.get("risk_level"),
        )
        icu = icu_engine.predict(
            monitoring=monitoring,
            events=events,
            risk_score=inp.get("risk_score"),
            risk_level=inp.get("risk_level"),
        )
        alerts = alert_engine.generate(
            monitoring=monitoring,
            triage=triage,
            events=events,
            icu=icu,
        )
        priority = priority_engine.rank(
            triage=triage,
            monitoring=monitoring,
            events=events,
            icu_signal=icu.signal,
        )
        bundles.append(
            {
                "case": item,
                "monitoring": monitoring,
                "events": events,
                "triage": triage,
                "icu": icu,
                "alerts": alerts,
                "priority": priority,
            }
        )

    results: dict[str, dict[str, Any]] = {}

    # 1. Vital Monitoring
    records = []
    truth_labels: list[str] = []
    pred_labels: list[str] = []
    status_matches = []
    for bundle in bundles:
        gt = bundle["case"]["ground_truth"]["monitoring"]
        pred = bundle["monitoring"]
        pred_sev = {o.name: o.severity for o in pred.observations}
        for name, true_label in gt["vital_severity"].items():
            truth_labels.append(true_label)
            pred_labels.append(pred_sev.get(name, "missing"))
        status_matches.append(pred.monitoring_status == gt["monitoring_status"])
        records.append(
            case_result(
                agent="Emergency",
                task_id="emergency_vital_monitoring",
                case_id=bundle["case"]["case_id"],
                prediction={
                    "vital_severity": pred_sev,
                    "monitoring_status": pred.monitoring_status,
                },
                ground_truth=gt,
                metrics={
                    "match": pred.monitoring_status == gt["monitoring_status"]
                    and pred_sev == gt["vital_severity"]
                },
            )
        )
    f1 = macro_f1(truth_labels, pred_labels)
    summary = base_summary(
        task_id="emergency_vital_monitoring",
        task="Real-Time Vital Monitoring",
        metric="Macro F1",
        value=f1,
        cases=len(cases),
        note=f"Vital severity agreement across {len(truth_labels)} labelled vital observations. Overall monitoring-status accuracy: {accuracy(status_matches)*100:.1f}%.",
        secondary_metrics={"status_accuracy": accuracy(status_matches), "label_count": len(truth_labels)},
    )
    write_task_results("emergency_vital_monitoring", records, summary)
    results["emergency_vital_monitoring"] = summary

    # 2. Triage
    y_true = [b["case"]["ground_truth"]["triage"] for b in bundles]
    y_pred = [b["triage"].category for b in bundles]
    triage_acc = accuracy([a == b for a, b in zip(y_true, y_pred)])
    triage_f1 = macro_f1(y_true, y_pred)
    records = [
        case_result(
            agent="Emergency",
            task_id="emergency_triage_classification",
            case_id=b["case"]["case_id"],
            prediction=b["triage"].category,
            ground_truth=b["case"]["ground_truth"]["triage"],
            metrics={"match": b["triage"].category == b["case"]["ground_truth"]["triage"]},
        )
        for b in bundles
    ]
    summary = base_summary(
        task_id="emergency_triage_classification",
        task="Triage Classification",
        metric="Accuracy",
        value=triage_acc,
        cases=len(cases),
        note=f"Synthetic project-reference triage benchmark. Accuracy {triage_acc*100:.1f}%; Macro F1 {triage_f1*100:.1f}%.",
        accuracy=triage_acc,
        macro_f1=triage_f1,
        f1_score=triage_f1,
    )
    write_task_results("emergency_triage_classification", records, summary)
    results["emergency_triage_classification"] = summary

    # 3. Critical Event Detection
    y_true_sets = [set(b["case"]["ground_truth"]["events"]) for b in bundles]
    y_pred_sets = [
        {e.event_type for e in b["events"].events}
        for b in bundles
    ]
    p, r, f1 = micro_set_metrics(y_true_sets, y_pred_sets)
    records = [
        case_result(
            agent="Emergency",
            task_id="emergency_critical_event_detection",
            case_id=b["case"]["case_id"],
            prediction=sorted({e.event_type for e in b["events"].events}),
            ground_truth=sorted(b["case"]["ground_truth"]["events"]),
            metrics={
                "precision": p,
                "recall": r,
                "f1": f1,
                "match": sorted({e.event_type for e in b["events"].events})
                == sorted(b["case"]["ground_truth"]["events"]),
            },
        )
        for b in bundles
    ]
    summary = base_summary(
        task_id="emergency_critical_event_detection",
        task="Critical Event Detection",
        metric="F1",
        value=f1,
        cases=len(cases),
        note=f"Micro-averaged event-set evaluation over explicit project-reference event labels. Precision {p*100:.1f}%; Recall {r*100:.1f}%; F1 {f1*100:.1f}%.",
        precision=p,
        recall=r,
        f1_score=f1,
    )
    write_task_results("emergency_critical_event_detection", records, summary)
    results["emergency_critical_event_detection"] = summary

    # 4. ICU Requirement Prediction
    y_true = [b["case"]["ground_truth"]["icu"] for b in bundles]
    y_pred = [b["icu"].signal for b in bundles]
    icu_acc = accuracy([a == b for a, b in zip(y_true, y_pred)])
    icu_f1 = macro_f1(y_true, y_pred)
    records = [
        case_result(
            agent="Emergency",
            task_id="emergency_icu_requirement_prediction",
            case_id=b["case"]["case_id"],
            prediction=b["icu"].signal,
            ground_truth=b["case"]["ground_truth"]["icu"],
            metrics={"match": b["icu"].signal == b["case"]["ground_truth"]["icu"]},
        )
        for b in bundles
    ]
    summary = base_summary(
        task_id="emergency_icu_requirement_prediction",
        task="ICU Requirement Prediction",
        metric="Macro F1",
        value=icu_f1,
        cases=len(cases),
        note=f"Synthetic project-reference acuity signal benchmark. Accuracy {icu_acc*100:.1f}%; Macro F1 {icu_f1*100:.1f}%.",
        accuracy=icu_acc,
        macro_f1=icu_f1,
        f1_score=icu_f1,
    )
    write_task_results("emergency_icu_requirement_prediction", records, summary)
    results["emergency_icu_requirement_prediction"] = summary

    # 5. Emergency Alert Generation
    y_true_sets = [set(b["case"]["ground_truth"]["alerts"]) for b in bundles]
    y_pred_sets = [{a.code for a in b["alerts"].alerts} for b in bundles]
    p, r, f1 = micro_set_metrics(y_true_sets, y_pred_sets)
    records = [
        case_result(
            agent="Emergency",
            task_id="emergency_alert_generation",
            case_id=b["case"]["case_id"],
            prediction=sorted({a.code for a in b["alerts"].alerts}),
            ground_truth=sorted(b["case"]["ground_truth"]["alerts"]),
            metrics={"precision": p, "recall": r, "f1": f1},
        )
        for b in bundles
    ]
    summary = base_summary(
        task_id="emergency_alert_generation",
        task="Emergency Alert Generation",
        metric="F1",
        value=f1,
        cases=len(cases),
        note=f"Alert-code set evaluation against explicit project-reference alert labels. Precision {p*100:.1f}%; Recall {r*100:.1f}%; F1 {f1*100:.1f}%.",
        precision=p,
        recall=r,
        f1_score=f1,
    )
    write_task_results("emergency_alert_generation", records, summary)
    results["emergency_alert_generation"] = summary

    # 6. Patient Priority Ranking
    y_true = [b["case"]["ground_truth"]["priority"] for b in bundles]
    y_pred = [b["priority"].priority_level for b in bundles]
    pr_acc = accuracy([a == b for a, b in zip(y_true, y_pred)])
    pr_f1 = macro_f1(y_true, y_pred)
    records = [
        case_result(
            agent="Emergency",
            task_id="emergency_patient_priority_ranking",
            case_id=b["case"]["case_id"],
            prediction=b["priority"].priority_level,
            ground_truth=b["case"]["ground_truth"]["priority"],
            metrics={"match": b["priority"].priority_level == b["case"]["ground_truth"]["priority"]},
        )
        for b in bundles
    ]
    summary = base_summary(
        task_id="emergency_patient_priority_ranking",
        task="Patient Priority Ranking",
        metric="Accuracy",
        value=pr_acc,
        cases=len(cases),
        note=f"Synthetic project-reference priority taxonomy benchmark. Accuracy {pr_acc*100:.1f}%; Macro F1 {pr_f1*100:.1f}%.",
        accuracy=pr_acc,
        macro_f1=pr_f1,
        f1_score=pr_f1,
    )
    write_task_results("emergency_patient_priority_ranking", records, summary)
    results["emergency_patient_priority_ranking"] = summary

    return results


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------

def run_scheduling(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    from app.ai.scheduling.appointment_scheduler import AppointmentSlotEngine
    from app.ai.scheduling.doctor_assignment import DoctorAssignmentEngine
    from app.ai.scheduling.follow_up import FollowUpPlanner
    from app.ai.scheduling.models import DoctorWorkload
    from app.ai.scheduling.queue_optimizer import QueueOptimizer
    from app.ai.scheduling.surgery_scheduler import SurgeryScheduler
    from app.ai.scheduling.workload_balancer import WorkloadBalancer

    assigner = DoctorAssignmentEngine()
    slot_engine = AppointmentSlotEngine()
    surgery_engine = SurgeryScheduler()
    follow_engine = FollowUpPlanner()
    queue_engine = QueueOptimizer()
    balance_engine = WorkloadBalancer()

    bundles = []
    for item in cases:
        inp = item["input"]
        assignment = assigner.assign(
            doctors=inp["doctors"],
            workload=inp["workload"],
            department_names=inp["department_names"],
            preferred_doctor_id=inp.get("preferred_doctor_id"),
            requested_department_id=inp.get("requested_department_id"),
            requested_department_name=inp.get("requested_department_name"),
            preferred_specialists=inp.get("preferred_specialists") or [],
            clinical_text=inp.get("clinical_text") or "",
            emergency_level=inp.get("emergency_level") or "Routine",
            visit_type=inp.get("visit_type") or "Consultation",
        )
        appointment = slot_engine.recommend(
            slots=inp.get("slots") or [],
            doctor_id=assignment.selected_doctor_id or "",
            doctor_name=assignment.selected_doctor_name or "",
            priority_level=inp.get("emergency_level") or "Routine",
        )
        surgery = surgery_engine.recommend(
            required=bool(inp.get("surgery_required")),
            procedure_names=inp.get("surgery_procedure_names") or [],
            windows=inp.get("surgery_windows") or [],
            doctor_id=assignment.selected_doctor_id,
            doctor_name=assignment.selected_doctor_name,
            duration_minutes=int(inp.get("surgery_duration_minutes") or 0),
        )
        follow = follow_engine.plan(
            appointment_date=date.fromisoformat(inp["appointment_date"]),
            interval_days=int(inp["follow_up_interval_days"]),
            priority_level=inp.get("emergency_level") or "Routine",
        )
        queue = queue_engine.optimize(
            doctor_id=assignment.selected_doctor_id,
            appointment_date=inp.get("appointment_date"),
            appointments=inp.get("queue_appointments") or [],
            priority_by_patient=inp.get("queue_priorities") or {},
        )
        doctor_loads = [
            DoctorWorkload(**row)
            for row in (inp.get("workload_doctors") or [])
        ]
        balance = balance_engine.balance(doctors=doctor_loads)
        bundles.append(
            {"case": item, "assignment": assignment, "appointment": appointment,
             "surgery": surgery, "follow": follow, "queue": queue, "balance": balance}
        )

    results: dict[str, dict[str, Any]] = {}

    records=[]
    matches=[]
    for b in bundles:
        gt=b["case"]["ground_truth"]["doctor_assignment"]["doctor_id"]
        pred=b["assignment"].selected_doctor_id
        matches.append(pred==gt)
        records.append(case_result(agent="Scheduling",task_id="scheduling_doctor_assignment",
            case_id=b["case"]["case_id"],prediction=pred,ground_truth=gt,metrics={"match":pred==gt}))
    metrics=exact_score(matches)
    summary=base_summary(task_id="scheduling_doctor_assignment",task="Doctor Assignment",metric="Exact-match Accuracy",value=metrics["accuracy"],cases=len(cases),
        note=f"Reference assignment requires a suitable available specialist; exact-match accuracy {metrics['accuracy']*100:.1f}%.",
        **metrics)
    write_task_results("scheduling_doctor_assignment",records,summary);results["scheduling_doctor_assignment"]=summary

    records=[];matches=[]
    for b in bundles:
        gt=b["case"]["ground_truth"]["appointment_scheduling"]; p=b["appointment"].recommended_slot
        pred=None if p is None else {"doctor_id":p.doctor_id,"date":p.appointment_date,"start_time":p.start_time,"end_time":p.end_time}
        matches.append(pred==gt)
        records.append(case_result(agent="Scheduling",task_id="scheduling_appointment_scheduling",case_id=b["case"]["case_id"],prediction=pred,ground_truth=gt,metrics={"match":pred==gt}))
    metrics=exact_score(matches)
    summary=base_summary(task_id="scheduling_appointment_scheduling",task="Appointment Scheduling",metric="Exact-slot Accuracy",value=metrics["accuracy"],cases=len(cases),
        note=f"Reference slot is the earliest feasible slot in the supplied availability window. Exact-slot accuracy {metrics['accuracy']*100:.1f}%.",**metrics)
    write_task_results("scheduling_appointment_scheduling",records,summary);results["scheduling_appointment_scheduling"]=summary

    records=[];matches=[]
    for b in bundles:
        gt=b["case"]["ground_truth"]["surgery_scheduling"]; p=b["surgery"]
        if gt.get("slot") is None:
            pred={"required":p.required,"duration_minutes":p.duration_minutes,"slot":None} if p.recommended_slot is None else {"required":p.required,"duration_minutes":p.duration_minutes,"date":p.recommended_slot.appointment_date,"start_time":p.recommended_slot.start_time,"end_time":p.recommended_slot.end_time}
        else:
            pred={"required":p.required,"duration_minutes":p.duration_minutes,"date":p.recommended_slot.appointment_date if p.recommended_slot else None,"start_time":p.recommended_slot.start_time if p.recommended_slot else None,"end_time":p.recommended_slot.end_time if p.recommended_slot else None}
        matches.append(pred==gt)
        records.append(case_result(agent="Scheduling",task_id="scheduling_surgery_scheduling",case_id=b["case"]["case_id"],prediction=pred,ground_truth=gt,metrics={"match":pred==gt}))
    metrics=exact_score(matches)
    summary=base_summary(task_id="scheduling_surgery_scheduling",task="Surgery Scheduling",metric="Constraint/Plan Accuracy",value=metrics["accuracy"],cases=len(cases),
        note=f"Reference checks required/not-required state, available doctor, procedure duration and feasible window. Exact plan agreement {metrics['accuracy']*100:.1f}%.",**metrics)
    write_task_results("scheduling_surgery_scheduling",records,summary);results["scheduling_surgery_scheduling"]=summary

    records=[];matches=[]
    for b in bundles:
        gt=b["case"]["ground_truth"]["follow_up_planning"];pred={"interval_days":b["follow"].interval_days,"recommended_date":b["follow"].recommended_date}
        matches.append(pred==gt)
        records.append(case_result(agent="Scheduling",task_id="scheduling_follow_up_planning",case_id=b["case"]["case_id"],prediction=pred,ground_truth=gt,metrics={"match":pred==gt}))
    metrics=exact_score(matches)
    summary=base_summary(task_id="scheduling_follow_up_planning",task="Follow-Up Planning",metric="Interval/Date Accuracy",value=metrics["accuracy"],cases=len(cases),
        note=f"Reference follows the implemented priority-aware interval cap rules. Exact interval/date agreement {metrics['accuracy']*100:.1f}%.",**metrics)
    write_task_results("scheduling_follow_up_planning",records,summary);results["scheduling_follow_up_planning"]=summary

    records=[];position_matches=[];exact_matches=[]
    for b in bundles:
        gt=b["case"]["ground_truth"]["queue_optimization"]["ordered_ids"]
        pred=[x.appointment_id for x in b["queue"].ordered_queue]
        exact=pred==gt;exact_matches.append(exact)
        n=max(len(gt),len(pred),1);position_matches.append(sum(1 for j in range(min(len(gt),len(pred))) if gt[j]==pred[j])/n)
        records.append(case_result(agent="Scheduling",task_id="scheduling_queue_optimization",case_id=b["case"]["case_id"],prediction=pred,ground_truth=gt,metrics={"exact_sequence_match":exact,"position_accuracy":position_matches[-1]}))
    pos_acc=sum(position_matches)/len(position_matches); exact_acc=accuracy(exact_matches)
    summary=base_summary(task_id="scheduling_queue_optimization",task="Queue Optimization",metric="Queue Position Accuracy",value=pos_acc,cases=len(cases),
        note=f"Position agreement across generated patient queues is {pos_acc*100:.1f}%; full-sequence accuracy is {exact_acc*100:.1f}%.",accuracy=pos_acc,secondary_metrics={"exact_sequence_accuracy":exact_acc})
    write_task_results("scheduling_queue_optimization",records,summary);results["scheduling_queue_optimization"]=summary

    records=[];matches=[];gap_errors=[]
    for b in bundles:
        gt=b["case"]["ground_truth"]["workload_balancing"]
        pred_id=None
        recommendation=str(b["balance"].recommendation or "")
        for doctor in b["balance"].doctor_loads:
            if doctor.doctor_name and doctor.doctor_name in recommendation:
                pred_id=doctor.doctor_id
                break
        matches.append(pred_id==gt["doctor_id"]);gap_errors.append(abs(float(b["balance"].balance_gap)-float(gt["balance_gap"])))
        records.append(case_result(agent="Scheduling",task_id="scheduling_workload_balancing",case_id=b["case"]["case_id"],prediction={"doctor_id":pred_id,"balance_gap":b["balance"].balance_gap,"recommendation":recommendation},ground_truth=gt,metrics={"match":pred_id==gt["doctor_id"],"gap_abs_error":gap_errors[-1]}))
    acc=accuracy(matches); mae=sum(gap_errors)/len(gap_errors) if gap_errors else 0
    summary=base_summary(task_id="scheduling_workload_balancing",task="Workload Balancing",metric="Recommendation Accuracy",value=acc,cases=len(cases),
        note=f"Reference recommends the lowest-load available doctor in the supplied workload set. Recommendation accuracy {acc*100:.1f}%; mean workload-gap error {mae:.2f}.",accuracy=acc,secondary_metrics={"mean_gap_absolute_error":mae})
    write_task_results("scheduling_workload_balancing",records,summary);results["scheduling_workload_balancing"]=summary

    return results


# ---------------------------------------------------------------------------
# Resource Allocation
# ---------------------------------------------------------------------------

def run_resource_allocation(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    from app.ai.resource_allocation.availability_assessor import AvailabilityAssessor
    from app.ai.resource_allocation.models import ResourceRequirement

    assessor=AvailabilityAssessor()
    task_map={"Bed":"resource_allocation_bed_allocation","ICU Bed":"resource_allocation_icu_allocation","Ventilator":"resource_allocation_ventilator_allocation","Medical Equipment":"resource_allocation_equipment_allocation"}

    bundles=[]
    for item in cases:
        inp=item["input"]
        reqs=[ResourceRequirement(**r) for r in inp["requirements"]]
        outputs=assessor.assess(requirements=reqs,resources=inp["resources"],doctors=inp["doctors"],selected_doctor_id=inp.get("selected_doctor_id"),preferred_specialists=inp.get("preferred_specialists") or [])
        bundles.append({"case":item,"outputs":outputs})

    results={}
    for resource_type,task_id in task_map.items():
        records=[];matches=[]
        for b in bundles:
            pred_item=next(x for x in b["outputs"] if x.resource_type==resource_type)
            gt=b["case"]["ground_truth"][task_id.replace("resource_allocation_","")]
            pred={"required":pred_item.required_quantity,"available":pred_item.available_quantity,"allocated":pred_item.allocated_quantity,"status":pred_item.status}
            matches.append(pred==gt)
            records.append(case_result(agent="Resource Allocation",task_id=task_id,case_id=b["case"]["case_id"],prediction=pred,ground_truth=gt,metrics={"match":pred==gt}))
        m=exact_score(matches)
        label=resource_type if resource_type!="Medical Equipment" else "Equipment"
        summary=base_summary(task_id=task_id,task=f"{label} Allocation",metric="Allocation Accuracy",value=m["accuracy"],cases=len(cases),
            note=f"Availability-based allocation benchmark for {label.lower()}: exact agreement with the explicit resource-capacity reference rule. Accuracy {m['accuracy']*100:.1f}%.",**m)
        write_task_results(task_id,records,summary);results[task_id]=summary

    records=[];matches=[]
    for b in bundles:
        gt=b["case"]["ground_truth"]["staff_allocation"]
        pred_item=next(x for x in b["outputs"] if x.requirement=="Specialist Staff")
        pred_id=pred_item.matched_resources[0].resource_id if pred_item.matched_resources else None
        pred={"doctor_id":pred_id,"status":pred_item.status,"available":pred_item.available_quantity,"allocated":pred_item.allocated_quantity}
        matches.append(pred==gt)
        records.append(case_result(agent="Resource Allocation",task_id="resource_allocation_staff_allocation",case_id=b["case"]["case_id"],prediction=pred,ground_truth=gt,metrics={"match":pred==gt}))
    m=exact_score(matches)
    summary=base_summary(task_id="resource_allocation_staff_allocation",task="Staff Allocation",metric="Assignment Accuracy",value=m["accuracy"],cases=len(cases),
        note=f"Specialist assignment benchmark using explicit selected-doctor and specialization references. Exact assignment accuracy {m['accuracy']*100:.1f}%.",**m)
    write_task_results("resource_allocation_staff_allocation",records,summary);results["resource_allocation_staff_allocation"]=summary

    # Current Resource Allocation Agent has no demand-forecasting implementation.
    demand_summary={
        "task_id":"resource_allocation_demand_forecasting",
        "task":"Demand Forecasting",
        "status":"NOT_IMPLEMENTED",
        "cases_evaluated":0,
        "cases_in_benchmark":len(cases),
        "dataset":"HOS-OPS-REF-25-v1 (synthetic project reference)",
        "note":"The current Resource Allocation Agent implementation is planning/allocation only; no demand forecasting model is present, so no score is produced.",
    }
    RESULT_ROOT.mkdir(parents=True,exist_ok=True)
    (RESULT_ROOT/"resource_allocation_demand_forecasting.summary.json").write_text(json.dumps(demand_summary,indent=2)+"\n",encoding="utf-8")
    results["resource_allocation_demand_forecasting"]=demand_summary
    return results


def main() -> int:
    parser=argparse.ArgumentParser(description="Run dataset-grounded validation for operational agents.")
    parser.add_argument("--cases",type=int,default=25,help="Maximum benchmark cases per agent (1-25).")
    parser.add_argument("--agent",choices=["emergency","scheduling","resource_allocation","all"],default="all")
    args=parser.parse_args()
    if not BENCHMARK_PATH.is_file():
        raise SystemExit(f"Benchmark dataset missing: {BENCHMARK_PATH}")
    payload=json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    limit=max(1,min(int(args.cases),25))
    outputs={}
    if args.agent in ("emergency","all"): outputs["emergency"]=run_emergency(payload["emergency_cases"][:limit])
    if args.agent in ("scheduling","all"): outputs["scheduling"]=run_scheduling(payload["scheduling_cases"][:limit])
    if args.agent in ("resource_allocation","all"): outputs["resource_allocation"]=run_resource_allocation(payload["resource_allocation_cases"][:limit])
    summary={
        "benchmark_id":payload["benchmark_id"],
        "benchmark_type":payload["type"],
        "cases_per_agent":limit,
        "agents":outputs,
        "note":"Synthetic project-reference dataset; metrics validate deterministic rule/constraint agreement, not clinical accuracy.",
    }
    RESULT_ROOT.mkdir(parents=True,exist_ok=True)
    (RESULT_ROOT/"benchmark_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
