"""
Validation Center API.

Read-only endpoints over stored evaluation artifacts. Every handler requires
an authenticated user; nothing here writes to the validation tree or to
production tables.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.auth.dependencies import CurrentUser
from app.schemas.execution_validation import ExecutionValidationOut
from app.schemas.validation import (
    AgentDetail,
    AgentSummary,
    CaseDetail,
    CaseListResponse,
    CompareResponse,
    DatasetCoverageResponse,
    ErrorAnalysisResponse,
    EvidenceCard,
    HardeningBundleResponse,
    HumanReviewStatus,
    LimitationsResponse,
    MetricDefinitionsResponse,
    MethodologyResponse,
    PresentationResponse,
    RunDetail,
    RunListResponse,
    SafetyResponse,
    TaskDetail,
    ValidationHealthResponse,
    ValidationOverview,
)
from app.schemas.diagnosis_validation import (
    DiagnosisCaseDetailOut,
    DiagnosisSummaryOut,
    DiagnosisTaskDetailOut,
)
from app.schemas.research_validation import (
    ResearchCaseDetailOut,
    ResearchSummaryOut,
    ResearchTaskDetailOut,
)
from app.schemas.intake_validation import (
    IntakeCaseDetailOut,
    IntakeSummaryOut,
    IntakeTaskDetailOut,
)
from app.schemas.prescription_validation import (
    PrescriptionCaseDetailOut,
    PrescriptionSummaryOut,
    PrescriptionTaskDetailOut,
)
from app.schemas.medical_report_validation import (
    MedicalReportCaseDetailOut,
    MedicalReportSummaryOut,
    MedicalReportTaskDetailOut,
)
from app.services.diagnosis_validation_service import diagnosis_validation_service
from app.services.research_validation_service import research_validation_service
from app.services.prescription_validation_service import prescription_validation_service
from app.services.medical_report_validation_service import medical_report_validation_service
from app.services.execution_validation_service import execution_validation_service
from app.services.intake_validation_service import intake_validation_service
from app.services.validation_service import validation_service

router = APIRouter(prefix="/validation", tags=["validation"])


def _missing(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc) or "Not found")


@router.get("/overview", response_model=ValidationOverview)
def get_overview(
    _current_user: CurrentUser,
    run_id: Optional[str] = Query(default=None),
) -> ValidationOverview:
    try:
        return validation_service.overview(run_id)
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/runs", response_model=RunListResponse)
def list_runs(_current_user: CurrentUser) -> RunListResponse:
    return validation_service.list_runs()


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run(_current_user: CurrentUser, run_id: str) -> RunDetail:
    try:
        return validation_service.get_run(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/agents", response_model=list[AgentSummary])
def list_agents(
    _current_user: CurrentUser,
    run_id: Optional[str] = Query(default=None),
) -> list[AgentSummary]:
    try:
        return validation_service.list_agents(run_id)
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/agents/{agent_id}", response_model=AgentDetail)
def get_agent(
    _current_user: CurrentUser,
    agent_id: str,
    run_id: Optional[str] = Query(default=None),
) -> AgentDetail:
    try:
        return validation_service.get_agent(agent_id, run_id)
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def get_task(
    _current_user: CurrentUser,
    task_id: str,
    run_id: Optional[str] = Query(default=None),
) -> TaskDetail:
    try:
        return validation_service.get_task(task_id, run_id)
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/datasets", response_model=DatasetCoverageResponse)
def list_datasets(
    _current_user: CurrentUser,
    run_id: Optional[str] = Query(default=None),
) -> DatasetCoverageResponse:
    try:
        return validation_service.datasets(run_id)
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/cases", response_model=CaseListResponse)
def list_cases(
    _current_user: CurrentUser,
    run_id: Optional[str] = Query(default=None),
    agent: Optional[str] = Query(default=None),
    task: Optional[str] = Query(default=None),
    dataset: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    evaluation_type: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None, description="Search case ID, agent, task, dataset."),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> CaseListResponse:
    try:
        return validation_service.list_cases(
            run_id=run_id,
            agent=agent,
            task=task,
            dataset=dataset,
            status=status,
            evaluation_type=evaluation_type,
            q=q,
            page=page,
            page_size=page_size,
        )
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/cases/{case_id}", response_model=CaseDetail)
def get_case(
    _current_user: CurrentUser,
    case_id: str,
    run_id: Optional[str] = Query(default=None),
) -> CaseDetail:
    try:
        return validation_service.get_case(case_id, run_id)
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/errors", response_model=ErrorAnalysisResponse)
def get_errors(
    _current_user: CurrentUser,
    run_id: Optional[str] = Query(default=None),
    agent: Optional[str] = Query(default=None),
    task: Optional[str] = Query(default=None),
    error_type: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> ErrorAnalysisResponse:
    try:
        return validation_service.errors(
            run_id,
            agent=agent,
            task=task,
            error_type=error_type,
            severity=severity,
            page=page,
            page_size=page_size,
        )
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/safety", response_model=SafetyResponse)
def get_safety(
    _current_user: CurrentUser,
    run_id: Optional[str] = Query(default=None),
) -> SafetyResponse:
    try:
        return validation_service.safety(run_id)
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/limitations", response_model=LimitationsResponse)
def get_limitations(
    _current_user: CurrentUser,
    run_id: Optional[str] = Query(default=None),
) -> LimitationsResponse:
    try:
        return validation_service.limitations(run_id)
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/presentation", response_model=PresentationResponse)
def get_presentation(
    _current_user: CurrentUser,
    run_id: Optional[str] = Query(default=None),
) -> PresentationResponse:
    try:
        return validation_service.presentation(run_id)
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/human-review", response_model=HumanReviewStatus)
def get_human_review(
    _current_user: CurrentUser,
    run_id: Optional[str] = Query(default=None),
) -> HumanReviewStatus:
    try:
        return validation_service.human_review(run_id)
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/health", response_model=ValidationHealthResponse)
def get_validation_health() -> ValidationHealthResponse:
    """Subsystem liveness. No secrets, no patient data."""
    return validation_service.health()


@router.get("/metrics/definitions", response_model=MetricDefinitionsResponse)
def get_metric_definitions(_current_user: CurrentUser) -> MetricDefinitionsResponse:
    return validation_service.metric_definitions()


@router.get("/evidence", response_model=list[EvidenceCard])
def get_evidence(
    _current_user: CurrentUser,
    run_id: Optional[str] = Query(default=None),
):
    try:
        return validation_service.evidence(run_id)
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/methodology/{task_id}", response_model=MethodologyResponse)
def get_methodology(
    _current_user: CurrentUser,
    task_id: str,
    run_id: Optional[str] = Query(default=None),
) -> MethodologyResponse:
    try:
        return validation_service.methodology(task_id, run_id)
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/compare", response_model=CompareResponse)
def get_compare(
    _current_user: CurrentUser,
    run_a: str = Query(...),
    run_b: str = Query(...),
) -> CompareResponse:
    try:
        return validation_service.compare(run_a, run_b)
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/hardening/{run_id}", response_model=HardeningBundleResponse)
def get_hardening(
    _current_user: CurrentUser,
    run_id: str,
) -> HardeningBundleResponse:
    try:
        return validation_service.hardening_bundle(run_id)
    except KeyError as exc:
        raise _missing(exc) from exc


@router.get("/intake/summary", response_model=IntakeSummaryOut)
def get_intake_summary(_current_user: CurrentUser) -> IntakeSummaryOut:
    return intake_validation_service.summary()


@router.get("/intake/{task}", response_model=IntakeTaskDetailOut)
def get_intake_task(_current_user: CurrentUser, task: str) -> IntakeTaskDetailOut:
    try:
        return intake_validation_service.task(task)
    except FileNotFoundError as exc:
        raise _missing(exc) from exc


@router.get("/intake/{task}/{case_id}", response_model=IntakeCaseDetailOut)
def get_intake_case(
    _current_user: CurrentUser,
    task: str,
    case_id: str,
) -> IntakeCaseDetailOut:
    try:
        return intake_validation_service.case(task, case_id)
    except (FileNotFoundError, KeyError) as exc:
        raise _missing(exc) from exc


@router.get("/diagnosis/summary", response_model=DiagnosisSummaryOut)
def get_diagnosis_summary(_current_user: CurrentUser) -> DiagnosisSummaryOut:
    return diagnosis_validation_service.summary()


@router.get("/diagnosis/{task}", response_model=DiagnosisTaskDetailOut)
def get_diagnosis_task(_current_user: CurrentUser, task: str) -> DiagnosisTaskDetailOut:
    try:
        return diagnosis_validation_service.task(task)
    except FileNotFoundError as exc:
        raise _missing(exc) from exc


@router.get("/diagnosis/{task}/{case_id}", response_model=DiagnosisCaseDetailOut)
def get_diagnosis_case(
    _current_user: CurrentUser,
    task: str,
    case_id: str,
) -> DiagnosisCaseDetailOut:
    try:
        return diagnosis_validation_service.case(task, case_id)
    except (FileNotFoundError, KeyError) as exc:
        raise _missing(exc) from exc


@router.get("/research/summary", response_model=ResearchSummaryOut)
def get_research_summary(_current_user: CurrentUser) -> ResearchSummaryOut:
    return research_validation_service.summary()


@router.get("/research/{task}", response_model=ResearchTaskDetailOut)
def get_research_task(_current_user: CurrentUser, task: str) -> ResearchTaskDetailOut:
    try:
        return research_validation_service.task(task)
    except FileNotFoundError as exc:
        raise _missing(exc) from exc


@router.get("/research/{task}/{case_id}", response_model=ResearchCaseDetailOut)
def get_research_case(
    _current_user: CurrentUser,
    task: str,
    case_id: str,
) -> ResearchCaseDetailOut:
    try:
        return research_validation_service.case(task, case_id)
    except (FileNotFoundError, KeyError) as exc:
        raise _missing(exc) from exc


@router.get("/prescription/summary", response_model=PrescriptionSummaryOut)
def get_prescription_summary(_current_user: CurrentUser) -> PrescriptionSummaryOut:
    return prescription_validation_service.summary()


@router.get("/prescription/{task}", response_model=PrescriptionTaskDetailOut)
def get_prescription_task(_current_user: CurrentUser, task: str) -> PrescriptionTaskDetailOut:
    try:
        return prescription_validation_service.task(task)
    except FileNotFoundError as exc:
        raise _missing(exc) from exc


@router.get("/prescription/{task}/{case_id}", response_model=PrescriptionCaseDetailOut)
def get_prescription_case(
    _current_user: CurrentUser,
    task: str,
    case_id: str,
) -> PrescriptionCaseDetailOut:
    try:
        return prescription_validation_service.case(task, case_id)
    except (FileNotFoundError, KeyError) as exc:
        raise _missing(exc) from exc


@router.get("/medical-report/summary", response_model=MedicalReportSummaryOut)
def get_medical_report_summary(_current_user: CurrentUser) -> MedicalReportSummaryOut:
    return medical_report_validation_service.summary()


@router.get("/medical-report/{task}", response_model=MedicalReportTaskDetailOut)
def get_medical_report_task(_current_user: CurrentUser, task: str) -> MedicalReportTaskDetailOut:
    try:
        return medical_report_validation_service.task(task)
    except FileNotFoundError as exc:
        raise _missing(exc) from exc


@router.get("/medical-report/{task}/{case_id}", response_model=MedicalReportCaseDetailOut)
def get_medical_report_case(
    _current_user: CurrentUser,
    task: str,
    case_id: str,
) -> MedicalReportCaseDetailOut:
    try:
        return medical_report_validation_service.case(task, case_id)
    except (FileNotFoundError, KeyError) as exc:
        raise _missing(exc) from exc


@router.get(
    "/executions/{task_id}/{execution_id}",
    response_model=ExecutionValidationOut,
    summary="Per-execution validation result for a hospital task run",
)
def get_execution_validation(
    _current_user: CurrentUser,
    task_id: str,
    execution_id: str,
) -> ExecutionValidationOut:
    record = execution_validation_service.get(task_id, execution_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation result is not available for this execution.",
        )
    return execution_validation_service.to_schema(record)


@router.get(
    "/{task_id}/{case_id}",
    response_model=ExecutionValidationOut,
    summary="Latest stored validation result for a dataset case",
)
def get_validation_by_case(
    _current_user: CurrentUser,
    task_id: str,
    case_id: str,
) -> ExecutionValidationOut:
    record = execution_validation_service.get_by_case(task_id, case_id)
    if not record:
        record = execution_validation_service.get(task_id, case_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation result is not available for this case.",
        )
    return execution_validation_service.to_schema(record)
