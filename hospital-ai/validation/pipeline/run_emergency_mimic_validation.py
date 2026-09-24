"""Validate Emergency Triage Classification against MIMIC-IV-ED triage acuity.

Expected input:
  path to MIMIC-IV-ED `triage.csv` or `triage.csv.gz`.

Ground-truth mapping used for this project benchmark:
  acuity 1-2 -> Critical
  acuity 3   -> Urgent
  acuity 4   -> Semi-Urgent
  acuity 5   -> Routine

The mapping is a project benchmark convention, not an official replacement
for a clinical triage scale. Per-case predictions are stored as JSONL and
aggregate Accuracy and Macro F1 are written to summary.json.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.ai.emergency.critical_event_detector import CriticalEventDetector
from app.ai.emergency.models import CriticalEventDetectionResult
from app.ai.emergency.triage_classifier import EmergencyTriageClassifier
from app.ai.emergency.vital_monitor import VitalMonitor

def label_for_acuity(value: int) -> str:
    if value in (1, 2): return "Critical"
    if value == 3: return "Urgent"
    if value == 4: return "Semi-Urgent"
    if value == 5: return "Routine"
    raise ValueError(f"Unsupported MIMIC acuity value: {value}")

def macro_f1(y_true: list[str], y_pred: list[str]) -> float:
    labels = sorted(set(y_true) | set(y_pred))
    values = []
    for label in labels:
        tp = sum(a == label and b == label for a, b in zip(y_true, y_pred))
        fp = sum(a != label and b == label for a, b in zip(y_true, y_pred))
        fn = sum(a == label and b != label for a, b in zip(y_true, y_pred))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        values.append((2 * precision * recall / (precision + recall)) if precision + recall else 0.0)
    return round(sum(values) / len(values), 4) if values else 0.0

def open_csv(path: Path):
    if path.suffix == ".gz": return gzip.open(path, "rt", newline="", encoding="utf-8")
    return path.open("r", newline="", encoding="utf-8")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--triage", required=True, help="Path to MIMIC-IV-ED triage.csv or triage.csv.gz")
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--output", default="validation/results/dataset/emergency_triage")
    args = parser.parse_args()

    triage_path = Path(args.triage)
    if not triage_path.is_file(): raise SystemExit(f"Dataset file not found: {triage_path}")
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    case_path = output_dir / "cases.jsonl"

    monitor = VitalMonitor()
    classifier = EmergencyTriageClassifier()
    y_true: list[str] = []
    y_pred: list[str] = []
    processed = 0

    with open_csv(triage_path) as handle, case_path.open("w", encoding="utf-8") as out:
        reader = csv.DictReader(handle)
        required = {"stay_id", "acuity", "chiefcomplaint", "heartrate", "o2sat", "sbp", "dbp"}
        missing = required - set(reader.fieldnames or [])
        if missing: raise SystemExit(f"Missing required MIMIC triage columns: {sorted(missing)}")

        for row in reader:
            if args.max_cases is not None and processed >= args.max_cases: break
            try: acuity = int(float(row.get("acuity", "")))
            except (TypeError, ValueError): continue
            if acuity not in {1,2,3,4,5}: continue

            vitals = []
            mappings = [("Heart Rate", "heartrate", "bpm"), ("SpO2", "o2sat", "%")
                        , ("Blood Pressure", None, "mmHg")]
            for name, key, unit in mappings:
                if key:
                    if str(row.get(key) or "").strip(): vitals.append({"name":name,"value":row[key],"unit":unit})
                else:
                    if str(row.get("sbp") or "").strip() and str(row.get("dbp") or "").strip():
                        vitals.append({"name":name,"value":f"{row['sbp']}/{row['dbp']}","unit":unit})

            monitoring = monitor.monitor(vitals)
            events = CriticalEventDetector().detect(
                conditions=[],
                symptoms=[str(row.get("chiefcomplaint") or "")],
                monitoring=monitoring,
                risk_level=None,
                risk_alerts=[],
            )
            prediction = classifier.classify(
                monitoring=monitoring, events=events, risk_score=None, risk_level=None
            ).category
            truth = label_for_acuity(acuity)
            y_true.append(truth); y_pred.append(prediction); processed += 1
            out.write(json.dumps({
                "case_id": f"MIMIC-ED-{row['stay_id']}",
                "task_id": "emergency_triage_classification",
                "status": "SCORED",
                "prediction": prediction,
                "ground_truth": truth,
                "metrics": {"match": prediction == truth},
                "input": {"triage_vitals": vitals, "chief_complaint_present": bool(str(row.get("chiefcomplaint") or "").strip())},
            }) + "\n")

    accuracy = sum(a == b for a, b in zip(y_true, y_pred)) / len(y_true) if y_true else 0.0
    summary = {
        "task_id": "emergency_triage_classification",
        "dataset": "MIMIC-IV-ED triage",
        "mapping": {"1-2":"Critical","3":"Urgent","4":"Semi-Urgent","5":"Routine"},
        "cases_evaluated": len(y_true),
        "accuracy": round(accuracy, 4),
        "macro_f1": macro_f1(y_true, y_pred),
        "case_file": str(case_path.as_posix()),
        "clinical_accuracy_claim": False,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())