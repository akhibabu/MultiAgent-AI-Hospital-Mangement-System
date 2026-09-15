"""Response models for Medical Report Agent task-level validation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MedicalReportTaskHeadline(BaseModel):
    model_config = ConfigDict(extra="allow")

    task: str
    task_label: str
    slug: str
    total_cases: int = 0
    eligible_cases: int = 0
    evaluated_cases: int = 0
    failed_cases: int = 0
    coverage: Optional[float] = None
    status: str
    notes: List[str] = Field(default_factory=list)
    display_metrics: List[Dict[str, Any]] = Field(default_factory=list)
    main_metric: Optional[Dict[str, Any]] = None
    human_summary: Optional[str] = None


class MedicalReportSummaryOut(BaseModel):
    agent: str = "medical_report"
    title: str = "MEDICAL REPORT AGENT VALIDATION"
    validation_timestamp: Optional[str] = None
    source_metrics_dir: Optional[str] = None
    dataset_cases_total: int = 0
    tasks: List[MedicalReportTaskHeadline] = Field(default_factory=list)
    overall_score: Optional[float] = None
    overall_score_note: Optional[str] = None
    coverage_vs_performance_note: Optional[str] = None


class MedicalReportTaskDetailOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    agent: str = "medical_report"
    task: str
    task_label: str
    total_cases: int = 0
    eligible_cases: int = 0
    evaluated_cases: int = 0
    failed_cases: int = 0
    coverage: Optional[float] = None
    coverage_note: Optional[str] = None
    metrics: Dict[str, Optional[float]] = Field(default_factory=dict)
    metric_applicability: List[str] = Field(default_factory=list)
    metric_notes: List[str] = Field(default_factory=list)
    status: str
    dataset_mapping: Optional[str] = None
    display_metrics: List[Dict[str, Any]] = Field(default_factory=list)
    main_metric: Optional[Dict[str, Any]] = None
    human_summary: Optional[str] = None
    per_case_results: List[Dict[str, Any]] = Field(default_factory=list)


class MedicalReportCaseDetailOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    case_id: Optional[str] = None
    agent: str = "medical_report"
    task: Optional[str] = None
    prediction: Any = None
    ground_truth: Any = None
    metrics: Dict[str, Optional[float]] = Field(default_factory=dict)
    status: Optional[str] = None
    execution_status: Optional[str] = None
    timestamp: Optional[str] = None
