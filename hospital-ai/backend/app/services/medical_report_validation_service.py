"""Read stored Medical Report Agent task-level validation reports."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config.settings import get_settings
from app.schemas.medical_report_validation import (
    MedicalReportCaseDetailOut,
    MedicalReportSummaryOut,
    MedicalReportTaskDetailOut,
)

_PIPELINE = get_settings().validation_root_path / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))

from medical_report_catalog import (  # noqa: E402
    MEDICAL_REPORT_TASK_IDS,
    resolve_medical_report_task,
    task_meta,
)


class MedicalReportValidationService:
    def __init__(self, root: Optional[Path] = None) -> None:
        settings = get_settings()
        self._root = (
            Path(root) if root else settings.validation_root_path / "results" / "medical_report"
        )

    def _snapshot_dirs(self) -> List[Tuple[str, Path]]:
        found: List[Tuple[str, Path]] = []
        if not self._root.is_dir():
            return found
        for child in self._root.iterdir():
            if not child.is_dir() or child.name == "latest":
                continue
            if (child / "summary.json").is_file() or any(child.glob("*.json")):
                found.append((child.name, child))
        latest = self._root / "latest"
        if latest.is_dir():
            found.append(("latest", latest))
        return found

    def _load_json(self, path: Path) -> Dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _rank(self, payload: Dict[str, Any], stamp: str) -> Tuple[int, int, str]:
        status = str(payload.get("status") or "")
        validated = 1 if status == "VALIDATED" else 0
        human = 1 if status == "PENDING_HUMAN_REVIEW" else 0
        return (int(payload.get("evaluated_cases") or 0), validated + human, stamp)

    def best_task_reports(self) -> Dict[str, Dict[str, Any]]:
        best: Dict[str, Dict[str, Any]] = {}
        best_rank: Dict[str, Tuple[int, int, str]] = {}
        for stamp, directory in self._snapshot_dirs():
            for task_id in MEDICAL_REPORT_TASK_IDS:
                slug = task_meta(task_id)["slug"]
                path = directory / f"{slug}.json"
                if not path.is_file():
                    continue
                payload = self._load_json(path)
                if not payload.get("task"):
                    payload["task"] = task_id
                rank = self._rank(payload, stamp)
                current = best_rank.get(task_id)
                if current is None or rank > current:
                    copied = dict(payload)
                    copied["_snapshot"] = stamp
                    best[task_id] = copied
                    best_rank[task_id] = rank
        return best

    def _headline_row(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "task": payload.get("task"),
            "task_label": payload.get("task_label"),
            "slug": payload.get("slug") or task_meta(str(payload.get("task") or ""))["slug"],
            "total_cases": int(payload.get("total_cases") or 0),
            "eligible_cases": int(payload.get("eligible_cases") or payload.get("total_cases") or 0),
            "evaluated_cases": int(payload.get("evaluated_cases") or 0),
            "failed_cases": int(payload.get("failed_cases") or 0),
            "coverage": payload.get("coverage"),
            "status": payload.get("status") or "NOT_EXECUTED",
            "notes": payload.get("metric_notes") or payload.get("notes") or [],
            "display_metrics": payload.get("display_metrics") or [],
            "main_metric": payload.get("main_metric"),
            "human_summary": payload.get("human_summary"),
            "source_metrics_dir": payload.get("source_metrics_dir") or payload.get("_snapshot"),
            "validation_timestamp": payload.get("validation_timestamp"),
        }

    def summary(self) -> MedicalReportSummaryOut:
        reports = self.best_task_reports()
        tasks = []
        sources = []
        for task_id in MEDICAL_REPORT_TASK_IDS:
            payload = reports.get(task_id)
            if not payload:
                meta = task_meta(task_id)
                tasks.append(
                    {
                        "task": task_id,
                        "task_label": meta["label"],
                        "slug": meta["slug"],
                        "total_cases": 0,
                        "eligible_cases": 0,
                        "evaluated_cases": 0,
                        "failed_cases": 0,
                        "coverage": None,
                        "status": "NOT_EXECUTED",
                        "notes": [],
                    }
                )
                continue
            tasks.append(self._headline_row(payload))
            if payload.get("source_metrics_dir"):
                sources.append(str(payload["source_metrics_dir"]))
            elif payload.get("_snapshot"):
                sources.append(str(payload["_snapshot"]))
        timestamps = [row.get("validation_timestamp") for row in tasks if row.get("validation_timestamp")]
        return MedicalReportSummaryOut.model_validate(
            {
                "agent": "medical_report",
                "title": "MEDICAL REPORT AGENT VALIDATION",
                "validation_timestamp": max(timestamps) if timestamps else None,
                "source_metrics_dir": ", ".join(dict.fromkeys(sources)),
                "dataset_cases_total": sum(int(row.get("total_cases") or 0) for row in tasks),
                "tasks": tasks,
                "overall_score": None,
                "overall_score_note": (
                    "No overall Medical Report Agent score is computed. Insurance coding, "
                    "clinical summaries and discharge narratives use different references."
                ),
                "coverage_vs_performance_note": (
                    "Dataset coverage is evaluated_cases / dataset_cases. It is not accuracy."
                ),
            }
        )

    def task(self, task: str) -> MedicalReportTaskDetailOut:
        task_id = resolve_medical_report_task(task)
        reports = self.best_task_reports()
        payload = reports.get(task_id)
        if not payload:
            meta = task_meta(task_id)
            raise FileNotFoundError(
                f"Medical Report validation artifact {meta['slug']}.json is missing."
            )
        return MedicalReportTaskDetailOut.model_validate(payload)

    def case(self, task: str, case_id: str) -> MedicalReportCaseDetailOut:
        detail = self.task(task)
        for row in detail.per_case_results:
            if row.get("case_id") == case_id:
                return MedicalReportCaseDetailOut.model_validate(row)
        raise KeyError(case_id)


medical_report_validation_service = MedicalReportValidationService()
