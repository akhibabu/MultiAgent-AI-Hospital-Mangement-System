#!/usr/bin/env python3
"""Medical Report validation runner — insurance is quantitative; summaries are human review."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PIPELINE = Path(__file__).resolve().parent
PROJECT = PIPELINE.parents[1]
VALIDATORS = PROJECT / "validation" / "validators"
CASES_ROOT = PROJECT / "validation" / "ground_truth" / "cases" / "medical_report"
RAW_ROOT = PROJECT / "validation" / "results" / "raw"
METRICS_ROOT = PROJECT / "validation" / "results" / "metrics"

for path in (str(PIPELINE), str(VALIDATORS), str(PROJECT / "backend")):
    if path not in sys.path:
        sys.path.insert(0, path)

from adapters.base import ExecutionRuntime  # noqa: E402
from adapters.medical_report_adapter import MedicalReportAdapter  # noqa: E402
from backend_bridge import (  # noqa: E402
    ContextRegistry,
    bootstrap,
    install_supabase_guard,
    seed_orchestrator,
)

VALIDATION_OVERLAY = PROJECT / "validation" / ".env.validation"
from aggregate_metrics import aggregate  # noqa: E402
from base_validator import CaseContext  # noqa: E402
from case_loader import load_case  # noqa: E402
from ground_truth_loader import GroundTruthLoader  # noqa: E402
from medical_report_catalog import (  # noqa: E402
    MEDICAL_REPORT_TASK_IDS,
    resolve_medical_report_tasks,
)
from validator_registry import get_validator  # noqa: E402

LLM_TASKS = frozenset(
    {
        "medical_report_clinical_summary",
        "medical_report_discharge_summary",
        "medical_report_insurance_documentation",
    }
)


def _iter_case_paths(task_ids: list[str], max_cases: int | None) -> list[Path]:
    paths: list[Path] = []
    for task_id in task_ids:
        task_paths = sorted(CASES_ROOT.glob(f"VC-{task_id}-*.json"))
        if max_cases is not None:
            task_paths = task_paths[: max_cases]
        paths.extend(task_paths)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Medical Report Agent validation")
    parser.add_argument("--run-id", help="Run id (default: VAL-RUN-YYYYMMDD-035)")
    parser.add_argument("--task", default="ALL", help="Task id or ALL")
    parser.add_argument("--max-cases", type=int, help="Cap cases per task")
    parser.add_argument(
        "--insurance-only",
        action="store_true",
        help="Run only medical_report_insurance_documentation",
    )
    args = parser.parse_args()

    bootstrap(env_overlay=VALIDATION_OVERLAY if VALIDATION_OVERLAY.is_file() else None)
    context_registry = ContextRegistry()
    seed_orchestrator(context_registry)
    install_supabase_guard()

    task_ids = resolve_medical_report_tasks([args.task])
    if args.insurance_only:
        task_ids = ["medical_report_insurance_documentation"]
    else:
        task_ids = [task_id for task_id in task_ids if task_id in LLM_TASKS]

    run_id = args.run_id or f"VAL-RUN-{datetime.now(timezone.utc).strftime('%Y%m%d')}-035"
    raw_dir = RAW_ROOT / run_id
    metrics_dir = METRICS_ROOT / run_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)

    adapter = MedicalReportAdapter()
    runtime = ExecutionRuntime(context_registry=context_registry)
    gt_loader = GroundTruthLoader()
    case_paths = _iter_case_paths(task_ids, args.max_cases)
    results_path = raw_dir / "results.jsonl"
    case_results: list[dict] = []

    with results_path.open("w", encoding="utf-8", newline="\n") as handle:
        for path in case_paths:
            sealed = load_case(path)
            loaded = gt_loader.load(sealed.validation_case_id)
            started = datetime.now(timezone.utc)
            llm_calls = 6 if sealed.task_id in LLM_TASKS else 0
            try:
                agent_input = adapter.build_input(sealed, runtime)
                output = adapter.execute(sealed, agent_input, runtime)
                status = "SUCCESS"
                error = None
            except Exception as exc:  # noqa: BLE001
                output = None
                status = "FAILED"
                error = str(exc)

            finished = datetime.now(timezone.utc)
            row = {
                "validation_case_id": sealed.validation_case_id,
                "task_id": sealed.task_id,
                "task": sealed.task,
                "agent": sealed.agent,
                "execution": {
                    "status": status,
                    "duration_ms": int((finished - started).total_seconds() * 1000),
                    "llm_calls": llm_calls if status == "SUCCESS" else 0,
                    "error": error,
                },
                "agent_output": output,
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

            validator = get_validator(sealed.task_id)
            context = CaseContext(
                case_id=sealed.validation_case_id,
                task_id=sealed.task_id,
                task=sealed.task,
                agent=sealed.agent,
                evaluation_type=sealed.evaluation_type,
                ground_truth_status=sealed.ground_truth_status,
            )
            if status != "SUCCESS":
                outcome_status = "EXECUTION_FAILED"
                evaluation = {"status": outcome_status, "reason": error}
            else:
                outcome = validator.validate(output, loaded.ground_truth, context)
                outcome_status = outcome.status
                evaluation = {
                    "status": outcome.status,
                    "evaluation_type": outcome.evaluation_type,
                    "metrics": outcome.metrics,
                    "reason": outcome.reason,
                    "details": outcome.details,
                    "counts": outcome.counts,
                    "validator": validator.__class__.__name__,
                }

            case_results.append(
                {
                    "case_id": sealed.validation_case_id,
                    "task_id": sealed.task_id,
                    "task": sealed.task_id,
                    "agent": "medical_report",
                    "status": outcome_status,
                    "execution": {
                        "status": status,
                        "duration_ms": int((finished - started).total_seconds() * 1000),
                        "llm_calls": llm_calls if status == "SUCCESS" else 0,
                    },
                    "evaluation": evaluation,
                    "reproducibility": {"evaluated_at": finished.isoformat()},
                }
            )

    (metrics_dir / "case_results.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in case_results) + "\n",
        encoding="utf-8",
    )
    task_metrics = aggregate(case_results)
    (metrics_dir / "task_metrics.json").write_text(
        json.dumps(task_metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    from write_medical_report_reports import write_medical_report_reports  # noqa: E402

    report_dir = write_medical_report_reports(metrics_dir)
    print(f"Run {run_id}: {len(case_paths)} cases across {', '.join(task_ids)}")
    print(f"Metrics: {metrics_dir}")
    print(f"Reports: {report_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
