from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.auth.dependencies import CurrentUser
from app.schemas.validation import (
    ValidationAgent, ValidationCase, ValidationCaseList, ValidationOverview,
    ValidationTaskDetail,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
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

def _agents() -> list[ValidationAgent]:
    return [ValidationAgent.model_validate(x) for x in _load().get("agents", [])]

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
                    **item.model_dump(), agent_id=agent_item.agent_id, cases=_load_cases(task_id)
                )
    raise HTTPException(status_code=404, detail="Validation task not found")

@router.get("/cases", response_model=ValidationCaseList)
def cases(
    _current_user: CurrentUser,
    task: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
) -> ValidationCaseList:
    items: list[ValidationCase] = []
    if CASE_ROOT.exists():
        for path in sorted(CASE_ROOT.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                raw = json.loads(line)
                if task and raw.get("task_id") != task:
                    continue
                if status and raw.get("status") != status:
                    continue
                items.append(ValidationCase.model_validate(raw))
    return ValidationCaseList(items=items, total=len(items))

def _load_cases(task_id: str) -> list[ValidationCase]:
    result: list[ValidationCase] = []
    if not CASE_ROOT.exists():
        return result
    for path in sorted(CASE_ROOT.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            if raw.get("task_id") == task_id:
                result.append(ValidationCase.model_validate(raw))
    return result