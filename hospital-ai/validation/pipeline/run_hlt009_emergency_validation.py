"""Dataset-grounded Emergency validation using HLT-009 alarm/vital data.

The HLT-009 sample is synthetic. This validator uses its labelled alarm stream
to evaluate two Emergency stages that HLT-005 cannot label directly:
- Real-Time Vital Monitoring: alarm-type/priority provides the expected
  warning/critical severity for supported vital streams.
- Critical Event Detection: true_alarm_flag is used only as a documented
  binary actionable-alarm proxy, not as a clinical event annotation.

Each task receives 25 independent cases by default. Per-case prediction,
ground truth, and match are stored as JSONL; aggregate metrics are written to
summary.json.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.ai.emergency.critical_event_detector import CriticalEventDetector
from app.ai.emergency.vital_monitor import VitalMonitor


SUPPORTED = {
    "HIGH_HR": ("Heart Rate", "hr_bpm"),
    "LOW_HR": ("Heart Rate", "hr_bpm"),
    "CRITICAL_LOW_HR": ("Heart Rate", "hr_bpm"),
    "LOW_SPO2": ("SpO2", "spo2_pct"),
    "CRITICAL_LOW_SPO2": ("SpO2", "spo2_pct"),
    "HIGH_SBP": ("Blood Pressure", "nbp_sys_mmhg"),
    "LOW_SBP": ("Blood Pressure", "nbp_sys_mmhg"),
}


def f1(true: list[bool], pred: list[bool]) -> float:
    tp = sum(t and p for t, p in zip(true, pred))
    fp = sum((not t) and p for t, p in zip(true, pred))
    fn = sum(t and (not p) for t, p in zip(true, pred))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def accuracy(true: list[bool], pred: list[bool]) -> float:
    return sum(t == p for t, p in zip(true, pred)) / len(true) if true else 0.0


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def nearest_vitals(
    rows: list[dict[str, str]],
    episode_id: str,
    onset: datetime | None,
) -> dict[str, str]:
    episode = [row for row in rows if str(row.get("episode_id")) == episode_id]
    if not episode:
        return {}
    if onset is None:
        return episode[0]
    best = episode[0]
    best_distance = math.inf
    for row in episode:
        timestamp = parse_ts(row.get("timestamp"))
        if timestamp is None:
            continue
        distance = abs((timestamp - onset).total_seconds())
        if distance < best_distance:
            best = row
            best_distance = distance
    return best


def vital_input(alarm: dict[str, str], vital: dict[str, str]) -> list[dict[str, str]]:
    alarm_type = str(alarm.get("alarm_type") or "").strip()
    if alarm_type not in SUPPORTED:
        return []
    name, column = SUPPORTED[alarm_type]
    value = str(vital.get(column) or "").strip()
    if not value:
        return []
    if name == "Blood Pressure":
        sbp = str(vital.get("nbp_sys_mmhg") or "").strip()
        dbp = str(vital.get("nbp_dia_mmhg") or "").strip()
        if not sbp or not dbp:
            return []
        return [{"name": name, "value": f"{sbp}/{dbp}", "unit": "mmHg"}]
    unit = "%" if name == "SpO2" else "bpm"
    return [{"name": name, "value": value, "unit": unit}]


def expected_vital_severity(alarm: dict[str, str]) -> str:
    alarm_type = str(alarm.get("alarm_type") or "").upper()
    priority = str(alarm.get("alarm_priority") or "").upper()
    if alarm_type.startswith("CRITICAL_") or priority == "CRITICAL":
        return "critical"
    return "warning"


def binary_truth(alarm: dict[str, str]) -> bool:
    raw = str(alarm.get("true_alarm_flag") or "").strip().lower()
    return raw in {"1", "true", "yes"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vitals", required=True)
    parser.add_argument("--alarms", required=True)
    parser.add_argument("--max-cases", type=int, default=25)
    parser.add_argument(
        "--output",
        default="validation/results/dataset/emergency_hlt009",
    )
    args = parser.parse_args()

    vitals = read_csv(Path(args.vitals))
    alarms = read_csv(Path(args.alarms))
    supported = [a for a in alarms if str(a.get("alarm_type") or "") in SUPPORTED]
    supported = supported[: max(args.max_cases, 1)]

    if len(supported) < args.max_cases:
        raise SystemExit(
            f"HLT-009 contains only {len(supported)} supported alarm cases; "
            f"{args.max_cases} requested."
        )

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    vital_dir = output / "emergency_vital_monitoring"
    event_dir = output / "emergency_critical_event_detection"
    vital_dir.mkdir(parents=True, exist_ok=True)
    event_dir.mkdir(parents=True, exist_ok=True)

    monitor = VitalMonitor()
    detector = CriticalEventDetector()
    severity_true: list[str] = []
    severity_pred: list[str] = []
    event_true: list[bool] = []
    event_pred: list[bool] = []
    vital_cases = []
    event_cases = []

    for index, alarm in enumerate(supported, 1):
        episode_id = str(alarm.get("episode_id") or "")
        onset = parse_ts(alarm.get("alarm_onset_ts"))
        snapshot = nearest_vitals(vitals, episode_id, onset)
        inputs = vital_input(alarm, snapshot)
        if not inputs:
            continue

        monitoring = monitor.monitor(inputs)
        detected = detector.detect(
            conditions=[],
            symptoms=[],
            monitoring=monitoring,
            risk_level=None,
            risk_alerts=[],
        )

        observed = monitoring.observations[0].severity if monitoring.observations else "unknown"
        expected = expected_vital_severity(alarm)
        severity_true.append(expected)
        severity_pred.append(observed)

        vital_case = {
            "case_id": f"HLT009-VITAL-{index:03d}",
            "task_id": "emergency_vital_monitoring",
            "status": "SCORED",
            "input": inputs,
            "prediction": {
                "monitoring_status": monitoring.monitoring_status,
                "severity": observed,
            },
            "ground_truth": {
                "severity": expected,
                "alarm_type": alarm.get("alarm_type"),
                "alarm_priority": alarm.get("alarm_priority"),
            },
            "metrics": {"match": observed == expected},
        }
        vital_cases.append(vital_case)

        truth = binary_truth(alarm)
        predicted = detected.detected_event_count > 0
        event_true.append(truth)
        event_pred.append(predicted)
        event_cases.append(
            {
                "case_id": f"HLT009-EVENT-{index:03d}",
                "task_id": "emergency_critical_event_detection",
                "status": "SCORED",
                "input": inputs,
                "prediction": {
                    "event_detected": predicted,
                    "event_count": detected.detected_event_count,
                },
                "ground_truth": {
                    "actionable_alarm": truth,
                    "alarm_type": alarm.get("alarm_type"),
                    "true_alarm_flag": alarm.get("true_alarm_flag"),
                },
                "metrics": {"match": predicted == truth},
            }
        )

    with (vital_dir / "cases.jsonl").open("w", encoding="utf-8") as handle:
        for case in vital_cases:
            handle.write(json.dumps(case) + "\n")
    with (event_dir / "cases.jsonl").open("w", encoding="utf-8") as handle:
        for case in event_cases:
            handle.write(json.dumps(case) + "\n")

    severity_accuracy = (
        sum(a == b for a, b in zip(severity_true, severity_pred))
        / len(severity_true)
        if severity_true
        else 0.0
    )
    event_f1 = f1(event_true, event_pred)

    vital_summary = {
        "task_id": "emergency_vital_monitoring",
        "dataset": "HLT-009 Synthetic Continuous Vital Sign Monitoring Dataset",
        "cases_evaluated": len(vital_cases),
        "headline_metric": "Severity Accuracy",
        "headline_value": severity_accuracy,
        "accuracy": severity_accuracy,
        "clinical_accuracy_claim": False,
        "note": (
            "Measured against the dataset's labelled alarm type/priority for "
            "supported vital streams. HLT-009 is synthetic."
        ),
    }
    event_summary = {
        "task_id": "emergency_critical_event_detection",
        "dataset": "HLT-009 Synthetic Continuous Vital Sign Monitoring Dataset",
        "cases_evaluated": len(event_cases),
        "headline_metric": "F1 (alarm proxy)",
        "headline_value": event_f1,
        "f1_score": event_f1,
        "accuracy": accuracy(event_true, event_pred),
        "clinical_accuracy_claim": False,
        "status": "VALIDATED_WITH_PROXY",
        "note": (
            "Proxy evaluation: true_alarm_flag is used as binary actionable-alarm "
            "ground truth. It is not an independently annotated diagnosis/event label."
        ),
    }
    (vital_dir / "summary.json").write_text(
        json.dumps(vital_summary, indent=2) + "\n", encoding="utf-8"
    )
    (event_dir / "summary.json").write_text(
        json.dumps(event_summary, indent=2) + "\n", encoding="utf-8"
    )
    root_summary = {
        "dataset": "HLT-009 Synthetic Continuous Vital Sign Monitoring Dataset",
        "cases_evaluated": len(vital_cases),
        "tasks": {
            "emergency_vital_monitoring": vital_summary,
            "emergency_critical_event_detection": event_summary,
        },
    }
    (output / "summary.json").write_text(
        json.dumps(root_summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(root_summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
