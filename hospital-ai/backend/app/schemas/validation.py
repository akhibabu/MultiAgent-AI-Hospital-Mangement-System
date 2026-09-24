from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ValidationTask(BaseModel):
    task_id: str
    task: str
    status: str
    cases_evaluated: int = 0
    cases_in_benchmark: int = 0
    metric: Optional[str] = None
    value: Optional[float] = None
    planned_metric: Optional[str] = None
    dataset: Optional[str] = None
    note: Optional[str] = None

class ValidationAgent(BaseModel):
    agent_id: str
    agent: str
    tasks: List[ValidationTask] = Field(default_factory=list)

class ValidationOverview(BaseModel):
    as_of: Optional[str] = None
    source: Optional[str] = None
    disclaimer: str
    agents: List[ValidationAgent]
    operational_checks: Optional[Dict[str, Any]] = None

class ValidationCase(BaseModel):
    case_id: str
    task_id: str
    status: str
    prediction: Any = None
    ground_truth: Any = None
    metrics: Dict[str, Any] = Field(default_factory=dict)

class ValidationCaseList(BaseModel):
    items: List[ValidationCase] = Field(default_factory=list)
    total: int = 0

class ValidationTaskDetail(ValidationTask):
    agent_id: str
    cases: List[ValidationCase] = Field(default_factory=list)
