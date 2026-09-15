"""
Read-only Validation Center service.

Every number that leaves this module was already computed by the evaluation
engine and stored under `validation/results/`. This layer reshapes those
artifacts for the dashboard: it does not recompute precision, recall, F1, or
any other quality metric, and it never writes to disk.

Two jobs sit on top of that constraint.

The dashboard needs the whole project, not only the latest run. A smoke test
that scored one task would otherwise look like a system with one task. The
task registry supplies coverage for everything that was not executed; the run
supplies scores only where they exist.

Patient-derived text stays inside the validation tree. List endpoints return
identifiers and status. Case detail returns a described input, a truncated
output, and a redacted reference — enough to show that a real comparison
happened, not enough to browse a patient record.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.config.settings import get_settings
from app.repositories.validation_repository import (
    ValidationArtifactRepository,
    get_validation_repository,
)
from app.schemas.validation import (
    AgentDetail,
    AgentSummary,
    CaseDetail,
    CaseInputDescriptor,
    CaseListResponse,
    CaseSummary,
    CoverageCell,
    DatasetCoverageResponse,
    DatasetSummary,
    ErrorAnalysisResponse,
    ErrorGroup,
    FlowStage,
    HumanReviewStatus,
    LimitationItem,
    LimitationsResponse,
    MetricGroup,
    OverviewCounters,
    PresentationResponse,
    PresentationSlide,
    ProviderUsage,
    RunDetail,
    RunListResponse,
    RunSummary,
    SafetyResponse,
    SafetyRuleResult,
    TaskDetail,
    TaskHeadline,
    TaskSummary,
    ValidationOverview,
    ValidationStatusCounts,
    CompareResponse,
    EvidenceCard,
    HardeningBundleResponse,
    MetricDefinition,
    MetricDefinitionsResponse,
    MethodologyResponse,
    StructuredLimitation,
    ValidationHealthResponse,
)
DISCLAIMER = (
    "These results describe how the system behaved on this benchmark, under this "
    "configuration, on this date. They are not evidence of medical accuracy, "
    "clinical safety, or fitness for use in patient care."
)

AGENT_CATALOG: List[Dict[str, str]] = [
    {
        "agent_id": "intake",
        "agent": "Intake Agent",
        "description": (
            "Evaluates patient intake, information extraction and structured "
            "clinical understanding."
        ),
    },
    {
        "agent_id": "diagnosis",
        "agent": "Diagnosis Agent",
        "description": (
            "Evaluates differential diagnosis, severity assessment and "
            "clinical decision support against encounter-level references."
        ),
    },
    {
        "agent_id": "research",
        "agent": "Research Agent",
        "description": (
            "Evaluates literature retrieval, evidence ranking and research "
            "recommendations. Most tasks currently lack a labelled benchmark."
        ),
    },
    {
        "agent_id": "prescription",
        "agent": "Prescription Agent",
        "description": (
            "Evaluates medication selection, prescription structure and "
            "safety-related checks against recorded orders."
        ),
    },
    {
        "agent_id": "medical_report",
        "agent": "Medical Report Agent",
        "description": (
            "Evaluates clinical documentation — summaries, discharge notes "
            "and billing codes — against encounter records."
        ),
    },
]

_AGENT_BY_ID = {entry["agent_id"]: entry for entry in AGENT_CATALOG}
_AGENT_BY_NAME = {entry["agent"].lower(): entry for entry in AGENT_CATALOG}

_IDENTIFIER_KEYS = frozenset(
    {
        "subject_id",
        "hadm_id",
        "stay_id",
        "patient_id",
        "icustay_id",
        "ed_stay_id",
    }
)
_DROP_OUTPUT_KEYS = frozenset(
    {
        "ai_debug",
        "raw_response",
        "prompt",
        "system_prompt",
        "messages",
        "patient_context",
    }
)

_METRIC_CATEGORIES = (
    (
        "Extraction",
        "ENTITY_MATCH",
        "Entity and span agreement against annotated mentions.",
    ),
    (
        "Classification",
        "CLASSIFICATION",
        "Label agreement against a closed reference set.",
    ),
    (
        "Set comparison",
        "SET_COMPARISON",
        "Unordered set agreement (diagnoses, medications, codes).",
    ),
    (
        "Ranking",
        "RANKING",
        "Ordering quality against labelled relevance or documented positives.",
    ),
    (
        "Structured fields",
        "STRUCTURED_FIELD_MATCH",
        "Field-by-field agreement on registration or prescription structure.",
    ),
    (
        "Relations",
        "RELATION_MATCH",
        "Typed relationship agreement, scored separately from entities.",
    ),
    (
        "Safety",
        "SAFETY_RULE",
        "Safety-rule checks. Reported separately from quality metrics.",
    ),
)

_EXCERPT_LIMIT = 400
_LIST_CAP = 40
_STRING_CAP = 400


def resolve_agent_id(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    key = value.strip().lower().replace(" ", "_").replace("-", "_")
    if key in _AGENT_BY_ID:
        return key
    if key.endswith("_agent"):
        key = key[: -len("_agent")]
        if key in _AGENT_BY_ID:
            return key
    entry = _AGENT_BY_NAME.get(value.strip().lower())
    return entry["agent_id"] if entry else None


def resolve_agent_name(value: Optional[str]) -> str:
    agent_id = resolve_agent_id(value)
    if agent_id:
        return _AGENT_BY_ID[agent_id]["agent"]
    return value or "Unknown"


class ValidationService:
    """Shapes stored validation artifacts for the dashboard."""

    def __init__(self, repository: Optional[ValidationArtifactRepository] = None) -> None:
        self._repo = repository or get_validation_repository()
        self._intake_overlay_cache: Optional[Tuple[float, Dict[str, Any]]] = None
        self._diagnosis_overlay_cache: Optional[Tuple[float, Dict[str, Any]]] = None
        self._research_overlay_cache: Optional[Tuple[float, Dict[str, Any]]] = None
        self._prescription_overlay_cache: Optional[Tuple[float, Dict[str, Any]]] = None
        self._medical_report_overlay_cache: Optional[Tuple[float, Dict[str, Any]]] = None

    # ------------------------------------------------------------------
    # overview
    # ------------------------------------------------------------------

    def overview(self, run_id: Optional[str] = None) -> ValidationOverview:
        run_id = self._resolve_run(run_id)
        registry = self._registry()
        run_tasks = self._run_tasks(run_id)
        case_counts = self._case_counts_by_task()
        agents = [
            self._agent_summary(entry, registry, run_tasks, case_counts, run_id)
            for entry in AGENT_CATALOG
        ]
        coverage = [
            self._coverage_cell(task, run_tasks, case_counts)
            for task in registry
            if task.get("task_id") not in _HIDDEN_INTAKE_TASKS
        ]
        status_counts = self._status_counts(coverage)
        execution = self._execution(run_id)
        evaluated = sum(
            (run_tasks.get(task["task_id"]) or {}).get("sample", {}).get("evaluated", 0)
            for task in registry
        )
        if run_id:
            metrics = self._repo.metrics(run_id) or {}
            evaluated = (metrics.get("overall") or {}).get("cases_evaluated", evaluated)

        notice = None
        if not run_id:
            notice = (
                "No evaluated validation run is on disk yet. Coverage below comes "
                "from the task registry; quality metrics will appear after an "
                "evaluation is stored."
            )
        elif status_counts.validated == 0:
            notice = (
                f"Run {run_id} produced no scored tasks. Execution statistics "
                "are shown; quality metrics are not."
            )
        elif status_counts.validated == 1:
            notice = (
                f"Run {run_id} scored one task. Point estimates from a handful of "
                "cases are indicative of pipeline behaviour, not of system performance."
            )

        return ValidationOverview(
            run_id=run_id,
            evaluated_at=self._evaluated_at(run_id),
            has_results=bool(run_id),
            counters=OverviewCounters(
                total_agents=len(AGENT_CATALOG),
                total_tasks=len(registry),
                validated_tasks=status_counts.validated,
                not_validatable_tasks=status_counts.not_validatable,
                human_review_tasks=status_counts.pending_human_review,
                cases_evaluated=evaluated,
                cases_in_benchmark=sum(case_counts.values()),
                execution_success_rate=execution.get("success_rate"),
                tasks_exercised_in_latest_run=sum(
                    1 for task in registry if task["task_id"] in run_tasks
                ),
            ),
            status_counts=status_counts,
            agents=agents,
            coverage=coverage,
            metric_groups=self._metric_groups(registry, run_tasks),
            flow=self._flow(registry, case_counts, evaluated, run_id),
            provider_summary=self._provider_block(run_id),
            notice=notice,
        )

    # ------------------------------------------------------------------
    # agents
    # ------------------------------------------------------------------

    def list_agents(self, run_id: Optional[str] = None) -> List[AgentSummary]:
        overview = self.overview(run_id)
        return overview.agents

    def get_agent(self, agent_id: str, run_id: Optional[str] = None) -> AgentDetail:
        resolved = resolve_agent_id(agent_id)
        if not resolved or resolved not in _AGENT_BY_ID:
            raise KeyError(agent_id)
        run_id = self._resolve_run(run_id)
        registry = self._registry()
        run_tasks = self._run_tasks(run_id)
        case_counts = self._case_counts_by_task()
        entry = _AGENT_BY_ID[resolved]
        summary = self._agent_summary(entry, registry, run_tasks, case_counts, run_id)
        tasks = [
            self._task_summary(task, run_tasks, case_counts)
            for task in registry
            if resolve_agent_id(task.get("agent")) == resolved
            and task.get("task_id") not in _HIDDEN_INTAKE_TASKS
        ]
        return AgentDetail(summary=summary, tasks=tasks, run_id=run_id)

    # ------------------------------------------------------------------
    # tasks
    # ------------------------------------------------------------------

    def get_task(self, task_id: str, run_id: Optional[str] = None) -> TaskDetail:
        run_id = self._resolve_run(run_id)
        registry_task = self._registry_task(task_id)
        if registry_task is None:
            raise KeyError(task_id)
        run_tasks = self._run_tasks(run_id)
        case_counts = self._case_counts_by_task()
        summary = self._task_summary(registry_task, run_tasks, case_counts)
        run_entry = run_tasks.get(task_id) or {}
        quality = run_entry.get("quality")
        errors = self._error_groups_for_task(run_id, task_id)
        execution = self._task_execution(run_id, task_id)
        human_review = None
        if summary.validation_state == "PENDING_HUMAN_REVIEW":
            human_review = {
                "status": "AWAITING_REVIEW",
                "note": "Automatic evaluation is insufficient for this task.",
                "criteria": [
                    "factual_correctness",
                    "completeness",
                    "clinical_relevance",
                    "evidence_grounding",
                    "safety",
                    "clarity",
                    "unsupported_claims",
                ],
            }
        return TaskDetail(
            task_id=summary.task_id,
            task=summary.task,
            agent=summary.agent,
            registry_status=summary.registry_status,
            evaluation_type=summary.evaluation_type,
            secondary_evaluation_types=list(
                registry_task.get("secondary_evaluation_types") or []
            ),
            validation_state=summary.validation_state,
            ground_truth_status=registry_task.get("ground_truth_status"),
            ground_truth_required=bool(registry_task.get("ground_truth_required", True)),
            eligibility_reason=registry_task.get("eligibility_reason"),
            source_datasets=list(registry_task.get("source_datasets") or []),
            recommended_metrics=list(registry_task.get("recommended_metrics") or []),
            required_input=list(registry_task.get("required_input") or []),
            expected_output=list(registry_task.get("expected_output") or []),
            cases_in_benchmark=summary.cases_in_benchmark,
            sample=run_entry.get("sample") or {},
            metrics=quality,
            confidence_intervals=(quality or {}).get("confidence_intervals")
            if isinstance(quality, dict)
            else None,
            safety=run_entry.get("safety"),
            error_breakdown=errors,
            execution=execution,
            providers=self._providers(run_id),
            human_review=human_review,
            warnings=list(run_entry.get("warnings") or []),
            run_id=run_id,
            headline=summary.headline,
        )

    # ------------------------------------------------------------------
    # runs
    # ------------------------------------------------------------------

    def list_runs(self) -> RunListResponse:
        evaluated = self._repo.evaluated_run_ids()
        executed = self._repo.executed_run_ids()
        items = [self._run_summary(run_id) for run_id in evaluated]
        pending = [run_id for run_id in executed if run_id not in evaluated]
        return RunListResponse(
            items=items,
            total=len(items),
            executed_but_not_evaluated=pending,
        )

    def get_run(self, run_id: str) -> RunDetail:
        if run_id not in self._repo.evaluated_run_ids():
            if run_id in self._repo.executed_run_ids():
                raise FileNotFoundError(
                    f"Run {run_id} has stored agent output but has not been evaluated."
                )
            raise KeyError(run_id)
        metrics = self._repo.metrics(run_id) or {}
        evaluation = metrics.get("evaluation") or {}
        manifest = evaluation.get("raw_manifest") or self._repo.raw_manifest(run_id)
        summary_report = self._repo.summary_report(run_id)
        registry = self._registry()
        run_tasks = self._run_tasks(run_id)
        case_counts = self._case_counts_by_task()
        tasks = [
            self._task_summary(task, run_tasks, case_counts)
            for task in registry
            if task["task_id"] in run_tasks
            or task["task_id"] in (manifest.get("tasks") or [])
        ]
        if not tasks:
            tasks = [
                self._task_summary(task, run_tasks, case_counts)
                for task in registry
                if task["task_id"] in run_tasks
            ]
        config = manifest.get("configuration") or {}
        bundle_manifest = self._repo.run_bundle_json(run_id, "manifest.json")
        summary_bundle = self._repo.run_bundle_json(run_id, "summary.json")
        return RunDetail(
            run_id=run_id,
            created_at=manifest.get("created_at"),
            evaluated_at=evaluation.get("evaluated_at"),
            git_commit=manifest.get("git_commit"),
            evaluator_commit=evaluation.get("evaluator_commit"),
            random_seed=config.get("random_seed"),
            configuration=_without_secrets(config),
            provider_chain=list(manifest.get("provider_chain") or []),
            models=self._providers(run_id),
            execution=metrics.get("execution_metrics") or {},
            bootstrap=evaluation.get("bootstrap") or {},
            tasks=tasks,
            datasets=self._repo.dataset_metrics(run_id),
            ground_truth_files_hashed=(
                (summary_report.get("reproducibility") or {}).get(
                    "ground_truth_files_hashed"
                )
            ),
            safety_gate=self._repo.run_bundle_json(run_id, "safety_gate.json"),
            checkpoints=self._repo.run_bundle_list(run_id, "checkpoints.json"),
            prompt_versions=self._repo.run_bundle_list(run_id, "prompt_versions.json"),
            dataset_fingerprints=self._repo.run_bundle_list(run_id, "fingerprints.json"),
            regression=self._repo.run_bundle_json(run_id, "regression.json"),
            invalid_output_count=summary_bundle.get("invalid_output_count"),
            llm_as_judge=bool((bundle_manifest.get("llm_as_judge") or {}).get("used")),
            code_version=bundle_manifest.get("code_version")
            or manifest.get("git_commit")
            or evaluation.get("evaluator_commit"),
            deterministic_llm=(bundle_manifest.get("generation") or {}).get(
                "deterministic_llm"
            ),
            run_health=self._run_health(run_id, manifest, metrics),
        )

    # ------------------------------------------------------------------
    # datasets
    # ------------------------------------------------------------------

    def datasets(self, run_id: Optional[str] = None) -> DatasetCoverageResponse:
        run_id = self._resolve_run(run_id)
        inventory = self._repo.dataset_inventory()
        run_datasets = self._repo.dataset_metrics(run_id) if run_id else {}
        registry = self._registry()
        case_counts = self._case_counts_by_dataset()
        catalog = [
            DatasetSummary(
                name="MIMIC-IV Clinical Database Demo",
                version="2.2",
                source="PhysioNet MIMIC-IV demo",
                table_count=_inventory_table_count(
                    inventory, "MIMIC-IV Clinical Database Demo"
                ),
                cases_in_benchmark=case_counts.get("MIMIC-IV Demo", 0)
                + case_counts.get("MIMIC-IV Demo, MIMIC-IV-ED Demo", 0),
                cases_evaluated=_evaluated_for_dataset(run_datasets, "MIMIC"),
                tasks_supported=_tasks_for_dataset(registry, "MIMIC-IV Demo"),
                ground_truth_available=True,
                limitations=[
                    "Public demo of roughly 100 patients from one US academic centre, 2008–2019.",
                    "Does not represent a general or non-US hospital population.",
                ],
            ),
            DatasetSummary(
                name="MIMIC-IV-ED Demo",
                version="2.2",
                source="PhysioNet MIMIC-IV-ED demo",
                table_count=_inventory_table_count(inventory, "MIMIC-IV-ED Demo"),
                cases_in_benchmark=sum(
                    count
                    for name, count in case_counts.items()
                    if "ED" in name
                ),
                cases_evaluated=_evaluated_for_dataset(run_datasets, "ED"),
                tasks_supported=_tasks_for_dataset(registry, "MIMIC-IV-ED"),
                ground_truth_available=True,
                limitations=[
                    "Triage acuity is a queueing priority assigned at the door, not a measured severity.",
                    "Linked to the same small demo cohort as MIMIC-IV.",
                ],
            ),
            DatasetSummary(
                name="TAC 2017 ADR",
                version="2017",
                source="Text Analysis Conference 2017 Adverse Drug Reaction track",
                document_count=_inventory_document_count(inventory),
                cases_in_benchmark=sum(
                    count
                    for name, count in case_counts.items()
                    if "TAC" in name
                ),
                cases_evaluated=_evaluated_for_dataset(run_datasets, "TAC"),
                splits={
                    name.split()[-1]: entry.get("cases", 0)
                    for name, entry in run_datasets.items()
                    if "TAC" in name
                },
                tasks_supported=_tasks_for_dataset(registry, "TAC 2017"),
                ground_truth_available=True,
                limitations=[
                    "Annotates adverse-reaction concepts in FDA drug labels, not clinical notes.",
                    "Train-split cases in the smoke-test run are not a held-out result.",
                ],
            ),
        ]
        run_tasks = self._run_tasks(run_id)
        coverage = [
            self._coverage_cell(task, run_tasks, self._case_counts_by_task())
            for task in registry
            if task.get("source_datasets")
        ]
        return DatasetCoverageResponse(datasets=catalog, matrix=coverage, run_id=run_id)

    # ------------------------------------------------------------------
    # cases
    # ------------------------------------------------------------------

    def list_cases(
        self,
        *,
        run_id: Optional[str] = None,
        agent: Optional[str] = None,
        task: Optional[str] = None,
        dataset: Optional[str] = None,
        status: Optional[str] = None,
        evaluation_type: Optional[str] = None,
        q: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> CaseListResponse:
        run_id = self._resolve_run(run_id)
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        results_index = self._results_index(run_id)
        agent_id = resolve_agent_id(agent) if agent else None
        query = (q or "").strip().lower()

        matched: List[CaseSummary] = []
        for entry in self._manifest_cases():
            summary = self._case_summary(entry, results_index)
            if agent_id and resolve_agent_id(summary.agent) != agent_id:
                continue
            if task and summary.task_id != task:
                continue
            if dataset and dataset.lower() not in (summary.dataset or "").lower():
                continue
            if evaluation_type and summary.evaluation_type != evaluation_type:
                continue
            if status:
                haystack = (
                    summary.evaluation_status
                    or summary.execution_status
                    or ""
                ).upper()
                if status.upper() not in haystack:
                    continue
            if query:
                blob = " ".join(
                    [
                        summary.case_id,
                        summary.agent,
                        summary.task,
                        summary.task_id,
                        summary.dataset or "",
                    ]
                ).lower()
                if query not in blob:
                    continue
            matched.append(summary)

        total = len(matched)
        start = (page - 1) * page_size
        items = matched[start : start + page_size]
        total_pages = (total + page_size - 1) // page_size if total else 0
        return CaseListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_case(self, case_id: str, run_id: Optional[str] = None) -> CaseDetail:
        run_id = self._resolve_run(run_id)
        manifest_entry = self._manifest_case(case_id)
        if manifest_entry is None:
            raise KeyError(case_id)
        case_file = manifest_entry.get("case_file") or ""
        raw_case = self._repo.ground_truth_case(str(case_file)) or {}
        result = self._repo.case_result(run_id, case_id) if run_id else None
        raw_output = self._repo.raw_result(run_id, case_id) if run_id else None

        agent_output, truncated_output = _sanitize_agent_output(
            (raw_output or {}).get("agent_output") if raw_output else None
        )
        ground_truth, truncated_gt = _sanitize_ground_truth(raw_case.get("ground_truth"))
        evaluation = None
        if result and result.get("evaluation"):
            evaluation = _sanitize_evaluation(result["evaluation"])

        notice = None
        if not result:
            notice = (
                "This case is in the benchmark but was not scored in the selected run. "
                "Input and reference are shown; there is no agent output to compare."
            )
        kind = (raw_case.get("input") or {}).get("kind")
        if kind and kind != "DRUG_LABEL_SECTIONS":
            notice = (notice + " " if notice else "") + (
                "Patient-record contents are described by provenance rather than "
                "reproduced. This view is not a patient chart."
            )

        execution = {}
        if result:
            execution = result.get("execution") or {}
        elif raw_output:
            execution = {
                "status": raw_output.get("execution_status"),
                "provider": (raw_output.get("execution") or {}).get("provider"),
                "model": (raw_output.get("execution") or {}).get("model"),
            }

        return CaseDetail(
            case_id=case_id,
            agent=manifest_entry.get("agent") or raw_case.get("agent"),
            task_id=manifest_entry.get("task_id") or raw_case.get("task_id"),
            task=manifest_entry.get("task") or raw_case.get("task"),
            dataset=manifest_entry.get("source_dataset")
            or (raw_case.get("source") or {}).get("dataset"),
            split=manifest_entry.get("split") or (raw_case.get("source") or {}).get("split"),
            categories=list(manifest_entry.get("category") or []),
            evaluation_type=manifest_entry.get("evaluation_type"),
            ground_truth_status=manifest_entry.get("ground_truth_status"),
            input=_describe_input(raw_case.get("input") or {}),
            agent_output=agent_output,
            agent_output_truncated=truncated_output,
            ground_truth=ground_truth,
            ground_truth_truncated=truncated_gt,
            evaluation=evaluation,
            execution=execution,
            provenance={
                "dataset": (raw_case.get("source") or {}).get("dataset"),
                "source_file": (raw_case.get("source") or {}).get("source_file"),
                "split": (raw_case.get("source") or {}).get("split"),
                "unified_case_id": (raw_case.get("source") or {}).get("unified_case_id"),
                "version": (raw_case.get("source") or {}).get("version"),
            },
            run_id=run_id,
            notice=notice,
        )

    # ------------------------------------------------------------------
    # errors / safety / limitations / presentation
    # ------------------------------------------------------------------

    def errors(
        self,
        run_id: Optional[str] = None,
        *,
        agent: Optional[str] = None,
        task: Optional[str] = None,
        error_type: Optional[str] = None,
        severity: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> ErrorAnalysisResponse:
        run_id = self._resolve_run(run_id)
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        payload = self._repo.error_analysis(run_id) if run_id else {}
        taxonomy = (self._repo.error_taxonomy().get("error_types") or [])
        groups = [
            ErrorGroup(
                agent=resolve_agent_name(group.get("agent")),
                task=group.get("task") or "",
                dataset=group.get("dataset"),
                error_type=group.get("error_type") or "OTHER",
                severity=group.get("severity") or "MEDIUM",
                count=int(group.get("count") or 0),
                cases_affected=int(group.get("cases_affected") or 0),
                representative_case_ids=list(group.get("representative_case_ids") or []),
                examples=list(group.get("examples") or []),
            )
            for group in payload.get("groups") or []
        ]
        agent_id = resolve_agent_id(agent) if agent else None
        if agent_id:
            groups = [g for g in groups if resolve_agent_id(g.agent) == agent_id]
        if task:
            groups = [g for g in groups if g.task == task]
        if error_type:
            groups = [g for g in groups if g.error_type == error_type]
        if severity:
            groups = [g for g in groups if g.severity == severity.upper()]

        by_agent: Dict[str, int] = {}
        for group in groups:
            by_agent[group.agent] = by_agent.get(group.agent, 0) + group.count

        total = len(groups)
        start = (page - 1) * page_size
        return ErrorAnalysisResponse(
            run_id=run_id,
            total_errors=int(payload.get("total_errors") or 0) if not (agent or task or error_type or severity) else sum(g.count for g in groups),
            cases_with_errors=int(payload.get("cases_with_errors") or 0),
            by_error_type=dict(payload.get("by_error_type") or {}),
            by_severity=dict(payload.get("by_severity") or {}),
            by_task=dict(payload.get("by_task") or {}),
            by_agent=by_agent,
            by_dataset=dict(payload.get("by_dataset") or {}),
            groups=groups[start : start + page_size],
            total_groups=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size if total else 0,
            taxonomy=taxonomy,
            notes=list(payload.get("notes") or []),
        )

    def safety(self, run_id: Optional[str] = None) -> SafetyResponse:
        run_id = self._resolve_run(run_id)
        payload = self._repo.safety_metrics(run_id) if run_id else {}
        if not payload:
            rules = self._repo.safety_rules()
            return SafetyResponse(
                run_id=run_id,
                exercised=False,
                notice=(
                    "No safety benchmark was exercised. An absent check is not a pass."
                ),
                rules_without_reference=[
                    SafetyRuleResult(
                        rule_id=rule.get("rule_id") or "",
                        task=rule.get("task_id") or "",
                        status=rule.get("status") or "NOT_VALIDATABLE",
                        description=rule.get("description") or "",
                        reason=rule.get("reason_not_validatable") or rule.get("reason"),
                        required_to_enable=rule.get("required_to_enable"),
                        limitations=list(rule.get("limitations") or []),
                    )
                    for rule in rules.get("rules") or []
                ],
                principles=list(rules.get("principles") or []),
            )

        def _rule(entry: Dict[str, Any]) -> SafetyRuleResult:
            result = entry.get("result") or {}
            return SafetyRuleResult(
                rule_id=entry.get("rule_id") or "",
                task=entry.get("task") or "",
                status=entry.get("status") or "",
                description=entry.get("description") or "",
                task_present_in_run=bool(entry.get("task_present_in_run")),
                false_negatives=result.get("false_negatives", entry.get("false_negatives")),
                false_negative_case_ids=list(
                    result.get("false_negative_case_ids")
                    or entry.get("false_negative_case_ids")
                    or []
                ),
                true_positives=result.get("true_positives"),
                false_positives=result.get("false_positives"),
                true_negatives=result.get("true_negatives"),
                positive_reference_count=result.get("positive_reference_count"),
                sensitivity=result.get("sensitivity"),
                specificity=result.get("specificity"),
                cases=result.get("cases"),
                reason=entry.get("reason"),
                required_to_enable=entry.get("required_to_enable"),
                limitations=list(entry.get("limitations") or []),
                decision_rule=entry.get("decision_rule"),
            )

        evaluated = [_rule(entry) for entry in payload.get("evaluated_rules") or []]
        return SafetyResponse(
            run_id=run_id,
            exercised=bool(evaluated),
            false_negatives_total=int(payload.get("false_negatives_total") or 0),
            critical_findings=list(payload.get("critical_findings") or []),
            evaluated_rules=evaluated,
            rules_not_exercised=[
                _rule(entry)
                for entry in payload.get("rules_not_exercised_in_this_run") or []
            ],
            rules_without_reference=[
                _rule(entry)
                for entry in payload.get("rules_without_a_reference") or []
            ],
            principles=list(payload.get("principles") or []),
            notice=(
                None
                if evaluated
                else "No safety rule was exercised in this run. This is an absence of evidence and must not be read as a clean result."
            ),
            safety_gate=self._repo.run_bundle_json(run_id, "safety_gate.json") if run_id else {},
        )

    def limitations(self, run_id: Optional[str] = None) -> LimitationsResponse:
        run_id = self._resolve_run(run_id)
        report = self._repo.summary_report(run_id) if run_id else {}
        registry = self._registry()
        items = [
            LimitationItem(area=item.get("area") or "", detail=item.get("detail") or "")
            for item in report.get("limitations") or []
        ]
        if not items:
            items = [
                LimitationItem(
                    area="No evaluation yet",
                    detail="Limitations are generated from an evaluated run. None is stored.",
                )
            ]
        unsupported = [
            {
                "task_id": task["task_id"],
                "task": task["task"],
                "agent": task["agent"],
                "reason": task.get("eligibility_reason") or "No suitable benchmark exists.",
            }
            for task in registry
            if task.get("status") == "NOT_SUPPORTED"
            or task.get("evaluation_type") == "NOT_VALIDATABLE"
        ]
        human = [
            {
                "task_id": task["task_id"],
                "task": task["task"],
                "agent": task["agent"],
                "reason": task.get("eligibility_reason")
                or "Automatic evaluation is insufficient for this task.",
            }
            for task in registry
            if task.get("evaluation_type") == "HUMAN_REVIEW_REQUIRED"
        ]
        structured = [
            StructuredLimitation(**item)
            for item in (
                self._repo.run_bundle_list(run_id, "limitations.json") if run_id else []
            )
            if isinstance(item, dict) and item.get("limitation_id")
        ]
        return LimitationsResponse(
            run_id=run_id,
            items=items,
            unsupported_tasks=unsupported,
            human_review_tasks=human,
            registry_coverage=report.get("registry_coverage") or {},
            disclaimer=report.get("disclaimer") or DISCLAIMER,
            structured=structured,
        )

    def presentation(self, run_id: Optional[str] = None) -> PresentationResponse:
        overview = self.overview(run_id)
        safety = self.safety(run_id)
        limitations = self.limitations(run_id)
        counters = overview.counters
        metric_bullets = []
        for group in overview.metric_groups:
            for entry in group.entries:
                if entry.value is None:
                    continue
                metric_bullets.append(
                    f"{entry.task}: {entry.metric} {entry.value:.3f}"
                    + (
                        f" (precision {entry.precision:.3f}, recall {entry.recall:.3f})"
                        if entry.precision is not None and entry.recall is not None
                        else ""
                    )
                )
        if not metric_bullets:
            metric_bullets = ["No quality metric has been scored in the selected run."]

        agent_bullets = [
            f"{agent.agent}: {agent.tasks_validated} scored / "
            f"{agent.tasks_not_validatable} not validatable / "
            f"{agent.tasks_pending_human_review} pending review"
            for agent in overview.agents
        ]
        safety_bullets = [
            f"False negatives: {safety.false_negatives_total}",
            safety.notice or "Safety findings are reported separately from quality metrics.",
        ]
        for rule in safety.rules_without_reference[:4]:
            safety_bullets.append(f"{rule.task}: {rule.status}")

        slides = [
            PresentationSlide(
                key="project",
                title="Project validation",
                subtitle="Evidence-based evaluation of the five-agent clinical AI system",
                bullets=[
                    f"Run {overview.run_id or 'none yet'}",
                    DISCLAIMER,
                ],
                stats=[
                    {"label": "Agents", "value": counters.total_agents},
                    {"label": "Tasks", "value": counters.total_tasks},
                    {"label": "Validated tasks", "value": counters.validated_tasks},
                    {"label": "Cases evaluated", "value": counters.cases_evaluated},
                ],
            ),
            PresentationSlide(
                key="agents",
                title="Five agents",
                bullets=agent_bullets,
            ),
            PresentationSlide(
                key="coverage",
                title="Dataset coverage",
                bullets=[
                    f"{cell.task} — {cell.validation_state.replace('_', ' ').title()}"
                    for cell in overview.coverage
                    if cell.validation_state == "VALIDATED"
                ]
                or ["No task was scored against a dataset in this run."],
                stats=[
                    {"label": "Not validatable", "value": counters.not_validatable_tasks},
                    {"label": "Pending review", "value": counters.human_review_tasks},
                    {
                        "label": "Exercised this run",
                        "value": counters.tasks_exercised_in_latest_run,
                    },
                ],
            ),
            PresentationSlide(
                key="metrics",
                title="Key metrics",
                subtitle="Only metrics that exist are shown. Unrelated figures are not averaged.",
                bullets=metric_bullets,
            ),
            PresentationSlide(
                key="safety",
                title="Safety findings",
                bullets=safety_bullets,
            ),
            PresentationSlide(
                key="limitations",
                title="Limitations",
                bullets=[f"{item.area}: {item.detail}" for item in limitations.items[:8]],
            ),
        ]
        return PresentationResponse(
            run_id=overview.run_id,
            generated_at=overview.evaluated_at,
            slides=slides,
            disclaimer=DISCLAIMER,
        )

    def human_review(self, run_id: Optional[str] = None) -> HumanReviewStatus:
        run_id = self._resolve_run(run_id)
        payload = self._repo.human_review_index(run_id) if run_id else {}
        pending = int(payload.get("pending_cases") or 0)
        registry_pending = [
            task["task_id"]
            for task in self._registry()
            if task.get("evaluation_type") == "HUMAN_REVIEW_REQUIRED"
        ]
        return HumanReviewStatus(
            pending_cases=pending,
            status=payload.get("status") or ("NONE_QUEUED" if not pending else "AWAITING_REVIEW"),
            by_task=dict(payload.get("by_task") or {}),
            criteria=[
                "factual_correctness",
                "completeness",
                "clinical_relevance",
                "evidence_grounding",
                "safety",
                "clarity",
                "unsupported_claims",
            ],
            note=(
                payload.get("note")
                or (
                    f"{len(registry_pending)} tasks require clinician review. "
                    "Unreviewed cases contribute to no metric."
                )
            ),
        )

    def health(self) -> ValidationHealthResponse:
        return ValidationHealthResponse(**self._repo.health_snapshot())

    def metric_definitions(self) -> MetricDefinitionsResponse:
        payload = self._repo.metric_definitions()
        metrics = [
            MetricDefinition(
                metric_name=item.get("metric_name") or "",
                description=item.get("description") or "",
                formula=item.get("formula") or "",
                expected_range=list(item.get("expected_range") or []),
                higher_is_better=bool(item.get("higher_is_better", True)),
                applicable_evaluation_types=list(
                    item.get("applicable_evaluation_types") or []
                ),
                undefined_when=item.get("undefined_when"),
                not_for=list(item.get("not_for") or []),
            )
            for item in payload.get("metrics") or []
        ]
        return MetricDefinitionsResponse(
            metrics=metrics,
            primary_by_evaluation_type=dict(
                payload.get("primary_by_evaluation_type") or {}
            ),
        )

    def evidence(self, run_id: Optional[str] = None) -> List[EvidenceCard]:
        run_id = self._resolve_run(run_id)
        if not run_id:
            return []
        cards = self._repo.run_bundle_list(run_id, "evidence.json")
        return [EvidenceCard(**card) for card in cards if isinstance(card, dict)]

    def methodology(self, task_id: str, run_id: Optional[str] = None) -> MethodologyResponse:
        task = self.get_task(task_id, run_id)
        defs = {item.metric_name: item for item in self.metric_definitions().metrics}
        headline = task.headline
        metric_key = None
        if headline and headline.metric:
            metric_key = headline.metric.lower().replace("micro ", "").replace("macro ", "")
        definition = defs.get(metric_key or "")
        cards = [card for card in self.evidence(task.run_id) if card.task_id == task_id]
        card = cards[0] if cards else None
        n = headline.cases_evaluated if headline else None
        if not n:
            sample_n = task.sample.get("evaluated") if isinstance(task.sample, dict) else None
            n = sample_n if isinstance(sample_n, int) and sample_n > 0 else None
        return MethodologyResponse(
            task_id=task.task_id,
            task=task.task,
            dataset=", ".join(task.source_datasets) or None,
            cases=n,
            ground_truth=task.ground_truth_status,
            ground_truth_level=card.ground_truth_level if card else None,
            metric=headline.metric if headline else None,
            metric_definition=definition,
            evaluation=task.evaluation_type,
            model=task.providers[0].model if task.providers else None,
            provider=task.providers[0].provider if task.providers else None,
            prompt_version=card.prompt_version if card else None,
            prompt_hash=card.prompt_hash if card else None,
            run_id=task.run_id,
            n=n,
            ci=task.confidence_intervals,
            llm_judge=False,
        )

    def compare(self, run_a: str, run_b: str) -> CompareResponse:
        from app.schemas.validation import CompareRow

        tasks_a = self._repo.task_metrics(run_a)
        tasks_b = self._repo.task_metrics(run_b)
        if not tasks_a and run_a not in self._repo.evaluated_run_ids():
            raise KeyError(run_a)
        if not tasks_b and run_b not in self._repo.evaluated_run_ids():
            raise KeyError(run_b)
        rows = []
        for task_id in sorted(set(tasks_a) | set(tasks_b)):
            left = tasks_a.get(task_id) or {}
            right = tasks_b.get(task_id) or {}
            micro_a = (left.get("quality") or {}).get("micro") or {}
            micro_b = (right.get("quality") or {}).get("micro") or {}
            for metric in ("f1", "precision", "recall"):
                a_val = micro_a.get(metric)
                b_val = micro_b.get(metric)
                if a_val is None and b_val is None:
                    continue
                change = None
                if isinstance(a_val, (int, float)) and isinstance(b_val, (int, float)):
                    change = round(float(b_val) - float(a_val), 4)
                rows.append(
                    CompareRow(
                        task_id=task_id,
                        metric=metric,
                        run_a=a_val if isinstance(a_val, (int, float)) else None,
                        run_b=b_val if isinstance(b_val, (int, float)) else None,
                        change=change,
                        n_a=(left.get("sample") or {}).get("evaluated"),
                        n_b=(right.get("sample") or {}).get("evaluated"),
                        comparable=change is not None,
                        interpretation="Change. Statistical significance has not been tested.",
                    )
                )
        previous = self._run_regression_snapshot(run_a)
        current = self._run_regression_snapshot(run_b)
        return CompareResponse(
            run_a=run_a,
            run_b=run_b,
            rows=rows,
            notice=(
                "Only stored metrics that exist on both runs are compared. "
                "A difference is a change, not an improvement. No significance test is applied."
            ),
            regression=self._regression(previous, current),
        )

    def hardening_bundle(self, run_id: Optional[str] = None) -> HardeningBundleResponse:
        run_id = self._resolve_run(run_id)
        if not run_id:
            raise KeyError("No evaluated run")
        limitations = [
            StructuredLimitation(**item)
            for item in self._repo.run_bundle_list(run_id, "limitations.json")
            if isinstance(item, dict) and item.get("limitation_id")
        ]
        evidence = [
            EvidenceCard(**item)
            for item in self._repo.run_bundle_list(run_id, "evidence.json")
            if isinstance(item, dict)
        ]
        summary = self._repo.run_bundle_json(run_id, "summary.json")
        return HardeningBundleResponse(
            run_id=run_id,
            manifest=self._repo.run_bundle_json(run_id, "manifest.json"),
            checkpoints=self._repo.run_bundle_list(run_id, "checkpoints.json"),
            safety_gate=self._repo.run_bundle_json(run_id, "safety_gate.json"),
            human_review=self._repo.run_bundle_json(run_id, "human_review_gate.json"),
            fingerprints=self._repo.run_bundle_list(run_id, "fingerprints.json"),
            prompt_versions=self._repo.run_bundle_list(run_id, "prompt_versions.json"),
            limitations=limitations,
            regression=self._repo.run_bundle_json(run_id, "regression.json"),
            evidence=evidence,
            audit=self._repo.run_bundle_list(run_id, "audit.json"),
            invalid_output_count=summary.get("invalid_output_count"),
        )

    def _run_regression_snapshot(self, run_id: str) -> Dict[str, Any]:
        metrics = self._repo.metrics(run_id) or {}
        execution = metrics.get("execution_metrics") or {}
        safety = self._repo.safety_metrics(run_id)
        task_points = {}
        for task_id, entry in self._repo.task_metrics(run_id).items():
            micro = (entry.get("quality") or {}).get("micro") or {}
            task_points[task_id] = {
                "f1": micro.get("f1"),
                "precision": micro.get("precision"),
                "recall": micro.get("recall"),
            }
        return {
            "run_id": run_id,
            "execution_success_rate": execution.get("success_rate"),
            "safety_false_negatives": safety.get("false_negatives_total"),
            "task_metrics": task_points,
        }

    def _regression(self, previous: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        flags = []
        thresholds = {
            "f1_absolute_drop": 0.05,
            "recall_absolute_drop": 0.05,
            "execution_success_drop": 0.10,
            "safety_false_negative_increase": 1.0,
        }
        prev_rate = previous.get("execution_success_rate")
        curr_rate = current.get("execution_success_rate")
        if isinstance(prev_rate, (int, float)) and isinstance(curr_rate, (int, float)):
            if curr_rate - prev_rate <= -thresholds["execution_success_drop"]:
                flags.append({"kind": "execution_success_rate", "label": "REGRESSION DETECTED"})
        for task_id, metrics in (current.get("task_metrics") or {}).items():
            prior = (previous.get("task_metrics") or {}).get(task_id) or {}
            for name, limit in (("f1", 0.05), ("recall", 0.05)):
                before, after = prior.get(name), metrics.get(name)
                if isinstance(before, (int, float)) and isinstance(after, (int, float)):
                    if after - before <= -limit:
                        flags.append(
                            {
                                "kind": name,
                                "task_id": task_id,
                                "previous": before,
                                "current": after,
                                "label": "REGRESSION DETECTED",
                            }
                        )
        if previous.get("run_id") == current.get("run_id"):
            return {
                "status": "NOT_APPLICABLE",
                "reason": "Comparing a run with itself is not a regression check.",
                "thresholds": thresholds,
                "flags": [],
            }
        return {
            "status": "REGRESSION DETECTED" if flags else "NO_REGRESSION",
            "previous_run_id": previous.get("run_id"),
            "current_run_id": current.get("run_id"),
            "thresholds": thresholds,
            "flags": flags,
            "notice": "Thresholds are documented absolute drops, not p-values.",
        }

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _resolve_run(self, run_id: Optional[str]) -> Optional[str]:
        if run_id:
            if run_id not in self._repo.evaluated_run_ids():
                if run_id in self._repo.executed_run_ids():
                    return None
                raise KeyError(run_id)
            return run_id
        return self._repo.latest_run_id()

    def _registry(self) -> List[Dict[str, Any]]:
        return self._repo.task_registry()

    def _registry_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        for task in self._registry():
            if task.get("task_id") == task_id:
                return task
        return None

    def _intake_latest_summary(self) -> Dict[str, Any]:
        path = get_settings().validation_root_path / "results" / "intake" / "latest" / "summary.json"
        if not path.is_file():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _intake_overlay(self) -> Dict[str, Any]:
        """Most complete stored Intake report per task. Read-only; no rescoring."""
        from app.services.intake_validation_service import intake_validation_service

        root = get_settings().validation_root_path / "results" / "intake"
        mtime = root.stat().st_mtime if root.is_dir() else 0.0
        if self._intake_overlay_cache and self._intake_overlay_cache[0] == mtime:
            return self._intake_overlay_cache[1]

        best: Dict[str, Any] = {}
        for task_id, payload in intake_validation_service.best_task_reports().items():
            if task_id in _HIDDEN_INTAKE_TASKS:
                continue
            row = {
                "task": payload.get("task") or task_id,
                "status": payload.get("status"),
                "evaluated_cases": payload.get("evaluated_cases"),
                "total_cases": payload.get("total_cases"),
                "eligible_cases": payload.get("eligible_cases"),
                "accuracy": (payload.get("metrics") or {}).get("accuracy", payload.get("accuracy")),
                "precision": (payload.get("metrics") or {}).get("precision", payload.get("precision")),
                "recall": (payload.get("metrics") or {}).get("recall", payload.get("recall")),
                "f1_score": (payload.get("metrics") or {}).get("f1_score", payload.get("f1_score")),
                "display_metrics": payload.get("display_metrics") or [],
                "main_metric": payload.get("main_metric"),
            }
            status = str(payload.get("status") or "NOT_EXECUTED")
            quality = None if status == "NOT_VALIDATABLE" else _intake_quality_from_report(row)
            best[task_id] = {
                "task": task_id,
                "agent": "intake",
                "status": status,
                "sample": {
                    "evaluated": int(payload.get("evaluated_cases") or 0),
                    "eligible_cases": int(
                        payload.get("total_cases") or payload.get("eligible_cases") or 0
                    ),
                },
                "quality": quality,
                "_report_main_metric": payload.get("main_metric"),
                "_report_display_metrics": payload.get("display_metrics") or [],
                "_report_notes": payload.get("metric_notes") or payload.get("notes") or [],
                "_source_run_id": payload.get("source_metrics_dir") or payload.get("_snapshot"),
            }

        self._intake_overlay_cache = (mtime, best)
        return best

    def _merge_intake_overlay(self, tasks: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(tasks)
        for task_id, entry in self._intake_overlay().items():
            existing = merged.get(task_id) or {}
            existing_n = int((existing.get("sample") or {}).get("evaluated") or 0)
            overlay_n = int((entry.get("sample") or {}).get("evaluated") or 0)
            if overlay_n > existing_n or (
                overlay_n == existing_n and entry.get("status") == "VALIDATED"
            ) or task_id not in merged:
                merged[task_id] = entry
        return merged

    def _diagnosis_overlay(self) -> Dict[str, Any]:
        """Most complete stored Diagnosis report per task. Read-only; no rescoring."""
        from app.services.diagnosis_validation_service import diagnosis_validation_service

        root = get_settings().validation_root_path / "results" / "diagnosis"
        mtime = root.stat().st_mtime if root.is_dir() else 0.0
        if self._diagnosis_overlay_cache and self._diagnosis_overlay_cache[0] == mtime:
            return self._diagnosis_overlay_cache[1]

        best: Dict[str, Any] = {}
        for task_id, payload in diagnosis_validation_service.best_task_reports().items():
            row = {
                "task": payload.get("task") or task_id,
                "status": payload.get("status"),
                "evaluated_cases": payload.get("evaluated_cases"),
                "total_cases": payload.get("total_cases"),
                "eligible_cases": payload.get("eligible_cases"),
                "accuracy": (payload.get("metrics") or {}).get("accuracy", payload.get("accuracy")),
                "precision": (payload.get("metrics") or {}).get("precision", payload.get("precision")),
                "recall": (payload.get("metrics") or {}).get("recall", payload.get("recall")),
                "f1_score": (payload.get("metrics") or {}).get("f1_score", payload.get("f1_score")),
                "display_metrics": payload.get("display_metrics") or [],
                "main_metric": payload.get("main_metric"),
            }
            status = str(payload.get("status") or "NOT_EXECUTED")
            quality = None if status == "NOT_VALIDATABLE" else _diagnosis_quality_from_report(row)
            best[task_id] = {
                "task": task_id,
                "agent": "diagnosis",
                "status": status,
                "sample": {
                    "evaluated": int(payload.get("evaluated_cases") or 0),
                    "eligible_cases": int(
                        payload.get("total_cases") or payload.get("eligible_cases") or 0
                    ),
                },
                "quality": quality,
                "_report_main_metric": payload.get("main_metric"),
                "_report_display_metrics": payload.get("display_metrics") or [],
                "_report_notes": payload.get("metric_notes") or payload.get("notes") or [],
                "_source_run_id": payload.get("source_metrics_dir") or payload.get("_snapshot"),
            }

        self._diagnosis_overlay_cache = (mtime, best)
        return best

    def _merge_diagnosis_overlay(self, tasks: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(tasks)
        for task_id, entry in self._diagnosis_overlay().items():
            if not str(task_id).startswith("diagnosis_"):
                continue
            existing = merged.get(task_id) or {}
            existing_n = int((existing.get("sample") or {}).get("evaluated") or 0)
            overlay_n = int((entry.get("sample") or {}).get("evaluated") or 0)
            if overlay_n > existing_n or (
                overlay_n == existing_n and entry.get("status") == "VALIDATED"
            ) or task_id not in merged:
                merged[task_id] = entry
        return merged

    def _research_overlay(self) -> Dict[str, Any]:
        from app.services.research_validation_service import research_validation_service

        root = get_settings().validation_root_path / "results" / "research"
        mtime = root.stat().st_mtime if root.is_dir() else 0.0
        if self._research_overlay_cache and self._research_overlay_cache[0] == mtime:
            return self._research_overlay_cache[1]

        best: Dict[str, Any] = {}
        for task_id, payload in research_validation_service.best_task_reports().items():
            row = {
                "task": payload.get("task") or task_id,
                "status": payload.get("status"),
                "evaluated_cases": payload.get("evaluated_cases"),
                "total_cases": payload.get("total_cases"),
                "eligible_cases": payload.get("eligible_cases"),
                "display_metrics": payload.get("display_metrics") or [],
                "main_metric": payload.get("main_metric"),
            }
            status = str(payload.get("status") or "NOT_EXECUTED")
            quality = None if status == "NOT_VALIDATABLE" else _research_quality_from_report(row)
            best[task_id] = {
                "task": task_id,
                "agent": "research",
                "status": status,
                "sample": {
                    "evaluated": int(payload.get("evaluated_cases") or 0),
                    "eligible_cases": int(
                        payload.get("total_cases") or payload.get("eligible_cases") or 0
                    ),
                },
                "quality": quality,
                "_report_main_metric": payload.get("main_metric"),
                "_report_display_metrics": payload.get("display_metrics") or [],
                "_report_notes": payload.get("metric_notes") or payload.get("notes") or [],
                "_source_run_id": payload.get("source_metrics_dir") or payload.get("_snapshot"),
            }

        self._research_overlay_cache = (mtime, best)
        return best

    def _merge_research_overlay(self, tasks: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(tasks)
        for task_id, entry in self._research_overlay().items():
            if not str(task_id).startswith("research_"):
                continue
            existing = merged.get(task_id) or {}
            existing_n = int((existing.get("sample") or {}).get("evaluated") or 0)
            overlay_n = int((entry.get("sample") or {}).get("evaluated") or 0)
            if overlay_n > existing_n or (
                overlay_n == existing_n and entry.get("status") == "VALIDATED"
            ) or task_id not in merged:
                merged[task_id] = entry
        return merged

    def _prescription_overlay(self) -> Dict[str, Any]:
        from app.services.prescription_validation_service import prescription_validation_service

        root = get_settings().validation_root_path / "results" / "prescription"
        mtime = root.stat().st_mtime if root.is_dir() else 0.0
        if self._prescription_overlay_cache and self._prescription_overlay_cache[0] == mtime:
            return self._prescription_overlay_cache[1]

        best: Dict[str, Any] = {}
        for task_id, payload in prescription_validation_service.best_task_reports().items():
            row = {
                "task": payload.get("task") or task_id,
                "status": payload.get("status"),
                "evaluated_cases": payload.get("evaluated_cases"),
                "total_cases": payload.get("total_cases"),
                "eligible_cases": payload.get("eligible_cases"),
                "recall": (payload.get("metrics") or {}).get("recall"),
                "precision": (payload.get("metrics") or {}).get("precision"),
                "field_accuracy": (payload.get("metrics") or {}).get("field_accuracy"),
                "display_metrics": payload.get("display_metrics") or [],
                "main_metric": payload.get("main_metric"),
            }
            status = str(payload.get("status") or "NOT_EXECUTED")
            quality = None if status in {"NOT_VALIDATABLE", "PENDING_HUMAN_REVIEW"} else (
                _prescription_quality_from_report(row)
            )
            best[task_id] = {
                "task": task_id,
                "agent": "prescription",
                "status": status,
                "sample": {
                    "evaluated": int(payload.get("evaluated_cases") or 0),
                    "eligible_cases": int(
                        payload.get("total_cases") or payload.get("eligible_cases") or 0
                    ),
                },
                "quality": quality,
                "_report_main_metric": payload.get("main_metric"),
                "_report_display_metrics": payload.get("display_metrics") or [],
                "_report_notes": payload.get("metric_notes") or payload.get("notes") or [],
                "_source_run_id": payload.get("source_metrics_dir") or payload.get("_snapshot"),
            }

        self._prescription_overlay_cache = (mtime, best)
        return best

    def _merge_prescription_overlay(self, tasks: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(tasks)
        for task_id, entry in self._prescription_overlay().items():
            if not str(task_id).startswith("prescription_"):
                continue
            existing = merged.get(task_id) or {}
            existing_n = int((existing.get("sample") or {}).get("evaluated") or 0)
            overlay_n = int((entry.get("sample") or {}).get("evaluated") or 0)
            if overlay_n > existing_n or (
                overlay_n == existing_n and entry.get("status") == "VALIDATED"
            ) or task_id not in merged:
                merged[task_id] = entry
        return merged

    def _medical_report_overlay(self) -> Dict[str, Any]:
        from app.services.medical_report_validation_service import (
            medical_report_validation_service,
        )

        root = get_settings().validation_root_path / "results" / "medical_report"
        mtime = root.stat().st_mtime if root.is_dir() else 0.0
        if self._medical_report_overlay_cache and self._medical_report_overlay_cache[0] == mtime:
            return self._medical_report_overlay_cache[1]

        best: Dict[str, Any] = {}
        for task_id, payload in medical_report_validation_service.best_task_reports().items():
            row = {
                "task": payload.get("task") or task_id,
                "status": payload.get("status"),
                "evaluated_cases": payload.get("evaluated_cases"),
                "total_cases": payload.get("total_cases"),
                "eligible_cases": payload.get("eligible_cases"),
                "recall": (payload.get("metrics") or {}).get("recall"),
                "precision": (payload.get("metrics") or {}).get("precision"),
                "f1": (payload.get("metrics") or {}).get("f1"),
                "display_metrics": payload.get("display_metrics") or [],
                "main_metric": payload.get("main_metric"),
            }
            status = str(payload.get("status") or "NOT_EXECUTED")
            quality = None if status in {"NOT_VALIDATABLE", "NOT_EXECUTED"} else (
                _medical_report_quality_from_report(row)
            )
            best[task_id] = {
                "task": task_id,
                "agent": "medical_report",
                "status": status,
                "sample": {
                    "evaluated": int(payload.get("evaluated_cases") or 0),
                    "eligible_cases": int(
                        payload.get("total_cases") or payload.get("eligible_cases") or 0
                    ),
                },
                "quality": quality,
                "_report_main_metric": payload.get("main_metric"),
                "_report_display_metrics": payload.get("display_metrics") or [],
                "_report_notes": payload.get("metric_notes") or payload.get("notes") or [],
                "_source_run_id": payload.get("source_metrics_dir") or payload.get("_snapshot"),
            }

        self._medical_report_overlay_cache = (mtime, best)
        return best

    def _merge_medical_report_overlay(self, tasks: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(tasks)
        for task_id, entry in self._medical_report_overlay().items():
            if not str(task_id).startswith("medical_report_"):
                continue
            existing = merged.get(task_id) or {}
            existing_n = int((existing.get("sample") or {}).get("evaluated") or 0)
            overlay_n = int((entry.get("sample") or {}).get("evaluated") or 0)
            if overlay_n > existing_n or (
                overlay_n == existing_n and entry.get("status") == "VALIDATED"
            ) or task_id not in merged:
                merged[task_id] = entry
        return merged

    def _run_tasks(self, run_id: Optional[str]) -> Dict[str, Any]:
        tasks = dict(self._repo.task_metrics(run_id) or {}) if run_id else {}
        return self._merge_medical_report_overlay(
            self._merge_prescription_overlay(
                self._merge_research_overlay(
                    self._merge_diagnosis_overlay(self._merge_intake_overlay(tasks))
                )
            )
        )

    def _evaluated_at(self, run_id: Optional[str]) -> Optional[str]:
        if not run_id:
            return None
        metrics = self._repo.metrics(run_id) or {}
        return (metrics.get("evaluation") or {}).get("evaluated_at")

    def _run_health(
        self,
        run_id: str,
        manifest: Dict[str, Any],
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execution reliability for Run Details. Not quality metrics."""
        checkpoint = self._repo.execution_checkpoint(run_id)
        execution = metrics.get("execution_metrics") or {}
        coverage = checkpoint.get("evaluation_coverage") or manifest.get("evaluation_coverage") or {}
        status = checkpoint.get("status") or manifest.get("status") or "UNKNOWN"
        pending = checkpoint.get("pending_cases")
        if pending is None:
            pending = 0
        completed = checkpoint.get("completed_cases")
        failed = checkpoint.get("failed_cases")
        interrupted = status in {"PAUSED", "CANCELLED", "RATE_LIMITED"} or (
            isinstance(pending, int) and pending > 0
        )
        stats = checkpoint.get("provider_statistics") or manifest.get("provider_statistics") or {}
        rate_limits = 0
        retries = 0
        fallbacks = 0
        latency = None
        if isinstance(stats, dict):
            for entry in stats.values():
                if not isinstance(entry, dict):
                    continue
                rate_limits += int(entry.get("rate_limit_errors") or 0)
                retries += int(entry.get("failed_requests") or 0)
                fallbacks += int(entry.get("fallback_count") or 0)
                if entry.get("average_latency_ms") is not None:
                    latency = entry.get("average_latency_ms")
        return {
            "status": status,
            "cases_completed": completed,
            "cases_pending": pending,
            "cases_failed": failed,
            "dataset_cases": manifest.get("dataset_count") or checkpoint.get("total_cases"),
            "eligible": manifest.get("eligible_count"),
            "skipped": checkpoint.get("skipped_cases") or manifest.get("skipped_count"),
            "dataset_coverage": manifest.get("dataset_coverage") or coverage or None,
            "run_coverage": manifest.get("run_coverage"),
            "rate_limits_encountered": rate_limits or execution.get("rate_limit_count"),
            "retries": retries,
            "fallbacks": fallbacks,
            "provider_usage": stats or None,
            "average_latency_ms": latency,
            "evaluation_coverage": coverage or None,
            "resume_available": interrupted or status == "COMPLETED_PARTIAL",
            "resume_reason": status if interrupted or status == "COMPLETED_PARTIAL" else None,
            "resume_command": (
                f"python validation\\pipeline\\run_validation.py --run-id {run_id} "
                "--resume --rate-limit-safe"
                if interrupted or status == "COMPLETED_PARTIAL"
                else None
            ),
        }

    def _execution(self, run_id: Optional[str]) -> Dict[str, Any]:
        if not run_id:
            return {}
        metrics = self._repo.metrics(run_id) or {}
        return metrics.get("execution_metrics") or {}

    def _providers(self, run_id: Optional[str]) -> List[ProviderUsage]:
        if not run_id:
            return []
        payload = self._repo.provider_metrics(run_id)
        nested = (payload.get("providers") or {}).get("providers") or payload.get("providers") or {}
        if not isinstance(nested, dict):
            return []
        usages: List[ProviderUsage] = []
        for name, entry in nested.items():
            if not isinstance(entry, dict):
                continue
            models = entry.get("models") or []
            usages.append(
                ProviderUsage(
                    provider=name,
                    model=models[0] if models else None,
                    cases=int(entry.get("cases") or 0),
                    successful=int(entry.get("successful") or 0),
                    mean_latency_ms=entry.get("mean_latency_ms"),
                    fallback_used=int(entry.get("fallback_used") or 0),
                )
            )
        return usages

    def _provider_block(self, run_id: Optional[str]) -> Dict[str, Any]:
        if not run_id:
            return {}
        payload = self._repo.provider_metrics(run_id)
        comparison = (payload.get("providers") or {}).get("quality_comparison") or {}
        return {
            "providers": [item.model_dump() for item in self._providers(run_id)],
            "quality_comparison": comparison,
        }

    def _manifest_cases(self) -> List[Dict[str, Any]]:
        return list((self._repo.case_manifest().get("cases") or []))

    def _manifest_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        for entry in self._manifest_cases():
            if entry.get("validation_case_id") == case_id:
                return entry
        return None

    def _case_counts_by_task(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for entry in self._manifest_cases():
            task_id = str(entry.get("task_id") or "")
            counts[task_id] = counts.get(task_id, 0) + 1
        for task_id, entry in self._intake_overlay().items():
            eligible = int((entry.get("sample") or {}).get("eligible_cases") or 0)
            if eligible:
                counts[task_id] = max(counts.get(task_id, 0), eligible)
        for task_id, entry in self._diagnosis_overlay().items():
            eligible = int((entry.get("sample") or {}).get("eligible_cases") or 0)
            if eligible:
                counts[task_id] = max(counts.get(task_id, 0), eligible)
        for task_id, entry in self._prescription_overlay().items():
            eligible = int((entry.get("sample") or {}).get("eligible_cases") or 0)
            if eligible:
                counts[task_id] = max(counts.get(task_id, 0), eligible)
        for task_id, entry in self._medical_report_overlay().items():
            eligible = int((entry.get("sample") or {}).get("eligible_cases") or 0)
            if eligible:
                counts[task_id] = max(counts.get(task_id, 0), eligible)
        return counts

    def _case_counts_by_dataset(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for entry in self._manifest_cases():
            name = str(entry.get("source_dataset") or "unknown")
            counts[name] = counts.get(name, 0) + 1
        return counts

    def _results_index(self, run_id: Optional[str]) -> Dict[str, Dict[str, Any]]:
        if not run_id:
            return {}
        index: Dict[str, Dict[str, Any]] = {}
        for record in self._repo.case_results(run_id):
            case_id = record.get("case_id")
            if case_id:
                index[str(case_id)] = record
        return index

    def _display_state(
        self, registry_task: Dict[str, Any], run_entry: Optional[Dict[str, Any]]
    ) -> str:
        if run_entry:
            status = run_entry.get("status")
            if status in {
                "VALIDATED",
                "PENDING_HUMAN_REVIEW",
                "NOT_VALIDATABLE",
            }:
                return str(status)
        evaluation_type = registry_task.get("evaluation_type")
        status = registry_task.get("status")
        if evaluation_type == "HUMAN_REVIEW_REQUIRED":
            return "PENDING_HUMAN_REVIEW"
        if evaluation_type == "NOT_VALIDATABLE" or status == "NOT_SUPPORTED":
            return "NOT_VALIDATABLE"
        if status == "PARTIALLY_SUPPORTED":
            return "PARTIALLY_VALIDATED"
        return "NOT_EXECUTED"

    def _coverage_cell(
        self,
        registry_task: Dict[str, Any],
        run_tasks: Dict[str, Any],
        case_counts: Dict[str, int],
    ) -> CoverageCell:
        task_id = registry_task["task_id"]
        run_entry = run_tasks.get(task_id)
        state = self._display_state(registry_task, run_entry)
        reason = None
        if state != "VALIDATED":
            reason = registry_task.get("eligibility_reason")
        sample = (run_entry or {}).get("sample") or {}
        benchmark = case_counts.get(task_id, 0)
        eligible = int(sample.get("eligible_cases") or 0)
        if eligible:
            benchmark = max(benchmark, eligible)
        return CoverageCell(
            task_id=task_id,
            task=registry_task.get("task") or task_id,
            agent=registry_task.get("agent") or "",
            registry_status=registry_task.get("status") or "",
            evaluation_type=registry_task.get("evaluation_type") or "",
            validation_state=state,
            reason=reason,
            cases_in_benchmark=benchmark,
            cases_evaluated=int(sample.get("evaluated") or 0),
        )

    def _status_counts(self, coverage: Iterable[CoverageCell]) -> ValidationStatusCounts:
        counts = ValidationStatusCounts()
        for cell in coverage:
            if cell.validation_state == "VALIDATED":
                counts.validated += 1
            elif cell.validation_state == "PARTIALLY_VALIDATED":
                counts.partially_validated += 1
            elif cell.validation_state == "NOT_VALIDATABLE":
                counts.not_validatable += 1
            elif cell.validation_state == "PENDING_HUMAN_REVIEW":
                counts.pending_human_review += 1
            else:
                counts.not_executed += 1
        return counts

    def _task_summary(
        self,
        registry_task: Dict[str, Any],
        run_tasks: Dict[str, Any],
        case_counts: Dict[str, int],
    ) -> TaskSummary:
        cell = self._coverage_cell(registry_task, run_tasks, case_counts)
        run_entry = run_tasks.get(cell.task_id) or {}
        headline = _headline_from_quality(cell, run_entry)
        return TaskSummary(
            task_id=cell.task_id,
            task=cell.task,
            agent=cell.agent,
            registry_status=cell.registry_status,
            evaluation_type=cell.evaluation_type,
            validation_state=cell.validation_state,
            ground_truth_status=registry_task.get("ground_truth_status"),
            cases_in_benchmark=cell.cases_in_benchmark,
            cases_evaluated=cell.cases_evaluated,
            headline=headline,
            reason=cell.reason,
        )

    def _agent_summary(
        self,
        catalog: Dict[str, str],
        registry: List[Dict[str, Any]],
        run_tasks: Dict[str, Any],
        case_counts: Dict[str, int],
        run_id: Optional[str],
    ) -> AgentSummary:
        agent_id = catalog["agent_id"]
        tasks = [
            self._task_summary(task, run_tasks, case_counts)
            for task in registry
            if resolve_agent_id(task.get("agent")) == agent_id
            and task.get("task_id") not in _HIDDEN_INTAKE_TASKS
        ]
        counts = ValidationStatusCounts()
        for task in tasks:
            if task.validation_state == "VALIDATED":
                counts.validated += 1
            elif task.validation_state == "PARTIALLY_VALIDATED":
                counts.partially_validated += 1
            elif task.validation_state == "NOT_VALIDATABLE":
                counts.not_validatable += 1
            elif task.validation_state == "PENDING_HUMAN_REVIEW":
                counts.pending_human_review += 1
            else:
                counts.not_executed += 1
        headlines = [task.headline for task in tasks if task.headline and task.headline.value is not None]
        safety = None
        for task in tasks:
            entry = run_tasks.get(task.task_id) or {}
            if entry.get("safety"):
                safety = entry["safety"]
                break
        execution = self._execution(run_id)
        return AgentSummary(
            agent_id=agent_id,
            agent=catalog["agent"],
            description=catalog["description"],
            tasks_total=len(tasks),
            tasks_validated=counts.validated,
            tasks_not_validatable=counts.not_validatable,
            tasks_pending_human_review=counts.pending_human_review,
            tasks_not_executed=counts.not_executed,
            cases_in_benchmark=sum(task.cases_in_benchmark for task in tasks),
            cases_evaluated=sum(task.cases_evaluated for task in tasks),
            execution_success_rate=execution.get("success_rate") if any(t.cases_evaluated for t in tasks) else None,
            headline_metrics=headlines,
            has_safety_findings=bool(safety and safety.get("false_negatives")),
            safety_false_negatives=(safety or {}).get("false_negatives"),
        )

    def _metric_groups(
        self, registry: List[Dict[str, Any]], run_tasks: Dict[str, Any]
    ) -> List[MetricGroup]:
        case_counts = self._case_counts_by_task()
        groups: List[MetricGroup] = []
        for category, evaluation_type, description in _METRIC_CATEGORIES:
            entries: List[TaskHeadline] = []
            for task in registry:
                if task.get("evaluation_type") != evaluation_type:
                    continue
                summary = self._task_summary(task, run_tasks, case_counts)
                if summary.headline and summary.headline.value is not None:
                    entries.append(summary.headline)
            if entries:
                groups.append(
                    MetricGroup(
                        category=category,
                        description=description,
                        entries=entries,
                    )
                )
        return groups

    def _flow(
        self,
        registry: List[Dict[str, Any]],
        case_counts: Dict[str, int],
        evaluated: int,
        run_id: Optional[str],
    ) -> List[FlowStage]:
        return [
            FlowStage(
                key="datasets",
                label="Datasets",
                detail="MIMIC-IV Demo, MIMIC-IV-ED Demo, TAC 2017 ADR",
                count=3,
            ),
            FlowStage(
                key="unified",
                label="Unified validation dataset",
                detail="Case-oriented records with input separated from ground truth",
            ),
            FlowStage(
                key="cases",
                label="Validation cases",
                detail="Task-specific benchmark cases with provenance",
                count=sum(case_counts.values()) or None,
            ),
            FlowStage(
                key="agents",
                label="Five AI agents",
                detail="Existing production pipelines, invoked without exposing the answer key",
                count=5,
            ),
            FlowStage(
                key="outputs",
                label="Agent outputs",
                detail="Stored under validation/results/raw — never written to production tables",
            ),
            FlowStage(
                key="comparison",
                label="Ground-truth comparison",
                detail="Task-specific validators; unsupported tasks are declined, not scored",
                count=len(registry),
            ),
            FlowStage(
                key="metrics",
                label="Metrics",
                detail="Read from stored evaluation artifacts; the UI does not recompute them",
                count=evaluated or None,
            ),
            FlowStage(
                key="analysis",
                label="Error + safety analysis",
                detail="False negatives reported separately from quality scores",
            ),
        ]

    def _error_groups_for_task(self, run_id: Optional[str], task_id: str) -> List[ErrorGroup]:
        if not run_id:
            return []
        payload = self._repo.error_analysis(run_id)
        return [
            ErrorGroup(
                agent=resolve_agent_name(group.get("agent")),
                task=group.get("task") or "",
                dataset=group.get("dataset"),
                error_type=group.get("error_type") or "OTHER",
                severity=group.get("severity") or "MEDIUM",
                count=int(group.get("count") or 0),
                cases_affected=int(group.get("cases_affected") or 0),
                representative_case_ids=list(group.get("representative_case_ids") or []),
                examples=list(group.get("examples") or []),
            )
            for group in payload.get("groups") or []
            if group.get("task") == task_id
        ]

    def _task_execution(self, run_id: Optional[str], task_id: str) -> Dict[str, Any]:
        run_entry = (self._run_tasks(run_id) or {}).get(task_id) or {}
        sample = run_entry.get("sample") or {}
        execution = self._execution(run_id)
        return {
            "sample": sample,
            "run_success_rate": execution.get("success_rate"),
            "run_latency_ms": execution.get("latency_ms"),
        }

    def _case_summary(
        self, entry: Dict[str, Any], results_index: Dict[str, Dict[str, Any]]
    ) -> CaseSummary:
        case_id = str(entry.get("validation_case_id") or "")
        result = results_index.get(case_id) or {}
        evaluation = result.get("evaluation") or {}
        execution = result.get("execution") or {}
        return CaseSummary(
            case_id=case_id,
            agent=entry.get("agent") or "",
            task_id=entry.get("task_id") or "",
            task=entry.get("task") or "",
            dataset=entry.get("source_dataset"),
            split=entry.get("split"),
            categories=list(entry.get("category") or []),
            ground_truth_available=bool(entry.get("ground_truth_available")),
            ground_truth_status=entry.get("ground_truth_status"),
            eligible_for_quantitative_evaluation=bool(
                entry.get("eligible_for_quantitative_evaluation")
            ),
            evaluation_type=entry.get("evaluation_type"),
            execution_status=execution.get("status") or result.get("execution_status"),
            evaluation_status=evaluation.get("status"),
        )

    def _run_summary(self, run_id: str) -> RunSummary:
        metrics = self._repo.metrics(run_id) or {}
        evaluation = metrics.get("evaluation") or {}
        manifest = evaluation.get("raw_manifest") or self._repo.raw_manifest(run_id)
        overall = metrics.get("overall") or {}
        execution = metrics.get("execution_metrics") or {}
        providers = self._providers(run_id)
        tasks_by_status = overall.get("tasks_by_status") or {}
        return RunSummary(
            run_id=run_id,
            created_at=manifest.get("created_at"),
            evaluated_at=evaluation.get("evaluated_at"),
            evaluated=True,
            agents=[resolve_agent_name(name) for name in (manifest.get("agents") or [])],
            tasks=list(manifest.get("tasks") or []),
            records=int(execution.get("total_records") or manifest.get("case_count") or 0),
            cases_attempted=int(execution.get("attempted") or 0),
            cases_evaluated=int(overall.get("cases_evaluated") or 0),
            execution_success_rate=execution.get("success_rate"),
            validated_tasks=int(tasks_by_status.get("VALIDATED") or 0),
            providers=[item.provider for item in providers],
            status=str(manifest.get("status") or "EVALUATED"),
        )


_HIDDEN_INTAKE_TASKS = {"intake_medical_entity_recognition_unannotated"}
_INTAKE_PRIMARY = {
    "intake_patient_registration": "Field Accuracy",
    "intake_medical_history_extraction": "History Item F1",
    "intake_ocr_on_reports": "Field F1",
    "intake_medical_entity_recognition": "Entity F1",
    "intake_patient_knowledge_graph_creation": "Entity F1",
}
_DIAGNOSIS_PRIMARY = {
    "diagnosis_differential_diagnosis": "Top-1 Accuracy",
    "diagnosis_disease_probability_scoring": "Top-1 Accuracy",
    "diagnosis_severity_prediction": "Macro F1",
}


def _headline_from_quality(
    cell: CoverageCell, run_entry: Dict[str, Any]
) -> Optional[TaskHeadline]:
    report_metric = run_entry.get("_report_main_metric") if isinstance(run_entry, dict) else None
    if isinstance(report_metric, dict) and report_metric.get("label"):
        value = report_metric.get("value")
        higher = not str(report_metric.get("label") or "").upper().startswith(("CER", "WER"))
        if cell.validation_state != "VALIDATED" and value is None:
            return TaskHeadline(
                task_id=cell.task_id,
                task=cell.task,
                status=cell.validation_state,
                cases_evaluated=cell.cases_evaluated,
                cases_eligible=cell.cases_in_benchmark,
                higher_is_better=higher,
            )
        return TaskHeadline(
            task_id=cell.task_id,
            task=cell.task,
            status=cell.validation_state,
            metric=str(report_metric.get("label")),
            value=value,
            cases_evaluated=cell.cases_evaluated,
            cases_eligible=cell.cases_in_benchmark,
            higher_is_better=higher,
        )

    quality = run_entry.get("quality") or {}
    metric = None
    value = None
    precision = None
    recall = None
    items = None
    higher = True
    micro = quality.get("micro") if isinstance(quality, dict) else None
    task_id = cell.task_id
    if task_id in _INTAKE_PRIMARY and isinstance(quality, dict):
        metric, value, precision, recall, items, higher = _intake_headline_values(
            task_id, quality, micro if isinstance(micro, dict) else None
        )
    elif task_id in _DIAGNOSIS_PRIMARY and isinstance(quality, dict):
        metric, value, precision, recall, items, higher = _diagnosis_headline_values(
            task_id, quality, micro if isinstance(micro, dict) else None
        )
    elif isinstance(micro, dict) and micro.get("f1") is not None:
        metric = "micro F1"
        value = micro.get("f1")
        precision = micro.get("precision")
        recall = micro.get("recall")
        items = micro.get("gold_count")
    elif isinstance(quality, dict) and quality.get("classification"):
        metric = "accuracy"
        value = quality["classification"].get("accuracy")
        items = quality["classification"].get("n")
    elif isinstance(quality, dict) and quality.get("ranking"):
        metric = "NDCG@5"
        value = quality["ranking"].get("ndcg_at_5")
    elif isinstance(quality, dict) and quality.get("structured_fields"):
        metric = "Field Accuracy"
        value = quality["structured_fields"].get("field_accuracy")
    if metric is None and cell.validation_state != "VALIDATED":
        return TaskHeadline(
            task_id=cell.task_id,
            task=cell.task,
            status=cell.validation_state,
            cases_evaluated=cell.cases_evaluated,
            cases_eligible=cell.cases_in_benchmark,
        )
    if metric is None:
        return None
    return TaskHeadline(
        task_id=cell.task_id,
        task=cell.task,
        status=cell.validation_state,
        metric=metric,
        value=value,
        precision=precision,
        recall=recall,
        items=items,
        cases_evaluated=cell.cases_evaluated,
        cases_eligible=cell.cases_in_benchmark,
        higher_is_better=higher,
    )


def _intake_headline_values(
    task_id: str,
    quality: Dict[str, Any],
    micro: Optional[Dict[str, Any]],
) -> Tuple[Optional[str], Optional[float], Optional[float], Optional[float], Optional[int], bool]:
    label = _INTAKE_PRIMARY[task_id]
    if task_id == "intake_patient_registration":
        fields = quality.get("structured_fields") or {}
        value = fields.get("field_accuracy")
        if value is None and micro:
            value = micro.get("f1")
        return label, value, None, None, None, True
    if task_id == "intake_ocr_on_reports":
        ocr = quality.get("ocr") or quality.get("fields") or {}
        if ocr.get("cer") is not None:
            return "CER", ocr.get("cer"), None, None, None, False
        value = (ocr.get("f1") if isinstance(ocr, dict) else None) or (
            micro.get("f1") if micro else None
        )
        return label, value, micro.get("precision") if micro else None, micro.get("recall") if micro else None, None, True
    if task_id == "intake_patient_knowledge_graph_creation":
        entities = quality.get("entities") or {}
        value = entities.get("f1")
        if value is None and micro:
            value = micro.get("f1")
        return label, value, entities.get("precision") or (micro.get("precision") if micro else None), entities.get("recall") or (micro.get("recall") if micro else None), None, True
    if task_id == "intake_medical_history_extraction":
        items = quality.get("history_items") or {}
        value = items.get("f1")
        if value is None and micro:
            value = micro.get("f1")
        return label, value, items.get("precision") or (micro.get("precision") if micro else None), items.get("recall") or (micro.get("recall") if micro else None), None, True
    value = micro.get("f1") if micro else None
    return label, value, micro.get("precision") if micro else None, micro.get("recall") if micro else None, micro.get("gold_count") if micro else None, True


def _diagnosis_headline_values(
    task_id: str,
    quality: Dict[str, Any],
    micro: Optional[Dict[str, Any]],
) -> Tuple[Optional[str], Optional[float], Optional[float], Optional[float], Optional[int], bool]:
    label = _DIAGNOSIS_PRIMARY[task_id]
    ranking = quality.get("ranking") if isinstance(quality.get("ranking"), dict) else {}
    classification = quality.get("classification") if isinstance(quality.get("classification"), dict) else {}
    if task_id == "diagnosis_severity_prediction":
        macro = classification.get("macro") if isinstance(classification.get("macro"), dict) else {}
        value = macro.get("f1")
        if value is None:
            value = classification.get("f1")
        return label, value, macro.get("precision"), macro.get("recall"), classification.get("n"), True
    value = ranking.get("hit_rate_at_1")
    return (
        label,
        value,
        ranking.get("precision_at_1") or (micro.get("precision") if micro else None),
        ranking.get("recall_at_5") or (micro.get("recall") if micro else None),
        ranking.get("relevant_count"),
        True,
    )


def _describe_input(payload: Dict[str, Any]) -> CaseInputDescriptor:
    kind = payload.get("kind")
    sections = []
    for section in payload.get("sections") or []:
        if not isinstance(section, dict):
            continue
        sections.append(
            {
                "id": section.get("id"),
                "name": section.get("name"),
                "char_length": section.get("char_length"),
            }
        )
    record_sets = []
    for item in payload.get("record_sets") or payload.get("sets") or []:
        if not isinstance(item, dict):
            continue
        ranges = item.get("line_ranges") or []
        record_sets.append(
            {
                "table": item.get("logical_table") or item.get("table"),
                "dataset": (item.get("provenance") or {}).get("dataset"),
                "source_table": (item.get("provenance") or {}).get("source_table"),
                "segment_count": len(ranges) if isinstance(ranges, list) else 0,
                "excluded_fields": list(
                    ((item.get("query") or {}).get("excluded_fields") or [])
                )[:20],
            }
        )
    description = None
    if kind == "DRUG_LABEL_SECTIONS":
        description = (
            "Public FDA drug-label sections. Section names and lengths are shown; "
            "the full label text is not duplicated here."
        )
    elif record_sets:
        description = (
            f"{len(record_sets)} patient-record set(s) referenced by table. "
            "Row contents are not returned."
        )
    elif kind:
        description = f"Input kind {kind}."
    return CaseInputDescriptor(
        kind=kind,
        description=description,
        record_sets=record_sets,
        document_sections=sections,
        excerpt=None,
        provenance={"ref": payload.get("ref")},
    )


def _sanitize_agent_output(payload: Any) -> Tuple[Optional[Dict[str, Any]], bool]:
    if payload is None:
        return None, False
    truncated = {"flag": False}

    def walk(value: Any, depth: int) -> Any:
        if depth > 6:
            truncated["flag"] = True
            return None
        if isinstance(value, dict):
            out: Dict[str, Any] = {}
            for key, item in value.items():
                lowered = str(key).lower()
                if lowered in _DROP_OUTPUT_KEYS or lowered in _IDENTIFIER_KEYS:
                    truncated["flag"] = True
                    continue
                out[key] = walk(item, depth + 1)
            return out
        if isinstance(value, list):
            if len(value) > _LIST_CAP:
                truncated["flag"] = True
            return [walk(item, depth + 1) for item in value[:_LIST_CAP]]
        if isinstance(value, str) and len(value) > _STRING_CAP:
            truncated["flag"] = True
            return value[:_STRING_CAP] + "…"
        return value

    cleaned = walk(payload, 0)
    if not isinstance(cleaned, dict):
        cleaned = {"value": cleaned}
    return cleaned, truncated["flag"]


def _sanitize_ground_truth(payload: Any) -> Tuple[Optional[Dict[str, Any]], bool]:
    if not isinstance(payload, dict):
        return None, False
    truncated = False
    items = []
    for item in payload.get("items") or []:
        if not isinstance(item, dict):
            continue
        value = item.get("value")
        if isinstance(value, dict):
            value = {
                key: val
                for key, val in value.items()
                if str(key).lower() not in _IDENTIFIER_KEYS
            }
        source = item.get("source") or {}
        items.append(
            {
                "name": item.get("name"),
                "status": item.get("status"),
                "value": value,
                "source": {
                    "dataset": source.get("dataset"),
                    "table": source.get("source_table") or source.get("table"),
                    "field": source.get("field"),
                },
            }
        )
        if len(items) >= _LIST_CAP:
            truncated = True
            break
    result = {
        "kind": payload.get("kind"),
        "status": payload.get("status"),
        "item_count": payload.get("item_count") or payload.get("counts"),
        "notes": payload.get("notes"),
        "reason": payload.get("reason"),
        "items": items,
    }
    if payload.get("counts"):
        result["counts"] = payload.get("counts")
    return result, truncated


def _sanitize_evaluation(payload: Dict[str, Any]) -> Dict[str, Any]:
    errors = []
    for error in payload.get("errors") or []:
        if not isinstance(error, dict):
            continue
        errors.append(
            {
                "error_type": error.get("error_type"),
                "field": error.get("field"),
                "expected": error.get("expected"),
                "actual": error.get("actual"),
                "severity": error.get("severity"),
                "note": error.get("note"),
            }
        )
        if len(errors) >= _LIST_CAP:
            break
    return {
        "status": payload.get("status"),
        "evaluation_type": payload.get("evaluation_type"),
        "validator": payload.get("validator"),
        "metrics": payload.get("metrics"),
        "counts": payload.get("counts"),
        "errors": errors,
        "warnings": list(payload.get("warnings") or [])[:20],
        "reason": payload.get("reason"),
        "details": _public_details(payload.get("details") or {}),
    }


def _public_details(details: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {
        "gold_mention_instances",
        "gold_unique_concepts",
        "predicted_entity_instances",
        "predicted_unique_concepts",
        "unreachable_gold_types",
        "structural_coverage",
        "split",
        "agent_output_field",
        "reference_note",
        "matching_rules",
        "primary",
    }
    return {key: details[key] for key in allowed if key in details}


def _without_secrets(payload: Any) -> Any:
    if isinstance(payload, dict):
        out = {}
        for key, value in payload.items():
            lowered = str(key).lower()
            if any(token in lowered for token in ("key", "token", "secret", "password", "jwt")):
                continue
            out[key] = _without_secrets(value)
        return out
    if isinstance(payload, list):
        return [_without_secrets(item) for item in payload]
    return payload


def _inventory_table_count(inventory: Dict[str, Any], name: str) -> Optional[int]:
    for dataset in inventory.get("datasets") or []:
        if dataset.get("dataset") == name:
            return dataset.get("table_count")
    return None


def _inventory_document_count(inventory: Dict[str, Any]) -> Optional[int]:
    for dataset in inventory.get("datasets") or []:
        if "TAC" in str(dataset.get("dataset") or ""):
            return dataset.get("document_count") or dataset.get("file_count")
    return None


def _tasks_for_dataset(registry: List[Dict[str, Any]], needle: str) -> List[str]:
    found = []
    for task in registry:
        sources = " ".join(task.get("source_datasets") or [])
        if needle.lower() in sources.lower():
            found.append(task["task_id"])
    return found


def _evaluated_for_dataset(run_datasets: Dict[str, Any], needle: str) -> int:
    total = 0
    for name, entry in run_datasets.items():
        if needle.lower() in name.lower() and isinstance(entry, dict):
            total += int(entry.get("evaluated") or 0)
    return total


def _intake_entry_from_report(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task": row.get("task"),
        "agent": "intake",
        "status": row.get("status") or "NOT_EXECUTED",
        "sample": {
            "evaluated": int(row.get("evaluated_cases") or 0),
            "eligible_cases": int(row.get("eligible_cases") or row.get("total_cases") or 0),
        },
        "quality": _intake_quality_from_report(row),
    }


def _intake_quality_from_report(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    extras = {
        item.get("key"): item.get("value")
        for item in (row.get("display_metrics") or [])
        if isinstance(item, dict) and item.get("key")
    }
    if (
        row.get("f1_score") is None
        and row.get("precision") is None
        and row.get("accuracy") is None
        and not extras
    ):
        return None
    quality: Dict[str, Any] = {}
    if row.get("f1_score") is not None or row.get("precision") is not None:
        quality["micro"] = {
            "precision": row.get("precision"),
            "recall": row.get("recall"),
            "f1": row.get("f1_score"),
        }
    if row.get("accuracy") is not None or extras.get("accuracy") is not None:
        quality["structured_fields"] = {
            "field_accuracy": row.get("accuracy") if row.get("accuracy") is not None else extras.get("accuracy"),
            "exact_match_rate": extras.get("exact_match_rate"),
        }
    if extras.get("entity_f1") is not None:
        quality["entities"] = {
            "precision": extras.get("entity_precision"),
            "recall": extras.get("entity_recall"),
            "f1": extras.get("entity_f1"),
        }
    if extras.get("relation_f1") is not None:
        quality["relations"] = {
            "precision": extras.get("relation_precision"),
            "recall": extras.get("relation_recall"),
            "f1": extras.get("relation_f1"),
        }
    if extras.get("cer") is not None or extras.get("wer") is not None:
        quality["ocr"] = {"cer": extras.get("cer"), "wer": extras.get("wer")}
    return quality or None


def _diagnosis_quality_from_report(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    extras = {
        item.get("key"): item.get("value")
        for item in (row.get("display_metrics") or [])
        if isinstance(item, dict) and item.get("key")
    }
    metrics = {
        "accuracy": row.get("accuracy"),
        "precision": row.get("precision"),
        "recall": row.get("recall"),
        "f1_score": row.get("f1_score"),
        **extras,
    }
    if all(metrics.get(key) is None for key in ("top_1_accuracy", "f1_score", "accuracy", "precision")):
        if extras.get("top_1_accuracy") is None and extras.get("f1_score") is None:
            return None
    quality: Dict[str, Any] = {}
    top1 = extras.get("top_1_accuracy")
    if top1 is not None:
        quality["ranking"] = {
            "hit_rate_at_1": top1,
            "hit_rate_at_5": extras.get("top_k_accuracy"),
            "ndcg_at_5": extras.get("ndcg_at_5"),
        }
    if extras.get("f1_score") is not None or row.get("f1_score") is not None:
        f1 = extras.get("f1_score") if extras.get("f1_score") is not None else row.get("f1_score")
        quality["classification"] = {
            "accuracy": extras.get("accuracy") if extras.get("accuracy") is not None else row.get("accuracy"),
            "macro": {"f1": f1, "precision": row.get("precision"), "recall": row.get("recall")},
        }
    if row.get("f1_score") is not None or row.get("precision") is not None:
        quality.setdefault(
            "micro",
            {
                "precision": row.get("precision"),
                "recall": row.get("recall"),
                "f1": row.get("f1_score"),
            },
        )
    return quality or None


def _research_quality_from_report(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    extras = {
        item.get("key"): item.get("value")
        for item in (row.get("display_metrics") or [])
        if isinstance(item, dict) and item.get("key")
    }
    if extras.get("ndcg_at_5") is None and extras.get("mrr") is None:
        return None
    return {
        "ranking": {
            "ndcg_at_5": extras.get("ndcg_at_5"),
            "mrr": extras.get("mrr"),
            "precision_at_1": extras.get("precision_at_1"),
            "recall_at_5": extras.get("recall_at_5"),
            "hit_rate_at_1": extras.get("hit_rate_at_1"),
        }
    }


def _prescription_quality_from_report(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    metrics = row if isinstance(row, dict) else {}
    field_accuracy = metrics.get("field_accuracy")
    if field_accuracy is not None:
        return {
            "structured_fields": {
                "field_accuracy": field_accuracy,
                "missing_field_rate": metrics.get("missing_field_rate"),
            }
        }
    recall = metrics.get("recall")
    if recall is not None:
        return {
            "micro": {
                "recall": recall,
                "precision": metrics.get("precision"),
            }
        }
    extras = {
        item.get("key"): item.get("value")
        for item in (metrics.get("display_metrics") or [])
        if isinstance(item, dict) and item.get("key")
    }
    if extras.get("field_accuracy") is not None:
        return {
            "structured_fields": {
                "field_accuracy": extras.get("field_accuracy"),
                "missing_field_rate": extras.get("missing_field_rate"),
            }
        }
    if extras.get("recall") is not None:
        return {"micro": {"recall": extras.get("recall"), "precision": extras.get("precision")}}
    return None


def _medical_report_quality_from_report(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    metrics = row if isinstance(row, dict) else {}
    recall = metrics.get("recall")
    if recall is not None:
        return {
            "micro": {
                "recall": recall,
                "precision": metrics.get("precision"),
                "f1": metrics.get("f1"),
            }
        }
    extras = {
        item.get("key"): item.get("value")
        for item in (metrics.get("display_metrics") or [])
        if isinstance(item, dict) and item.get("key")
    }
    if extras.get("recall") is not None:
        return {
            "micro": {
                "recall": extras.get("recall"),
                "precision": extras.get("precision"),
                "f1": extras.get("f1"),
            }
        }
    return None


validation_service = ValidationService()
