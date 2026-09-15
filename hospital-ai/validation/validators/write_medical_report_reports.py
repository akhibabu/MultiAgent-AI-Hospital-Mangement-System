"""
Write task-level Medical Report Agent validation reports.

Reads evaluated run metrics and case results. Never invents scores.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PIPELINE_DIR = Path(__file__).resolve().parents[1] / "pipeline"
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))

from medical_report_catalog import (  # noqa: E402
    MEDICAL_REPORT_TASKS,
    MEDICAL_REPORT_TASK_IDS,
    task_meta,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_ROOT = PROJECT_ROOT / "validation"
METRICS_ROOT = VALIDATION_ROOT / "results" / "metrics"
RAW_ROOT = VALIDATION_ROOT / "results" / "raw"
MEDICAL_REPORT_ROOT = VALIDATION_ROOT / "results" / "medical_report"
MANIFEST_PATH = VALIDATION_ROOT / "ground_truth" / "validation_case_manifest.json"
REGISTRY_PATH = VALIDATION_ROOT / "config" / "task_registry.json"
CASES_ROOT = VALIDATION_ROOT / "ground_truth" / "cases"

NOT_VALIDATABLE_REASONS = {
    "medical_report_doctor_notes_generation": (
        "MIMIC-IV Demo excludes free-text clinical notes; no reference SOAP notes exist."
    ),
    "medical_report_referral_letter_creation": (
        "No reference referral letters exist for these encounters."
    ),
    "medical_report_patient_report_generation": (
        "No reference patient-facing reports exist. Readability alone would not "
        "establish that the content is correct."
    ),
}

HUMAN_REVIEW_NOTES = {
    "medical_report_clinical_summary": (
        "No reference clinical summary exists. Reviewer judges factual accuracy "
        "against supplied records; text-similarity metrics are forbidden."
    ),
    "medical_report_discharge_summary": (
        "No reference discharge summary exists. Reviewer judges coverage of "
        "admission, course, procedures and disposition without inventing content."
    ),
}

DATASET_NOTES = {
    "medical_report_insurance_documentation": (
        "MIMIC billing codes (ICD diagnosis + procedure) withheld from input; "
        "DRG codes are in ground truth but excluded from automatic scoring."
    ),
    "medical_report_clinical_summary": (
        "MIMIC encounter data (vitals, labs, meds, admissions) without reference summary text."
    ),
    "medical_report_discharge_summary": (
        "MIMIC admission/discharge context without reference discharge narrative."
    ),
}

EXECUTABLE_TASKS = frozenset(
    {
        "medical_report_clinical_summary",
        "medical_report_discharge_summary",
        "medical_report_insurance_documentation",
    }
)


def _load(path: Path) -> Any:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _newest_metrics_dir() -> Optional[Path]:
    if not METRICS_ROOT.is_dir():
        return None
    candidates = [path for path in METRICS_ROOT.iterdir() if path.is_dir()]
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def _dataset_counts() -> Dict[str, int]:
    counts = {task_id: 0 for task_id in MEDICAL_REPORT_TASK_IDS}
    manifest = _load(MANIFEST_PATH) or {}
    for case in manifest.get("cases") or []:
        task_id = str(case.get("task_id") or "")
        if task_id in counts:
            counts[task_id] += 1
    report_dir = CASES_ROOT / "medical_report"
    if report_dir.is_dir():
        for task_id in MEDICAL_REPORT_TASK_IDS:
            task_cases = list(report_dir.glob(f"VC-{task_id}-*.json"))
            if task_cases:
                counts[task_id] = len(task_cases)
    return counts


def _registry_notes() -> Dict[str, Dict[str, Any]]:
    return {
        item["task_id"]: item
        for item in (_load(REGISTRY_PATH) or {}).get("tasks") or []
        if str(item.get("task_id") or "").startswith("medical_report_")
    }


def _raw_index(run_id: Optional[str]) -> Dict[str, Dict[str, Any]]:
    if not run_id:
        return {}
    path = RAW_ROOT / run_id / "results.jsonl"
    if not path.is_file():
        return {}
    index: Dict[str, Dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        case_id = str(row.get("validation_case_id") or row.get("case_id") or "")
        if case_id:
            index[case_id] = row
    return index


def _iter_case_results(metrics_dir: Path) -> List[Dict[str, Any]]:
    path = metrics_dir / "case_results.jsonl"
    if not path.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _load_case_files(task_id: str) -> Dict[str, Dict[str, Any]]:
    directory = CASES_ROOT / "medical_report"
    if not directory.is_dir():
        return {}
    files: Dict[str, Dict[str, Any]] = {}
    for path in directory.glob(f"VC-{task_id}-*.json"):
        payload = _load(path) or {}
        files[path.stem] = payload
    return files


def _billing_gt_text(ground_truth: Dict[str, Any]) -> str:
    if ground_truth.get("kind") != "BILLING_CODE_SET":
        return str(ground_truth.get("reason") or "")
    lines: List[str] = []
    for item in ground_truth.get("items") or []:
        if item.get("name") not in {"diagnosis_code", "procedure_code"}:
            continue
        display = (item.get("derived_display") or {}).get("value")
        code = (item.get("value") or {}).get("icd_code")
        if display:
            lines.append(f"• {display} ({code})")
        elif code:
            lines.append(f"• {code}")
    return "\n".join(lines[:30])


def _insurance_output_text(output: Any) -> str:
    if not isinstance(output, dict):
        return str(output or "")
    lines: List[str] = []
    for key in ("diagnosis_codes", "procedure_codes"):
        entries = output.get(key) or []
        for entry in entries[:15]:
            if isinstance(entry, dict):
                code = entry.get("code") or entry.get("icd_code") or "?"
                desc = entry.get("description") or entry.get("title") or ""
                lines.append(f"• {code} {desc}".strip())
            else:
                lines.append(f"• {entry}")
    return "\n".join(lines)


def _summary_output_text(output: Any, task_id: str) -> str:
    if not isinstance(output, dict):
        return str(output or "")
    if task_id == "medical_report_clinical_summary":
        parts = [
            output.get("patient_overview"),
            output.get("chief_complaint"),
            output.get("history"),
            output.get("diagnosis_summary"),
        ]
        return "\n\n".join(str(part) for part in parts if part)
    if task_id == "medical_report_discharge_summary":
        parts = [
            output.get("admission_reason"),
            output.get("hospital_course"),
            output.get("condition_on_discharge"),
            output.get("follow_up"),
        ]
        return "\n\n".join(str(part) for part in parts if part)
    return json.dumps(output, indent=2)[:2000]


def _case_metrics(evaluation: Dict[str, Any]) -> Dict[str, Optional[float]]:
    metrics = evaluation.get("metrics") or {}
    strict = metrics.get("strict") if isinstance(metrics.get("strict"), dict) else {}
    if strict:
        return {
            "recall": strict.get("recall"),
            "precision": strict.get("precision"),
            "f1": strict.get("f1"),
        }
    return {}


def _sanitize_case(
    record: Dict[str, Any],
    raw_by_case: Dict[str, Dict[str, Any]],
    case_files: Dict[str, Dict[str, Any]],
    gt_loader: Any = None,
) -> Dict[str, Any]:
    case_id = str(record.get("case_id") or "")
    evaluation = record.get("evaluation") or {}
    raw = raw_by_case.get(case_id) or {}
    case_file = case_files.get(case_id) or {}
    ground_truth = case_file.get("ground_truth") or {}
    if not ground_truth and gt_loader is not None:
        try:
            loaded = gt_loader.load(case_id)
            ground_truth = loaded.ground_truth or {}
        except Exception:  # noqa: BLE001
            ground_truth = {}
    output = raw.get("agent_output") or {}
    metrics = _case_metrics(evaluation)
    task_id = str(record.get("task") or record.get("task_id") or "")
    if metrics.get("recall") is not None:
        summary = f"Recall={metrics['recall']:.1%}"
    else:
        summary = str(evaluation.get("status") or record.get("status") or "")
    gt_text = (
        _billing_gt_text(ground_truth)
        if ground_truth.get("kind") == "BILLING_CODE_SET"
        else "No reference text — human review against source records."
    )
    agent_text = (
        _insurance_output_text(output)
        if task_id == "medical_report_insurance_documentation"
        else _summary_output_text(output, task_id)
    )
    return {
        "case_id": case_id,
        "agent": "medical_report",
        "task": task_id,
        "prediction": output,
        "ground_truth": ground_truth,
        "metrics": metrics,
        "status": evaluation.get("status") or record.get("status"),
        "execution_status": (raw.get("execution") or {}).get("status"),
        "timestamp": (record.get("reproducibility") or {}).get("evaluated_at"),
        "agent_text": agent_text,
        "ground_truth_text": gt_text,
        "human_summary": summary,
    }


def _headline_from_quality(task_id: str, quality: Dict[str, Any]) -> Dict[str, Any]:
    primary = task_meta(task_id).get("primary_metric") or "recall"
    micro = quality.get("micro") if isinstance(quality, dict) else None
    macro = (quality.get("macro_over_cases") or {}) if isinstance(quality, dict) else {}
    recall = None
    precision = None
    f1 = None
    if isinstance(micro, dict):
        recall = micro.get("recall")
        precision = micro.get("precision")
        f1 = micro.get("f1")
    if recall is None and isinstance(macro, dict):
        recall = macro.get("recall")
        precision = macro.get("precision")
        f1 = macro.get("f1")
    return {
        "primary_metric": primary,
        "recall": recall,
        "precision": precision,
        "f1": f1,
        "applicable": ["recall", "precision", "f1"],
        "notes": [
            DATASET_NOTES.get(task_id, ""),
            "Matching uses strict ICD title equality; DRG codes are excluded from scoring.",
            "Reference reflects billed codes, not re-adjudicated clinical truth.",
        ],
    }


def _display_metrics(headline: Dict[str, Any]) -> List[Dict[str, Any]]:
    labels = {
        "recall": "Recall",
        "precision": "Precision",
        "f1": "F1",
    }
    rows: List[Dict[str, Any]] = []
    for key, label in labels.items():
        value = headline.get(key)
        if value is not None:
            rows.append({"key": key, "label": label, "value": value})
    return rows


def _main_metric(headline: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    key = str(headline.get("primary_metric") or "recall")
    labels = {"recall": "Recall", "precision": "Precision", "f1": "F1"}
    value = headline.get(key)
    if value is None:
        return None
    return {"key": key, "label": labels.get(key, key), "value": value}


def build_medical_report_reports(metrics_dir: Optional[Path] = None) -> Dict[str, Any]:
    metrics_dir = metrics_dir or _newest_metrics_dir()
    task_metrics: Dict[str, Any] = {}
    if metrics_dir and (metrics_dir / "task_metrics.json").is_file():
        payload = _load(metrics_dir / "task_metrics.json") or {}
        task_metrics = payload.get("task_metrics") or payload

    dataset_counts = _dataset_counts()
    registry = _registry_notes()
    cases_by_task: Dict[str, List[Dict[str, Any]]] = {
        task_id: [] for task_id in MEDICAL_REPORT_TASK_IDS
    }
    case_rows_by_task: Dict[str, List[Dict[str, Any]]] = {
        task_id: [] for task_id in MEDICAL_REPORT_TASK_IDS
    }
    gt_loader = None
    if metrics_dir:
        from ground_truth_loader import GroundTruthLoader

        gt_loader = GroundTruthLoader()
        raw_index = _raw_index(metrics_dir.name)
        case_files_by_task = {
            task_id: _load_case_files(task_id) for task_id in MEDICAL_REPORT_TASK_IDS
        }
        for row in _iter_case_results(metrics_dir):
            task_id = str(row.get("task") or row.get("task_id") or "")
            if task_id in cases_by_task:
                case_files = case_files_by_task.get(task_id) or {}
                cases_by_task[task_id].append(
                    _sanitize_case(row, raw_index, case_files, gt_loader)
                )
                case_rows_by_task[task_id].append(row)

    timestamp = datetime.now(timezone.utc).isoformat()
    tasks_out: List[Dict[str, Any]] = []
    files: Dict[str, Dict[str, Any]] = {}

    for meta in MEDICAL_REPORT_TASKS:
        task_id = meta["task_id"]
        entry = task_metrics.get(task_id) or {}
        sample = entry.get("sample") or {}
        total = int(dataset_counts.get(task_id) or 0)
        evaluated = int(sample.get("evaluated") or 0)
        failed = int(sample.get("execution_failed") or 0)
        coverage = (evaluated / total) if total else None
        is_quantitative = meta.get("validatable") == "true" and total > 0
        is_human_review = task_id in HUMAN_REVIEW_NOTES and total > 0

        if task_id in NOT_VALIDATABLE_REASONS and total == 0:
            reason = NOT_VALIDATABLE_REASONS[task_id]
            status = "NOT_VALIDATABLE"
            payload = {
                "agent": "medical_report",
                "task": task_id,
                "task_label": meta["label"],
                "total_cases": total,
                "eligible_cases": total,
                "evaluated_cases": 0,
                "failed_cases": failed,
                "coverage": None,
                "coverage_note": "Coverage is evaluated_cases / dataset_cases. It is not accuracy.",
                "metrics": {},
                "metric_applicability": [],
                "metric_notes": [reason],
                "display_metrics": [],
                "main_metric": None,
                "human_summary": reason,
                "status": status,
                "dataset_mapping": (registry.get(task_id) or {}).get("dataset_mapping"),
                "validator": meta.get("validator"),
                "validation_timestamp": timestamp,
                "source_metrics_dir": str(metrics_dir.name) if metrics_dir else None,
                "per_case_results": [],
            }
        elif is_human_review:
            reason = HUMAN_REVIEW_NOTES[task_id]
            status = "PENDING_HUMAN_REVIEW" if evaluated else "NOT_EXECUTED"
            payload = {
                "agent": "medical_report",
                "task": task_id,
                "task_label": meta["label"],
                "total_cases": total,
                "eligible_cases": total,
                "evaluated_cases": evaluated,
                "failed_cases": failed,
                "coverage": coverage if evaluated else None,
                "coverage_note": "Coverage is executed_cases / dataset_cases. It is not accuracy.",
                "metrics": {},
                "metric_applicability": [],
                "metric_notes": [reason],
                "display_metrics": [],
                "main_metric": None,
                "human_summary": reason,
                "status": status,
                "dataset_mapping": DATASET_NOTES.get(task_id),
                "validator": meta.get("validator"),
                "validation_timestamp": timestamp,
                "source_metrics_dir": str(metrics_dir.name) if metrics_dir else None,
                "per_case_results": cases_by_task.get(task_id) or [],
            }
        elif is_quantitative:
            headline = _headline_from_quality(task_id, entry.get("quality") or {})
            status = str(entry.get("status") or ("VALIDATED" if evaluated else "NOT_EXECUTED"))
            primary = headline.get("primary_metric") or "recall"
            primary_value = headline.get(primary)
            payload = {
                "agent": "medical_report",
                "task": task_id,
                "task_label": meta["label"],
                "total_cases": total,
                "eligible_cases": int(sample.get("eligible_cases") or total),
                "evaluated_cases": evaluated,
                "failed_cases": failed,
                "coverage": coverage,
                "coverage_note": "Coverage is evaluated_cases / dataset_cases. It is not accuracy.",
                "metrics": {
                    "recall": headline.get("recall"),
                    "precision": headline.get("precision"),
                    "f1": headline.get("f1"),
                },
                "metric_applicability": headline.get("applicable") or [],
                "metric_notes": headline.get("notes") or [],
                "display_metrics": _display_metrics(headline),
                "main_metric": _main_metric(headline),
                "human_summary": (
                    f"{_main_metric(headline)['label']} {primary_value:.1%}"
                    if primary_value is not None and _main_metric(headline)
                    else None
                ),
                "status": status,
                "dataset_mapping": DATASET_NOTES.get(task_id),
                "validator": meta.get("validator"),
                "validation_timestamp": timestamp,
                "source_metrics_dir": str(metrics_dir.name) if metrics_dir else None,
                "per_case_results": cases_by_task.get(task_id) or [],
            }
        else:
            reason = NOT_VALIDATABLE_REASONS.get(
                task_id,
                (registry.get(task_id) or {}).get("dataset_mapping") or "No benchmark imported.",
            )
            payload = {
                "agent": "medical_report",
                "task": task_id,
                "task_label": meta["label"],
                "total_cases": total,
                "eligible_cases": total,
                "evaluated_cases": 0,
                "failed_cases": failed,
                "coverage": None,
                "coverage_note": "Coverage is evaluated_cases / dataset_cases. It is not accuracy.",
                "metrics": {},
                "metric_applicability": [],
                "metric_notes": [reason],
                "display_metrics": [],
                "main_metric": None,
                "human_summary": reason,
                "status": "NOT_VALIDATABLE",
                "dataset_mapping": (registry.get(task_id) or {}).get("dataset_mapping"),
                "validator": meta.get("validator"),
                "validation_timestamp": timestamp,
                "source_metrics_dir": str(metrics_dir.name) if metrics_dir else None,
                "per_case_results": [],
            }

        files[meta["slug"]] = payload
        tasks_out.append(
            {
                "task": task_id,
                "task_label": meta["label"],
                "slug": meta["slug"],
                "total_cases": payload["total_cases"],
                "eligible_cases": payload["eligible_cases"],
                "evaluated_cases": payload["evaluated_cases"],
                "failed_cases": payload["failed_cases"],
                "coverage": payload["coverage"],
                "status": payload["status"],
                "notes": payload.get("metric_notes") or [],
                "display_metrics": payload.get("display_metrics") or [],
                "main_metric": payload.get("main_metric"),
                "human_summary": payload.get("human_summary"),
            }
        )

    summary = {
        "agent": "medical_report",
        "title": "MEDICAL REPORT AGENT VALIDATION",
        "validation_timestamp": timestamp,
        "source_metrics_dir": str(metrics_dir.name) if metrics_dir else None,
        "dataset_cases_total": sum(int(row["total_cases"] or 0) for row in tasks_out),
        "tasks": tasks_out,
        "overall_score": None,
        "overall_score_note": (
            "No overall Medical Report Agent score is computed. Insurance coding, "
            "clinical summaries and discharge narratives use different references."
        ),
        "coverage_vs_performance_note": (
            "Dataset coverage is evaluated_cases / dataset_cases. It is not accuracy."
        ),
    }
    return {"summary": summary, "tasks": files}


def _evaluated_total(bundle: Dict[str, Any]) -> int:
    tasks = bundle.get("summary", {}).get("tasks") or []
    return sum(int(row.get("evaluated_cases") or 0) for row in tasks)


def write_medical_report_reports(metrics_dir: Optional[Path] = None) -> Path:
    bundle = build_medical_report_reports(metrics_dir)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = MEDICAL_REPORT_ROOT / stamp
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "summary.json").write_text(json.dumps(bundle["summary"], indent=2), encoding="utf-8")
    for slug, payload in bundle["tasks"].items():
        (dest / f"{slug}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest = MEDICAL_REPORT_ROOT / "latest"
    new_total = _evaluated_total(bundle)
    old_total = 0
    if latest.is_dir() and (latest / "summary.json").is_file():
        old_summary = _load(latest / "summary.json") or {}
        old_total = sum(int(row.get("evaluated_cases") or 0) for row in old_summary.get("tasks") or [])
    if new_total >= old_total:
        if latest.exists() or latest.is_symlink():
            if latest.is_dir() and not latest.is_symlink():
                shutil.rmtree(latest)
            else:
                latest.unlink()
        shutil.copytree(dest, latest)
    pointer = {"current": stamp, "written_at": bundle["summary"]["validation_timestamp"]}
    (MEDICAL_REPORT_ROOT / "current.json").write_text(json.dumps(pointer, indent=2), encoding="utf-8")
    return dest


def finalize_medical_report_validation(run_id: str) -> Path:
    from run_evaluation import main as evaluate_main

    evaluate_main(["--run-id", run_id, "--agent", "medical_report", "--task", "ALL", "--force"])
    metrics_dir = METRICS_ROOT / run_id
    return write_medical_report_reports(metrics_dir if metrics_dir.is_dir() else None)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Write Medical Report validation task reports")
    parser.add_argument("--run-id", help="Metrics run id (defaults to newest)")
    args = parser.parse_args()
    metrics_dir = METRICS_ROOT / args.run_id if args.run_id else None
    path = write_medical_report_reports(
        metrics_dir if metrics_dir and metrics_dir.is_dir() else None
    )
    print(path)
