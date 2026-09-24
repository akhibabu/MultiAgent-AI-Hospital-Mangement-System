from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from app.auth.dependencies import CurrentUser
from app.schemas.validation import (
    ValidationAgent,
    ValidationCase,
    ValidationCaseList,
    ValidationOverview,
    ValidationTaskDetail,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FROZEN_PATH = PROJECT_ROOT / "validation" / "frozen_results.json"
CASE_ROOT = PROJECT_ROOT / "validation" / "results" / "dataset"

router = APIRouter(prefix="/validation", tags=["validation"])
DISCLAIMER = (
    "Dataset-grounded validation compares each benchmark input with the corresponding "
    "ground truth using a task-specific metric. Tasks without defensible ground truth "
    "are not assigned artificial scores. Displayed frozen values preserve prior results "
    "until a new benchmark run replaces them."
)


def _load() -> dict:
    if not FROZEN_PATH.exists():
        return {"agents": []}
    return json.loads(FROZEN_PATH.read_text(encoding="utf-8"))


def _read_json(path: Path) -> Optional[dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _case_path_for_summary(summary_path: Path) -> Optional[Path]:
    # Operational benchmark files use <task_id>.summary.json beside <task_id>.jsonl.
    if summary_path.name.endswith(".summary.json"):
        candidate = summary_path.with_name(
            summary_path.name[: -len(".summary.json")] + ".jsonl"
        )
        return candidate if candidate.exists() else None

    # Dataset-run files use <task_dir>/summary.json beside <task_dir>/cases.jsonl.
    candidate = summary_path.parent / "cases.jsonl"
    return candidate if candidate.exists() else None


def _result_manifest() -> dict[str, tuple[dict[str, Any], Optional[Path]]]:
    """
    Build one canonical result source per task.

    The repository contains historical task runs as well as the current
    operational_agents_v1 benchmark. Prefer the latter (operational *.summary.json)
    so the Validation Center does not merge duplicate case sets or silently
    regress to an older benchmark.
    """
    manifest: dict[str, tuple[dict[str, Any], Optional[Path]]] = {}

    if not CASE_ROOT.exists():
        return manifest

    # First pass: current operational benchmark results.
    for summary_path in sorted(CASE_ROOT.rglob("*.summary.json")):
        payload = _read_json(summary_path)
        if not payload or not payload.get("task_id"):
            continue
        task_id = str(payload["task_id"])
        manifest[task_id] = (payload, _case_path_for_summary(summary_path))

    # Second pass: legacy/task-run summaries only when no preferred result
    # exists for that task.
    for summary_path in sorted(CASE_ROOT.rglob("summary.json")):
        payload = _read_json(summary_path)
        if not payload or not payload.get("task_id"):
            continue
        task_id = str(payload["task_id"])
        if task_id not in manifest:
            manifest[task_id] = (payload, _case_path_for_summary(summary_path))

    return manifest


def _dataset_overrides() -> dict[str, dict[str, Any]]:
    return {
        task_id: payload
        for task_id, (payload, _case_path) in _result_manifest().items()
    }


def _agents() -> list[ValidationAgent]:
    overrides = _dataset_overrides()
    agents = []

    for raw_agent in _load().get("agents", []):
        agent = ValidationAgent.model_validate(raw_agent)
        updated_tasks = []

        for task in agent.tasks:
            override = overrides.get(task.task_id)
            if not override:
                updated_tasks.append(task)
                continue

            metric_text = task.metric or task.planned_metric
            value = task.value
            note = task.note

            headline_metric = override.get("headline_metric")
            headline_value = override.get("headline_value")
            accuracy = override.get("accuracy")
            precision = override.get("precision")
            recall = override.get("recall")
            macro_f1 = override.get("macro_f1")
            f1_score = override.get("f1_score")

            if headline_metric is not None and headline_value is not None:
                metric_text = str(headline_metric)
                value = float(headline_value) * 100.0
                secondary = []

                if accuracy is not None:
                    secondary.append(f"Accuracy: {float(accuracy) * 100.0:.1f}%")
                if precision is not None:
                    secondary.append(f"Precision: {float(precision) * 100.0:.1f}%")
                if recall is not None:
                    secondary.append(f"Recall: {float(recall) * 100.0:.1f}%")
                if macro_f1 is not None:
                    secondary.append(f"Macro F1: {float(macro_f1) * 100.0:.1f}%")
                if f1_score is not None and macro_f1 is None:
                    secondary.append(f"F1: {float(f1_score) * 100.0:.1f}%")

                note = "; ".join(secondary) or note

            elif accuracy is not None and macro_f1 is not None:
                metric_text = "Accuracy / Macro F1"
                value = float(accuracy) * 100.0
                note = (
                    f"Accuracy: {float(accuracy) * 100.0:.1f}%; "
                    f"Macro F1: {float(macro_f1) * 100.0:.1f}%."
                )

            elif accuracy is not None and f1_score is not None:
                metric_text = "Accuracy / F1"
                value = float(accuracy) * 100.0
                note = (
                    f"Accuracy: {float(accuracy) * 100.0:.1f}%; "
                    f"F1: {float(f1_score) * 100.0:.1f}%."
                )

            status_override = override.get("status")
            cases_evaluated = int(override.get("cases_evaluated") or 0)
            cases_in_benchmark = int(
                override.get("cases_in_benchmark")
                or override.get("cases_evaluated")
                or 0
            )

            updated_tasks.append(
                task.model_copy(
                    update={
                        "status": status_override or "VALIDATED",
                        "cases_evaluated": cases_evaluated,
                        "cases_in_benchmark": cases_in_benchmark,
                        "metric": metric_text,
                        "value": value,
                        "dataset": override.get("dataset") or task.dataset,
                        "note": note,
                    }
                )
            )

        agents.append(agent.model_copy(update={"tasks": updated_tasks}))

    return agents


@router.get("/overview", response_model=ValidationOverview)
def overview(_current_user: CurrentUser) -> ValidationOverview:
    payload = _load()
    return ValidationOverview(
        as_of=payload.get("as_of"),
        source=payload.get("source"),
        disclaimer=DISCLAIMER,
        agents=_agents(),
        operational_checks={
            "type": "supplemental_engineering_verification",
            "note": "Operational checks are kept separate from dataset accuracy/F1 metrics.",
        },
    )


@router.get("/agents", response_model=list[ValidationAgent])
def agents(_current_user: CurrentUser) -> list[ValidationAgent]:
    return _agents()


@router.get("/agents/{agent_id}", response_model=ValidationAgent)
def agent(_current_user: CurrentUser, agent_id: str) -> ValidationAgent:
    for item in _agents():
        if item.agent_id == agent_id:
            return item
    raise HTTPException(status_code=404, detail="Validation agent not found")


@router.get("/tasks/{task_id}", response_model=ValidationTaskDetail)
def task(_current_user: CurrentUser, task_id: str) -> ValidationTaskDetail:
    for agent_item in _agents():
        for item in agent_item.tasks:
            if item.task_id == task_id:
                return ValidationTaskDetail(
                    **item.model_dump(),
                    agent_id=agent_item.agent_id,
                    cases=_load_cases(task_id),
                )
    raise HTTPException(status_code=404, detail="Validation task not found")


@router.get("/cases", response_model=ValidationCaseList)
def cases(
    _current_user: CurrentUser,
    task: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
) -> ValidationCaseList:
    items: list[ValidationCase] = []
    manifest = _result_manifest()

    if task:
        selected = {task: manifest[task]} if task in manifest else {}
    else:
        selected = manifest

    for _task_id, (_payload, case_path) in sorted(selected.items()):
        if case_path is None:
            continue

        try:
            lines = case_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue

        for line in lines:
            if not line.strip():
                continue

            try:
                raw = json.loads(line)
                case = ValidationCase.model_validate(raw)
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

            if status and case.status != status:
                continue
            items.append(case)

    return ValidationCaseList(items=items, total=len(items))


def _load_cases(task_id: str) -> list[ValidationCase]:
    manifest = _result_manifest()
    source = manifest.get(task_id)
    if source is None:
        return []

    _payload, case_path = source
    if case_path is None:
        return []

    result: list[ValidationCase] = []

    try:
        lines = case_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return result

    for line in lines:
        if not line.strip():
            continue

        try:
            raw = json.loads(line)
            if raw.get("task_id") != task_id:
                continue
            result.append(ValidationCase.model_validate(raw))
        except (json.JSONDecodeError, ValueError, TypeError):
            continue

    return result
