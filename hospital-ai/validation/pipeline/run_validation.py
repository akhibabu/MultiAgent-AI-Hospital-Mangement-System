"""
Controlled validation runner.

Executes the existing production agents against sealed validation cases and
records what they produced and how. It computes no metrics and reaches no
verdict: scoring joins these raw results against the ground truth in a later
step, which is the only place the answer key is ever opened.

    python validation/pipeline/run_validation.py --dry-run
    python validation/pipeline/run_validation.py --agent intake
    python validation/pipeline/run_validation.py --task intake_medical_entity_recognition
    python validation/pipeline/run_validation.py --case VC-intake_medical_entity_recognition-00001
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rate_limit.backoff import backoff_seconds
from rate_limit.limits import load_provider_limits, output_budget_for
from rate_limit.parse_retry import retry_after_from_exception
from rate_limit.scheduler import TokenAwareScheduler
from rate_limit.token_estimator import TokenEstimator

PIPELINE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PIPELINE_DIR.parents[1]
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))

from case_loader import (  # noqa: E402
    AgentInput,
    InputNotSupported,
    SealedCase,
    assert_payload_clean,
    iter_case_files,
    load_case,
)
from diagnosis_catalog import (  # noqa: E402
    DIAGNOSIS_TASK_IDS,
    is_diagnosis_agent,
    resolve_diagnosis_task,
    resolve_diagnosis_tasks,
)
from intake_catalog import (  # noqa: E402
    INTAKE_TASK_IDS,
    is_intake_agent,
    resolve_intake_task,
    resolve_intake_tasks,
)
from research_catalog import (  # noqa: E402
    RESEARCH_TASK_IDS,
    is_research_agent,
    resolve_research_task,
    resolve_research_tasks,
)
from prescription_catalog import (  # noqa: E402
    PRESCRIPTION_TASK_IDS,
    is_prescription_agent,
    resolve_prescription_task,
    resolve_prescription_tasks,
)
from medical_report_catalog import (  # noqa: E402
    MEDICAL_REPORT_TASK_IDS,
    is_medical_report_agent,
    resolve_medical_report_task,
    resolve_medical_report_tasks,
)
from results import (  # noqa: E402
    ExecutionStatus,
    ExecutionTelemetry,
    RETRYABLE_STATUSES,
    RunWriter,
    allocate_run_id,
    build_result,
    classify,
    git_commit,
    now_iso,
    redact,
)

CASES_ROOT = PROJECT_ROOT / "validation" / "ground_truth" / "cases"
TASK_REGISTRY = PROJECT_ROOT / "validation" / "task_registry.json"
CONFIG_PATH = PROJECT_ROOT / "validation" / "config.yaml"
RUN_CONFIG_PATH = PIPELINE_DIR / "run_config.json"

logger = logging.getLogger("validation.run")


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------


@dataclass
class CaseSelection:
    """Eligible cases this run will execute, plus those left PENDING or ineligible."""

    selected: List[Any]
    pending: List[Any] = field(default_factory=list)
    already_successful: List[Any] = field(default_factory=list)
    ineligible: List[Tuple[Any, str, str]] = field(default_factory=list)
    dataset_count: int = 0
    eligible_count: int = 0
    already_evaluated: int = 0
    pending_total: int = 0


@dataclass
class RunSettings:
    run_name: str = "baseline"
    agents: List[str] = None  # type: ignore[assignment]
    tasks: List[str] = None  # type: ignore[assignment]
    cases: List[str] = None  # type: ignore[assignment]
    max_cases: Optional[int] = 50
    max_cases_per_task: Optional[int] = None
    concurrency: int = 2
    retry_attempts: int = 2
    retry_base_delay_ms: int = 2000
    timeout_seconds: int = 300
    delay_between_requests_ms: int = 500
    random_seed: int = 20240617
    provider: Optional[str] = None
    output_directory: str = "validation/results/raw"
    block_supabase: bool = True
    allow_stub_provider: bool = True
    env_overlay: Optional[str] = None
    run_id: Optional[str] = None
    resume: bool = False
    retry_failed: bool = False
    rate_limit_safe: bool = False
    max_output_tokens: Optional[int] = None
    model: Optional[str] = None
    execution_type: Optional[str] = None

    def __post_init__(self) -> None:
        self.agents = self.agents or []
        self.tasks = self.tasks or []
        self.cases = self.cases or []


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_settings(args: argparse.Namespace) -> RunSettings:
    """Merge config.yaml, run_config.json and CLI flags, in that priority."""
    config = _load_yaml(Path(args.config))
    limits = config.get("validation", {}) or {}
    safety = config.get("safety", {}) or {}
    environment = config.get("environment", {}) or {}

    run_config: Dict[str, Any] = {}
    run_config_path = Path(args.run_config)
    if run_config_path.exists():
        run_config = json.loads(run_config_path.read_text(encoding="utf-8"))

    selection = run_config.get("selection", {}) or {}
    rc_limits = run_config.get("limits", {}) or {}
    rc_execution = run_config.get("execution", {}) or {}
    rc_provider = run_config.get("provider", {}) or {}
    rc_output = run_config.get("output", {}) or {}
    rc_safety = run_config.get("safety", {}) or {}

    def pick(cli: Any, run_value: Any, base: Any) -> Any:
        if cli is not None:
            return cli
        if run_value is not None:
            return run_value
        return base

    settings = RunSettings(
        run_name=pick(args.run_name, run_config.get("run_name"), "baseline"),
        agents=[args.agent] if args.agent else list(selection.get("agents") or []),
        tasks=_normalize_task_filter(
            args.task,
            selection.get("tasks") or [],
            agent=args.agent,
        ),
        cases=list(args.case or []) or list(selection.get("cases") or []),
        max_cases=_resolve_max_cases(args, rc_limits, limits),
        max_cases_per_task=pick(
            args.max_cases_per_task, rc_limits.get("max_cases_per_task"), None
        ),
        concurrency=int(
            pick(args.concurrency, rc_execution.get("concurrency"), limits.get("concurrency", 2))
        ),
        retry_attempts=int(
            pick(
                args.retry_attempts,
                rc_execution.get("retry_attempts"),
                _env_int("VALIDATION_MAX_RETRIES")
                if _env_int("VALIDATION_MAX_RETRIES") is not None
                else limits.get("retry_attempts", 2),
            )
        ),
        retry_base_delay_ms=_retry_delay_ms(args, limits),
        timeout_seconds=int(
            pick(
                args.timeout_seconds,
                rc_execution.get("timeout_seconds"),
                limits.get("timeout_seconds", 300),
            )
        ),
        delay_between_requests_ms=int(
            pick(
                args.delay_ms,
                rc_execution.get("delay_between_requests_ms"),
                limits.get("delay_between_requests_ms", 500),
            )
        ),
        random_seed=int(
            pick(args.seed, rc_execution.get("random_seed"), limits.get("random_seed", 20240617))
        ),
        provider=pick(args.provider, rc_provider.get("ai_provider"), None),
        output_directory=str(
            pick(args.output, rc_output.get("directory"), "validation/results/raw")
        ),
        block_supabase=bool(
            rc_safety.get("block_supabase", safety.get("block_supabase", True))
        ),
        allow_stub_provider=bool(
            args.allow_stub or rc_safety.get("allow_stub_provider", True)
        ),
        env_overlay=environment.get("overlay_env_file"),
        run_id=getattr(args, "run_id", None),
        resume=bool(getattr(args, "resume", False)),
        retry_failed=bool(getattr(args, "retry_failed", False)),
        rate_limit_safe=bool(getattr(args, "rate_limit_safe", False)),
        max_output_tokens=getattr(args, "max_output_tokens", None),
        model=getattr(args, "model", None),
        execution_type=_normalize_execution_type(getattr(args, "execution_type", None)),
    )
    if settings.rate_limit_safe and args.concurrency is None:
        settings.concurrency = min(settings.concurrency, 1)
    return settings


def _normalize_task_filter(
    cli_task: Optional[str],
    configured: Any,
    *,
    agent: Optional[str] = None,
) -> List[str]:
    """`--task ALL` means every registry task, not a literal task_id."""
    if cli_task and str(cli_task).strip().upper() in {"ALL", "*"}:
        if is_intake_agent(agent):
            return list(INTAKE_TASK_IDS)
        if is_diagnosis_agent(agent):
            return list(DIAGNOSIS_TASK_IDS)
        if is_research_agent(agent):
            return list(RESEARCH_TASK_IDS)
        if is_prescription_agent(agent):
            return list(PRESCRIPTION_TASK_IDS)
        return []
    if cli_task:
        if is_intake_agent(agent):
            resolved = resolve_intake_task(cli_task)
            if resolved == "ALL":
                return list(INTAKE_TASK_IDS)
            return [resolved]
        if is_diagnosis_agent(agent):
            resolved = resolve_diagnosis_task(cli_task)
            if resolved == "ALL":
                return list(DIAGNOSIS_TASK_IDS)
            return [resolved]
        if is_research_agent(agent):
            resolved = resolve_research_task(cli_task)
            if resolved == "ALL":
                return list(RESEARCH_TASK_IDS)
            return [resolved]
        if is_prescription_agent(agent):
            resolved = resolve_prescription_task(cli_task)
            if resolved == "ALL":
                return list(PRESCRIPTION_TASK_IDS)
            return [resolved]
        return [cli_task]
    configured_tasks = [
        str(item)
        for item in (configured or [])
        if str(item).strip().upper() not in {"ALL", "*"}
    ]
    if is_intake_agent(agent) and configured_tasks:
        return resolve_intake_tasks(configured_tasks)
    if is_diagnosis_agent(agent) and configured_tasks:
        return resolve_diagnosis_tasks(configured_tasks)
    if is_research_agent(agent) and configured_tasks:
        return resolve_research_tasks(configured_tasks)
    if is_prescription_agent(agent) and configured_tasks:
        return resolve_prescription_tasks(configured_tasks)
    return configured_tasks


def _resolve_max_cases(
    args: argparse.Namespace,
    rc_limits: Dict[str, Any],
    limits: Dict[str, Any],
) -> Optional[int]:
    """
    Intake without an explicit --max-cases runs every eligible Intake case.

    Other agents keep the configured default. Passing --max-cases 3 still
    caps an Intake run for tests.
    """
    if is_intake_agent(getattr(args, "agent", None)) and getattr(args, "max_cases", None) is None:
        return None
    if is_diagnosis_agent(getattr(args, "agent", None)) and getattr(args, "max_cases", None) is None:
        return None
    if is_research_agent(getattr(args, "agent", None)) and getattr(args, "max_cases", None) is None:
        return None
    if is_prescription_agent(getattr(args, "agent", None)) and getattr(args, "max_cases", None) is None:
        return None
    raw = args.max_cases
    if raw is None:
        raw = rc_limits.get("max_cases")
    if raw is None:
        raw = limits.get("max_cases", 50)
    return int(raw) if raw is not None else None


def _normalize_execution_type(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = str(value).strip().upper()
    if cleaned in {"ALL", "*"}:
        return None
    if cleaned not in {"ALGORITHM", "ML", "LLM", "HYBRID"}:
        raise SystemExit(
            f"Unsupported --execution-type {value!r}. Use ALGORITHM, ML, LLM, HYBRID, or ALL."
        )
    return cleaned


def _env_int(name: str) -> Optional[int]:
    import os

    raw = os.environ.get(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _retry_delay_ms(args: argparse.Namespace, limits: Dict[str, Any]) -> int:
    if getattr(args, "retry_delay", None) is not None:
        value = float(args.retry_delay)
        return int(value * 1000) if value <= 120 else int(value)
    return int(limits.get("retry_base_delay_ms", 2000))


# --------------------------------------------------------------------------
# Case selection
# --------------------------------------------------------------------------


def load_registry() -> Dict[str, Dict[str, Any]]:
    registry = json.loads(TASK_REGISTRY.read_text(encoding="utf-8"))
    return {entry["task_id"]: entry for entry in registry.get("tasks", [])}


def _load_task_strategy() -> Dict[str, Dict[str, Any]]:
    path = PROJECT_ROOT / "validation" / "config" / "task_strategy.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(key): dict(value) for key, value in (payload.get("tasks") or {}).items()}


@dataclass(frozen=True)
class TaskLevelSkip:
    """
    Stands in for a case on tasks that have none.

    Tasks ruled out at the framework level never had cases generated, so
    without this a run would silently say nothing about them. Emitting one
    record per such task makes the refusal explicit and auditable instead of
    leaving a reader to infer it from an absence.
    """

    validation_case_id: str
    agent: str
    task: str
    task_id: str
    source: Dict[str, Any]
    category: List[str]
    ground_truth_available: bool = False
    ground_truth_status: Optional[str] = "NOT_AVAILABLE"
    quantitative: bool = False
    validation_patient_ref: Optional[str] = None
    case_path: Path = TASK_REGISTRY


def unsupported_task_records(
    registry: Dict[str, Dict[str, Any]],
    settings: RunSettings,
    covered: set,
) -> List[Tuple[TaskLevelSkip, str, str]]:
    """One NOT_SUPPORTED record per ruled-out task that produced no cases."""
    wanted_agents = {a.strip().lower() for a in settings.agents if a.strip()}
    wanted_tasks = {t.strip() for t in settings.tasks if t.strip()}
    wanted_execution = (settings.execution_type or "").strip().upper()
    strategy_map = _load_task_strategy()

    records: List[Tuple[TaskLevelSkip, str, str]] = []
    for task_id, entry in sorted(registry.items()):
        if entry.get("status") != "NOT_SUPPORTED" or task_id in covered:
            continue
        if settings.cases:
            continue
        if wanted_execution:
            task_type = str((strategy_map.get(task_id) or {}).get("execution_type") or "").upper()
            if task_type != wanted_execution:
                continue
        if wanted_tasks and task_id not in wanted_tasks:
            continue
        if wanted_agents and agent_key(str(entry.get("agent", ""))) not in wanted_agents:
            continue
        records.append(
            (
                TaskLevelSkip(
                    validation_case_id=f"NO-CASES-{task_id}",
                    agent=str(entry.get("agent") or ""),
                    task=str(entry.get("task") or ""),
                    task_id=task_id,
                    source={"dataset": "none", "split": None},
                    category=list(entry.get("source_datasets") or []),
                ),
                ExecutionStatus.NOT_SUPPORTED,
                str(
                    entry.get("eligibility_reason")
                    or "No suitable validation input or ground truth exists."
                ),
            )
        )
    return records


def agent_key(agent_label: str) -> str:
    return agent_label.replace(" Agent", "").strip().lower().replace(" ", "_")


def select_pending(
    ordered: List[Any],
    *,
    completed_keys: Optional[set] = None,
    ineligible_status: Optional[Dict[str, Tuple[str, str]]] = None,
    max_cases: Optional[int] = None,
    max_cases_per_task: Optional[int] = None,
) -> CaseSelection:
    """
    Filter to pending candidates, then apply --max-cases.

    completed_keys: (case_id, task_id) pairs that already have SUCCESS.
    ineligible_status: task_id -> (status, reason) for genuine skips.
    """
    completed_keys = completed_keys or set()
    ineligible_status = ineligible_status or {}

    already_successful: List[Any] = []
    pending_candidates: List[Any] = []
    ineligible: List[Tuple[Any, str, str]] = []

    for case in ordered:
        task_id = getattr(case, "task_id", "")
        if task_id in ineligible_status:
            status, reason = ineligible_status[task_id]
            ineligible.append((case, status, reason))
            continue
        key = (getattr(case, "validation_case_id", ""), task_id)
        if key in completed_keys:
            already_successful.append(case)
            continue
        pending_candidates.append(case)

    selected, leftover = apply_max_cases(
        pending_candidates,
        max_cases=max_cases,
        max_cases_per_task=max_cases_per_task,
    )
    eligible_count = len(already_successful) + len(pending_candidates)
    return CaseSelection(
        selected=selected,
        pending=leftover,
        already_successful=already_successful,
        ineligible=ineligible,
        dataset_count=len(ordered),
        eligible_count=eligible_count,
        already_evaluated=len(already_successful),
        pending_total=len(pending_candidates),
    )


def apply_max_cases(
    pending_candidates: List[Any],
    *,
    max_cases: Optional[int],
    max_cases_per_task: Optional[int],
) -> Tuple[List[Any], List[Any]]:
    """Cap applies only to pending candidates, never to already-successful cases."""
    selected: List[Any] = []
    leftover: List[Any] = []
    per_task_counts: Dict[str, int] = {}
    ceiling = max_cases if max_cases is not None else len(pending_candidates)
    for case in pending_candidates:
        task_id = getattr(case, "task_id", "")
        if max_cases_per_task is not None and per_task_counts.get(task_id, 0) >= int(
            max_cases_per_task
        ):
            leftover.append(case)
            continue
        if len(selected) >= ceiling:
            leftover.append(case)
            continue
        per_task_counts[task_id] = per_task_counts.get(task_id, 0) + 1
        selected.append(case)
    return selected, leftover


def select_cases(
    settings: RunSettings,
    registry: Dict[str, Dict[str, Any]],
    completed_keys: Optional[set] = None,
) -> CaseSelection:
    """
    Choose pending cases to run this time.

    --max-cases limits pending/unevaluated cases only. Already-successful
    cases are removed before the cap is applied. Leftovers stay PENDING.
    SKIPPED is reserved for genuine ineligibility.
    """
    wanted_agents = {a.strip().lower() for a in settings.agents if a.strip()}
    wanted_tasks = {t.strip() for t in settings.tasks if t.strip()}
    wanted_cases = {c.strip() for c in settings.cases if c.strip()}
    wanted_execution = (settings.execution_type or "").strip().upper()
    strategy_map = _load_task_strategy()

    rng = random.Random(settings.random_seed)

    all_cases: List[SealedCase] = []
    for path in iter_case_files(CASES_ROOT):
        case = load_case(path)
        if wanted_cases and case.validation_case_id not in wanted_cases:
            continue
        if wanted_tasks and case.task_id not in wanted_tasks:
            continue
        if wanted_agents and agent_key(case.agent) not in wanted_agents:
            continue
        if wanted_execution:
            task_type = str(
                (strategy_map.get(case.task_id) or {}).get("execution_type") or ""
            ).upper()
            if task_type != wanted_execution:
                continue
        all_cases.append(case)

    by_task: Dict[str, List[SealedCase]] = {}
    for case in sorted(all_cases, key=lambda c: c.validation_case_id):
        by_task.setdefault(case.task_id, []).append(case)

    ordered: List[SealedCase] = []
    for task_id in sorted(by_task):
        bucket = list(by_task[task_id])
        rng.shuffle(bucket)
        ordered.extend(bucket)

    ineligible_status: Dict[str, Tuple[str, str]] = {}
    for case in ordered:
        entry = registry.get(case.task_id, {})
        status = str(entry.get("status") or case.task_status)
        if status == "NOT_SUPPORTED" and case.task_id not in ineligible_status:
            ineligible_status[case.task_id] = (
                ExecutionStatus.NOT_SUPPORTED,
                str(
                    entry.get("eligibility_reason")
                    or "Task registry marks this task NOT_SUPPORTED: no suitable "
                    "validation input or ground truth exists."
                ),
            )

    selection = select_pending(
        ordered,
        completed_keys=completed_keys,
        ineligible_status=ineligible_status,
        max_cases=settings.max_cases,
        max_cases_per_task=settings.max_cases_per_task,
    )
    selection.dataset_count = len(all_cases)
    return selection


# --------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------


class Pacer:
    """Spaces request starts so a run does not burst against provider limits."""

    def __init__(self, delay_ms: int) -> None:
        self._delay = max(delay_ms, 0) / 1000.0
        self._lock = threading.Lock()
        self._next_slot = 0.0

    def wait(self) -> None:
        if self._delay <= 0:
            return
        with self._lock:
            now = time.monotonic()
            slot = max(now, self._next_slot)
            self._next_slot = slot + self._delay
        remaining = slot - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)


def execute_case(
    case: SealedCase,
    *,
    settings: RunSettings,
    runtime: Any,
    run_id: str,
    commit: Optional[str],
    pacer: Pacer,
    scheduler: Optional[TokenAwareScheduler] = None,
    stop_event: Optional[threading.Event] = None,
    configured_provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Run one case, with retries, and return a schema-conformant result."""
    from adapters import adapter_for_task
    from backend_bridge import recorder

    started = now_iso()
    clock = time.perf_counter()

    adapter = adapter_for_task(case.task_id)
    if adapter is None:
        return build_result(
            run_id=run_id,
            case=case,
            status=ExecutionStatus.INPUT_NOT_SUPPORTED,
            telemetry=ExecutionTelemetry(started, now_iso(), 0),
            error={
                "type": "no_adapter",
                "message": f"No adapter is registered for task {case.task_id}.",
                "reason": "unmapped task",
            },
            commit=commit,
            random_seed=settings.random_seed,
        )

    agent_input: Optional[AgentInput] = None
    calls: List[Dict[str, Any]] = []
    status = ExecutionStatus.UNKNOWN_ERROR
    output: Any = None
    error: Optional[Dict[str, Any]] = None
    attempt = 0

    try:
        agent_input = adapter.build_input(case, runtime)
        # Last line of defence before anything reaches an agent.
        assert_payload_clean(agent_input.payload, case.validation_case_id)
    except Exception as exc:  # noqa: BLE001
        status = classify(exc)
        error = {
            "type": type(exc).__name__,
            "message": redact(exc),
            "reason": redact(getattr(exc, "reason", None)) if hasattr(exc, "reason") else None,
            "stage": "adapter_input",
            "retryable": False,
        }
        duration = int((time.perf_counter() - clock) * 1000)
        return build_result(
            run_id=run_id,
            case=case,
            status=status,
            telemetry=ExecutionTelemetry(started, now_iso(), duration),
            error=error,
            adapter=adapter.__class__.__name__,
            commit=commit,
            random_seed=settings.random_seed,
        )

    estimate = TokenEstimator().estimate_request(
        payload=agent_input.payload if agent_input else None,
        expected_output_tokens=output_budget_for(case.task_id, settings.max_output_tokens),
    )
    provider_name = (configured_provider or "groq").lower()
    rate_limit_hits = 0
    strategy = _load_task_strategy().get(case.task_id) or {}
    uses_provider = bool(strategy.get("api_required"))

    for attempt in range(1, settings.retry_attempts + 2):
        if stop_event is not None and stop_event.is_set():
            if status == ExecutionStatus.UNKNOWN_ERROR and output is None:
                return {}
            break
        if scheduler is not None and uses_provider:
            logger.info(
                "REQUEST_SCHEDULED case=%s estimated_tokens=%s provider=%s",
                case.validation_case_id,
                estimate["estimated_total_tokens"],
                provider_name,
            )
            slot = scheduler.wait_for_slot(
                provider=provider_name,
                estimated_tokens=estimate["estimated_total_tokens"],
            )
            if slot.get("stopped"):
                if status == ExecutionStatus.UNKNOWN_ERROR and output is None:
                    return {}
                break
        pacer.wait()
        captured: List[Dict[str, Any]] = []

        def _work() -> Any:
            with recorder.capture() as recorded:
                try:
                    return adapter.execute(case, agent_input, runtime)
                finally:
                    captured.extend(call.as_dict() for call in recorded)

        logger.info(
            "start case=%s task=%s agent=%s attempt=%d",
            case.validation_case_id,
            case.task_id,
            agent_key(case.agent),
            attempt,
        )
        try:
            # A dedicated worker lets the timeout measure execution time only,
            # never time spent queued behind other cases.
            with ThreadPoolExecutor(max_workers=1) as inner:
                future = inner.submit(_work)
                try:
                    output = future.result(timeout=settings.timeout_seconds)
                except FutureTimeout as exc:
                    # The orphaned thread finishes in the background; the
                    # orchestrator's own timeouts bound how long that lasts.
                    raise TimeoutError(
                        f"Agent execution exceeded {settings.timeout_seconds}s"
                    ) from exc
            status = ExecutionStatus.SUCCESS
            error = None
            calls = captured
            actual = _actual_tokens(captured)
            if scheduler is not None and uses_provider:
                scheduler.release(
                    provider=_actual_provider(captured, provider_name),
                    estimated_tokens=estimate["estimated_total_tokens"],
                    actual_tokens=actual,
                    success=True,
                    latency_ms=(time.perf_counter() - clock) * 1000,
                    fallback=_fallback_used(captured),
                )
            break
        except Exception as exc:  # noqa: BLE001
            calls = captured
            status = classify(exc)
            retry_after = retry_after_from_exception(exc)
            if status == ExecutionStatus.RATE_LIMITED:
                rate_limit_hits += 1
            error = {
                "type": type(exc).__name__,
                "message": redact(exc),
                "reason": redact(getattr(exc, "reason", None))
                if hasattr(exc, "reason")
                else None,
                "stage": "agent_execution",
                "retryable": status in RETRYABLE_STATUSES,
                "code": status,
            }
            logger.warning(
                "fail case=%s attempt=%d status=%s: %s",
                case.validation_case_id,
                attempt,
                status,
                redact(exc),
            )
            if scheduler is not None and uses_provider:
                scheduler.release(
                    provider=provider_name,
                    estimated_tokens=estimate["estimated_total_tokens"],
                    rate_limited=status == ExecutionStatus.RATE_LIMITED,
                    retry_after=retry_after,
                    success=False,
                    fallback=_fallback_used(captured),
                )
            if status not in RETRYABLE_STATUSES or attempt > settings.retry_attempts:
                # Rate-limit / all-providers-exhausted stay resumable. Never SKIPPED.
                if status == ExecutionStatus.RATE_LIMITED:
                    error["code"] = ExecutionStatus.RATE_LIMITED
                elif status == ExecutionStatus.PROVIDER_ERROR:
                    message = str(error.get("message") or "").lower()
                    if any(
                        token in message
                        for token in ("rate limit", "429", "quota", "too many", "timeout")
                    ):
                        status = ExecutionStatus.RATE_LIMITED
                    else:
                        status = ExecutionStatus.FAILED
                    error["code"] = status
                break
            delay = backoff_seconds(
                attempt,
                base_delay_ms=settings.retry_base_delay_ms,
                retry_after=retry_after,
            )
            time.sleep(delay)

    duration = int((time.perf_counter() - clock) * 1000)
    strategy = _load_task_strategy().get(case.task_id) or {}
    execution_type = str(strategy.get("execution_type") or "").upper() or None
    telemetry = ExecutionTelemetry(
        started,
        now_iso(),
        duration,
        attempt,
        calls,
        estimated_input_tokens=estimate["estimated_input_tokens"],
        estimated_output_tokens=estimate["estimated_output_tokens"],
        estimated_total_tokens=estimate["estimated_total_tokens"],
        rate_limit_count=rate_limit_hits,
        configured_provider=configured_provider,
        retry_count=max(attempt - 1, 0),
        execution_type=execution_type,
        api_call=bool(calls),
    )

    logger.info(
        "done case=%s status=%s provider=%s duration_ms=%d calls=%d",
        case.validation_case_id,
        status,
        telemetry.as_dict().get("provider"),
        duration,
        len(calls),
    )

    return build_result(
        run_id=run_id,
        case=case,
        status=status,
        telemetry=telemetry,
        agent_output=output,
        error=error,
        adapter=adapter.__class__.__name__,
        entry_point=agent_input.entry_point if agent_input else None,
        input_digest=agent_input.digest() if agent_input else None,
        adapter_notes=agent_input.notes if agent_input else None,
        random_seed=settings.random_seed,
        commit=commit,
    )


def _actual_tokens(calls: List[Dict[str, Any]]) -> Optional[int]:
    values = [
        (call.get("prompt_tokens") or 0) + (call.get("completion_tokens") or 0)
        for call in calls
        if call.get("prompt_tokens") is not None or call.get("completion_tokens") is not None
    ]
    return sum(values) if values else None


def _actual_provider(calls: List[Dict[str, Any]], default: str) -> str:
    for call in reversed(calls):
        if call.get("provider"):
            return str(call["provider"])
    return default


def _fallback_used(calls: List[Dict[str, Any]]) -> bool:
    return any(call.get("fallback_used") for call in calls)


# --------------------------------------------------------------------------
# Dry run
# --------------------------------------------------------------------------


def dry_run(
    settings: RunSettings,
    selection: CaseSelection,
    registry: Dict[str, Dict[str, Any]],
    already_evaluated: int = 0,
    success_keys: Optional[set] = None,
) -> int:
    """Prove the plan resolves without calling a provider."""
    from adapters import adapter_for_task

    print("\nDRY RUN — no LLM call will be made\n" + "=" * 64)

    selected = selection.selected
    by_task: Dict[str, List[SealedCase]] = {}
    for case in selected:
        by_task.setdefault(case.task_id, []).append(case)

    problems = 0
    for task_id in sorted(by_task):
        cases = by_task[task_id]
        sample = cases[0]
        entry = registry.get(task_id, {})
        adapter = adapter_for_task(task_id)

        print(f"\nAgent:          {sample.agent}")
        print(f"Task:           {sample.task}  ({task_id})")
        print(f"Registry:       {entry.get('status', 'UNKNOWN')}")
        print(f"Cases:          {len(cases)}")
        print(
            "Ground truth:   "
            f"{'Available' if sample.ground_truth_available else 'Not available'}"
            f" ({sample.ground_truth_status})"
        )
        print(f"Evaluation:     {sample.evaluation_type}")
        print(f"Adapter:        {adapter.__class__.__name__ if adapter else 'NONE'}")

        if adapter is None:
            print("Execution:      BLOCKED — no adapter registered")
            problems += 1
            continue

        entry_point = adapter.entry_points.get(task_id) or "(not executable)"
        print(f"Entry point:    {entry_point}")

        try:
            probe = adapter.build_input(sample, _dry_runtime())
            assert_payload_clean(probe.payload, sample.validation_case_id)
            print(f"Input:          OK  (digest {probe.digest()[:12]})")
            for note in probe.notes[:4]:
                print(f"                - {note}")
            print("Execution:      NOT STARTED")
        except InputNotSupported as exc:
            print(f"Input:          INPUT_NOT_SUPPORTED — {exc.reason}")
            print("Execution:      SKIPPED")
        except Exception as exc:  # noqa: BLE001
            print(f"Input:          ERROR — {type(exc).__name__}: {redact(exc)}")
            print("Execution:      BLOCKED")
            problems += 1

    ineligible_by_reason: Dict[str, int] = {}
    for _, status, reason in selection.ineligible:
        ineligible_by_reason[f"{status}: {reason}"] = (
            ineligible_by_reason.get(f"{status}: {reason}", 0) + 1
        )

    keys = success_keys or set()
    leaked = [
        case
        for case in selected
        if (case.validation_case_id, case.task_id) in keys
    ]
    if leaked:
        logger.warning(
            "selection leaked %d already-successful case(s); duplicate safety will drop them",
            len(leaked),
        )
    to_execute = len(selected) - len(leaked)
    pending = selection.pending_total if selection.pending_total else max(
        selection.eligible_count - already_evaluated, 0
    )
    print("\n" + "=" * 64)
    print("VALIDATION RUN (DRY RUN)")
    print("-" * 32)
    print(f"Dataset cases:       {selection.dataset_count}")
    print(f"Eligible:            {selection.eligible_count}")
    print(f"Already evaluated:   {already_evaluated}")
    print(f"Selected this run:   {len(selected)}")
    print(f"Pending:             {pending}")
    print(f"Skipped:             {len(selection.ineligible)}")
    print(f"Cases to execute:    {to_execute}")
    print(f"cases that would be scored this evaluation: {to_execute}")
    if selection.eligible_count:
        ds = already_evaluated / selection.eligible_count
        print(f"Dataset coverage:    {already_evaluated} / {selection.eligible_count} ({ds:.1%})")
    print("                     (dataset coverage before this run — not accuracy)")
    for reason, count in sorted(ineligible_by_reason.items(), key=lambda kv: -kv[1])[:8]:
        print(f"  skip_reason        {count:>5}  {reason[:96]}")
    print(f"Provider:            {settings.provider or 'configured provider chain'}")
    print("Execution:           NOT STARTED\n")
    _print_dry_run_estimates(settings, selected)
    print("NO EXTERNAL REQUESTS WERE MADE.\n")
    return 1 if problems else 0


def _print_dry_run_estimates(settings: RunSettings, selected: List[SealedCase]) -> None:
    """ESTIMATE only. Never presented as measured usage or guaranteed time."""
    from adapters import adapter_for_task

    config = _load_yaml(Path(CONFIG_PATH))
    limits = load_provider_limits(config)
    provider = (settings.provider or "groq").lower()
    limit = limits.get(provider) or next(iter(limits.values()))
    estimator = TokenEstimator()
    samples: List[int] = []
    for case in selected[: min(len(selected), 8)]:
        adapter = adapter_for_task(case.task_id)
        if adapter is None:
            continue
        try:
            probe = adapter.build_input(case, _dry_runtime())
            estimate = estimator.estimate_request(
                payload=probe.payload,
                expected_output_tokens=output_budget_for(
                    case.task_id, settings.max_output_tokens
                ),
            )
            samples.append(int(estimate["estimated_total_tokens"]))
        except Exception:  # noqa: BLE001
            continue
    if not samples:
        print("Token estimate:  unavailable (could not probe payloads)")
        return
    average = int(sum(samples) / len(samples))
    total = average * len(selected)
    usable = limit.usable_tpm
    minutes = total / usable if usable else None
    print("ESTIMATE")
    print(f"  records:                      {len(selected)}")
    print(f"  estimated average tokens:     {average}")
    print(f"  estimated total:              {total}")
    print(f"  provider:                     {limit.name}")
    print(f"  TPM limit:                    {limit.tpm_limit} ({limit.limit_source})")
    print(f"  usable TPM after safety:      {usable}")
    print(f"  configured concurrency:       {settings.concurrency}")
    print(
        f"  estimated minimum time:       ~{int(minutes)} min"
        if minutes is not None
        else "  estimated minimum time:       unavailable"
    )
    print("  (theoretical TPM lower bound — not a guaranteed duration)")


def _dry_runtime() -> Any:
    """A runtime whose context registry is a throwaway, for input probing."""
    from adapters.base import ExecutionRuntime
    from backend_bridge import ContextRegistry

    return ExecutionRuntime(context_registry=ContextRegistry())


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run controlled validation against the existing AI agents."
    )
    parser.add_argument("--agent", help="Limit to one agent, e.g. intake")
    parser.add_argument(
        "--task",
        help=(
            "Limit to one task_id, or ALL. With --agent intake, short names "
            "such as medical_entity_recognition are accepted."
        ),
    )
    parser.add_argument(
        "--execution-type",
        dest="execution_type",
        help="Limit to ALGORITHM, ML, LLM, HYBRID, or ALL",
    )
    parser.add_argument(
        "--case", action="append", help="Run a specific validation_case_id (repeatable)"
    )
    parser.add_argument("--run-name", dest="run_name")
    parser.add_argument("--run-id", dest="run_id", help="Reuse an existing VAL-RUN-* identifier")
    parser.add_argument("--max-cases", type=int)
    parser.add_argument("--max-cases-per-task", type=int)
    parser.add_argument("--concurrency", type=int)
    parser.add_argument("--retry-attempts", "--max-retries", dest="retry_attempts", type=int)
    parser.add_argument("--retry-delay", type=float, help="Base backoff in seconds")
    parser.add_argument("--timeout-seconds", type=int)
    parser.add_argument("--delay-ms", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--provider", help="Pin a provider instead of the configured chain")
    parser.add_argument("--model", help="Optional validation-only model override via environment")
    parser.add_argument("--max-output-tokens", dest="max_output_tokens", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="On resume, re-attempt failed cases only (never successful ones)",
    )
    parser.add_argument(
        "--rate-limit-safe",
        action="store_true",
        help="Conservative concurrency, token-aware scheduling, checkpoints",
    )
    parser.add_argument("--allow-stub", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--run-config", dest="run_config", default=str(RUN_CONFIG_PATH))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    )

    settings = load_settings(args)
    if settings.resume and not settings.run_id:
        logger.error("--resume requires --run-id")
        return 2
    registry = load_registry()

    from rate_limit.coverage import load_success_index

    success_index = load_success_index(PROJECT_ROOT / "validation" / "results" / "raw")
    completed_keys = set(success_index)
    intake_reevaluate = (
        is_intake_agent(settings.agents[0] if settings.agents else None)
        and not settings.resume
    )
    diagnosis_reevaluate = (
        is_diagnosis_agent(settings.agents[0] if settings.agents else None)
        and not settings.resume
    )
    if intake_reevaluate:
        # An Intake task-by-task run must attempt every eligible Intake case
        # unless the operator explicitly resumes a previous run.
        completed_keys = set()
    elif diagnosis_reevaluate and settings.tasks:
        # Re-score Diagnosis tasks after agent/validator fixes without touching
        # Intake success records or unrelated Diagnosis tasks in the same run.
        wanted_tasks = set(settings.tasks)
        completed_keys = {
            key for key in completed_keys if key[1] not in wanted_tasks
        }
    selection = select_cases(settings, registry, completed_keys=completed_keys)
    selected = selection.selected
    already_evaluated = selection.already_evaluated

    covered = {case.task_id for case, _, _ in selection.ineligible} | {
        c.task_id for c in selected
    } | {c.task_id for c in selection.pending} | {
        c.task_id for c in selection.already_successful
    }
    selection.ineligible.extend(unsupported_task_records(registry, settings, covered))

    if (
        not selected
        and not selection.pending
        and not selection.already_successful
        and not selection.ineligible
    ):
        logger.error("No validation cases matched the given filters")
        return 2

    if settings.model:
        import os as _os

        for key in (
            "INTAKE_MODEL",
            "DIAGNOSIS_MODEL",
            "RESEARCH_MODEL",
            "PRESCRIPTION_MODEL",
            "REPORT_MODEL",
            "GROQ_MODEL",
        ):
            _os.environ[key] = settings.model

    if args.dry_run:
        # Adapters import backend models, so the backend still has to be
        # importable. No orchestrator is seeded and no provider is contacted.
        from backend_bridge import bootstrap

        bootstrap(
            provider_override=settings.provider,
            env_overlay=PROJECT_ROOT / settings.env_overlay
            if settings.env_overlay
            else None,
        )
        return dry_run(
            settings,
            selection,
            registry,
            already_evaluated=already_evaluated,
            success_keys=set(success_index),
        )

    from adapters.base import ExecutionRuntime
    from backend_bridge import (
        ContextRegistry,
        bootstrap,
        guard,
        install_supabase_guard,
        provider_chain,
        seed_orchestrator,
    )

    bootstrap(
        provider_override=settings.provider,
        env_overlay=PROJECT_ROOT / settings.env_overlay if settings.env_overlay else None,
    )

    import os

    active_provider = os.environ.get("AI_PROVIDER", "")
    if active_provider == "stub" and not settings.allow_stub_provider:
        logger.error(
            "AI_PROVIDER=stub would produce canned responses, not a measurement. "
            "Pass --allow-stub to run anyway."
        )
        return 2

    registry_of_contexts = ContextRegistry()
    seed_orchestrator(registry_of_contexts)
    if settings.block_supabase:
        install_supabase_guard()

    runtime = ExecutionRuntime(context_registry=registry_of_contexts)

    output_root = PROJECT_ROOT / settings.output_directory
    output_root.mkdir(parents=True, exist_ok=True)
    if settings.run_id:
        run_id = settings.run_id
    else:
        run_id = allocate_run_id(output_root)
    writer = RunWriter(output_root, run_id)
    writer.hydrate_counts()
    commit = git_commit()
    pacer = Pacer(0 if settings.rate_limit_safe else settings.delay_between_requests_ms)

    from rate_limit.execution import partition_work
    from rate_limit.run_loop import execute_selected, print_summary

    todo, already_done, _index = partition_work(
        selected,
        run_id=run_id,
        results_path=writer.results_path,
        retry_failed=settings.retry_failed,
    )
    reused = 0
    still_todo: List[SealedCase] = []
    for case in todo:
        prior = success_index.get((case.validation_case_id, case.task_id))
        if prior and not settings.retry_failed and not intake_reevaluate and not diagnosis_reevaluate:
            logger.warning(
                "duplicate safety: selected already-successful case %s — selection should have excluded it",
                case.validation_case_id,
            )
            reused += 1
        else:
            still_todo.append(case)
    todo = still_todo
    if reused or already_done:
        logger.warning(
            "duplicate safety check removed %d prior SUCCESS and %d in-run case(s); "
            "pending selection should have excluded them",
            reused,
            len(already_done),
        )
    if settings.resume:
        logger.info(
            "RUN_RESUMED run_id=%s already_done=%d remaining=%d",
            run_id,
            len(already_done),
            len(todo),
        )

    config = _load_yaml(Path(settings.env_overlay and CONFIG_PATH or CONFIG_PATH))
    limits = load_provider_limits(config)
    scheduler = TokenAwareScheduler(
        limits,
        default_provider=(active_provider or settings.provider or "groq").lower(),
        max_concurrency=settings.concurrency,
        enabled=True,
    )

    logger.info(
        "run_id=%s cases=%d skipped=%d todo=%d concurrency=%d provider=%s rate_limit_safe=%s",
        run_id,
        len(selected),
        len(selection.ineligible),
        len(todo),
        settings.concurrency,
        active_provider or "configured chain",
        settings.rate_limit_safe,
    )

    started_at = now_iso()

    # Only genuine ineligibility is persisted as SKIPPED / NOT_SUPPORTED.
    # --max-cases leftovers stay PENDING and are not written.
    existing_keys = {(k[0], k[1]) for k in _index_keys(writer.results_path)}
    for case, status, reason in selection.ineligible:
        key = (case.validation_case_id, case.task_id)
        if key in existing_keys:
            continue
        skip_code = (
            "NOT_SUPPORTED"
            if status == ExecutionStatus.NOT_SUPPORTED
            else "UNSUPPORTED_CASE"
        )
        writer.write(
            build_result(
                run_id=run_id,
                case=case,
                status=status,
                telemetry=ExecutionTelemetry(started_at, started_at, 0),
                error={
                    "type": "skipped",
                    "message": reason,
                    "reason": reason,
                    "code": skip_code,
                    "stage": "selection",
                    "retryable": False,
                },
                commit=commit,
                random_seed=settings.random_seed,
            )
        )

    write_lock = threading.Lock()
    skipped_written = sum(
        writer.counts.get(name, 0)
        for name in (
            ExecutionStatus.SKIPPED,
            ExecutionStatus.NOT_SUPPORTED,
            ExecutionStatus.INPUT_NOT_SUPPORTED,
            ExecutionStatus.DRY_RUN,
        )
    )

    run_status, counts = execute_selected(
        selected=todo,
        skipped_count=skipped_written,
        progress_total=len(selected),
        eligible_count=selection.eligible_count,
        settings=settings,
        runtime=runtime,
        run_id=run_id,
        commit=commit,
        writer=writer,
        pacer=pacer,
        scheduler=scheduler,
        execute_case=execute_case,
        output_root=output_root,
        project_root=PROJECT_ROOT,
        configured_provider=active_provider or settings.provider or "groq",
        model=settings.model,
        started_monotonic=time.monotonic(),
        write_lock=write_lock,
    )

    from rate_limit.checkpoint import evaluation_coverage
    from rate_limit.execution import count_buckets

    buckets = count_buckets(writer.counts)
    from rate_limit.coverage import coverage_pair

    unique_success = already_evaluated + buckets["success"]
    dataset_coverage = coverage_pair(
        evaluated=unique_success,
        total=selection.eligible_count,
        label="Dataset coverage",
    )
    run_coverage = coverage_pair(
        evaluated=buckets["evaluated"],
        total=len(selected),
        label="Run coverage",
    )
    if selection.pending and run_status == "COMPLETED":
        run_status = "COMPLETED_PARTIAL"
    coverage = evaluation_coverage(
        evaluated=unique_success,
        eligible=selection.eligible_count,
    )
    from rate_limit.run_loop import save_checkpoint as _save_checkpoint

    prior_checkpoint = writer.directory / "checkpoint.json"
    last_case = None
    if prior_checkpoint.is_file():
        try:
            last_case = json.loads(prior_checkpoint.read_text(encoding="utf-8")).get(
                "last_completed_case"
            )
        except (OSError, json.JSONDecodeError):
            last_case = None

    _save_checkpoint(
        run_id=run_id,
        raw_dir=writer.directory,
        runs_dir=PROJECT_ROOT / "validation" / "results" / "runs" / run_id,
        status=run_status,
        total=selection.eligible_count,
        writer_counts=writer.counts,
        pending=len(selection.pending),
        last_case=last_case,
        scheduler=scheduler,
        extra={
            "task": settings.tasks[0] if settings.tasks else "",
            "dataset": settings.tasks[0] if settings.tasks else "",
            "configured_provider": active_provider or settings.provider or "groq",
            "model": settings.model,
            "eligible_cases": selection.eligible_count,
            "selected_cases": len(selected),
            "success_count": buckets["success"],
            "dataset_coverage": dataset_coverage,
            "run_coverage": run_coverage,
        },
    )

    manifest = {
        "run_id": run_id,
        "run_name": settings.run_name,
        "created_at": started_at,
        "completed_at": now_iso(),
        "project_version": _project_version(),
        "git_commit": commit,
        "tasks": sorted({case.task_id for case in selected}),
        "agents": sorted({agent_key(case.agent) for case in selected}),
        "case_count": len(selected),
        "skipped_count": len(selection.ineligible),
        "pending_count": len(selection.pending),
        "eligible_count": selection.eligible_count,
        "dataset_count": selection.dataset_count,
        "dataset_coverage": dataset_coverage,
        "run_coverage": run_coverage,
        "case_ids": [case.validation_case_id for case in selected],
        "provider_chain": provider_chain(),
        "configured_provider": active_provider or None,
        "configuration": {
            "max_cases": settings.max_cases,
            "max_cases_per_task": settings.max_cases_per_task,
            "concurrency": settings.concurrency,
            "retry_attempts": settings.retry_attempts,
            "retry_base_delay_ms": settings.retry_base_delay_ms,
            "timeout_seconds": settings.timeout_seconds,
            "delay_between_requests_ms": settings.delay_between_requests_ms,
            "random_seed": settings.random_seed,
            "rate_limit_safe": settings.rate_limit_safe,
            "resume": settings.resume,
            "retry_failed": settings.retry_failed,
            "filters": {
                "agents": settings.agents,
                "tasks": settings.tasks,
                "cases": settings.cases,
            },
        },
        "models": _configured_models(),
        "safety": {
            "supabase_blocked": settings.block_supabase,
            "blocked_supabase_calls": len(guard().blocked_calls),
            "blocked_call_samples": guard().blocked_calls[:10],
        },
        "evaluation_coverage": coverage,
        "provider_statistics": scheduler.provider_statistics(),
        "metrics_calculated": False,
        "status": run_status,
    }
    writer.write_manifest(manifest)

    logger.info("run %s complete: %s status=%s", run_id, counts, run_status)
    stats = scheduler.provider_statistics().get(
        (active_provider or settings.provider or "groq").lower(), {}
    )
    print_summary(
        run_id=run_id,
        task=settings.tasks[0] if settings.tasks else "",
        selected=len(selected),
        eligible=selection.eligible_count,
        evaluated=buckets["evaluated"],
        skipped=len(selection.ineligible),
        success=buckets["success"],
        failed=buckets["failed"],
        rate_limited=buckets["rate_limited"],
        coverage=coverage,
        provider=active_provider or "configured chain",
        fallbacks=int(stats.get("fallback_count") or 0),
        average_latency=stats.get("average_latency_ms"),
        status=run_status,
        results_path=writer.results_path,
        dataset_cases=selection.dataset_count,
        pending=len(selection.pending),
        dataset_coverage=dataset_coverage,
        run_coverage=run_coverage,
        provider_statistics=scheduler.provider_statistics(),
    )
    if guard().blocked_calls:
        print(
            f"\nBlocked {len(guard().blocked_calls)} production database call(s); "
            "see manifest.safety."
        )
    if is_intake_agent(settings.agents[0] if settings.agents else None) or (
        settings.agents == ["intake"]
    ):
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "validation" / "validators"))
            from write_intake_reports import finalize_intake_validation

            report_dir = finalize_intake_validation(run_id)
            print(f"\nIntake task-level reports: {report_dir}")
        except Exception:  # noqa: BLE001
            logger.exception("Intake task-level report generation failed; raw run is intact")
    elif is_diagnosis_agent(settings.agents[0] if settings.agents else None) or (
        settings.agents == ["diagnosis"]
    ):
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "validation" / "validators"))
            from write_diagnosis_reports import finalize_diagnosis_validation

            report_dir = finalize_diagnosis_validation(run_id)
            print(f"\nDiagnosis task-level reports: {report_dir}")
        except Exception:  # noqa: BLE001
            logger.exception("Diagnosis task-level report generation failed; raw run is intact")
    elif is_research_agent(settings.agents[0] if settings.agents else None) or (
        settings.agents == ["research"]
    ):
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "validation" / "validators"))
            from write_research_reports import finalize_research_validation

            report_dir = finalize_research_validation(run_id)
            print(f"\nResearch task-level reports: {report_dir}")
        except Exception:  # noqa: BLE001
            logger.exception("Research task-level report generation failed; raw run is intact")
    elif is_prescription_agent(settings.agents[0] if settings.agents else None) or (
        settings.agents == ["prescription"]
    ):
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "validation" / "validators"))
            from write_prescription_reports import finalize_prescription_validation

            report_dir = finalize_prescription_validation(run_id)
            print(f"\nPrescription task-level reports: {report_dir}")
        except Exception:  # noqa: BLE001
            logger.exception(
                "Prescription task-level report generation failed; raw run is intact"
            )
    elif is_medical_report_agent(settings.agents[0] if settings.agents else None) or (
        settings.agents == ["medical_report"]
    ):
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "validation" / "validators"))
            from write_medical_report_reports import finalize_medical_report_validation

            report_dir = finalize_medical_report_validation(run_id)
            print(f"\nMedical Report task-level reports: {report_dir}")
        except Exception:  # noqa: BLE001
            logger.exception(
                "Medical Report task-level report generation failed; raw run is intact"
            )
    return 0


def _reuse_success(
    prior: Dict[str, Any],
    *,
    run_id: str,
    case: Any,
    commit: Optional[str],
    seed: int,
) -> Dict[str, Any]:
    """Copy a prior SUCCESS into this run. Does not invent output or tokens."""
    reused = dict(prior)
    reused["run_id"] = run_id
    reused["eligible"] = True
    reused["skip_reason"] = None
    execution = dict(reused.get("execution") or {})
    execution["reused_from_run_id"] = prior.get("run_id")
    reused["execution"] = execution
    repro = dict(reused.get("reproducibility") or {})
    repro["reused_from_run_id"] = prior.get("run_id")
    if commit:
        repro["git_commit"] = commit
    repro["random_seed"] = seed
    reused["reproducibility"] = repro
    return reused


def _index_keys(results_path: Path) -> List[Tuple[str, str]]:
    from rate_limit.checkpoint import load_result_index

    return list(load_result_index(results_path).keys())


def _project_version() -> Optional[str]:
    readme = PROJECT_ROOT / "README.md"
    return "hospital-ai" if readme.exists() else None


def _configured_models() -> Dict[str, Any]:
    """Model routing as configured, for reproducibility. No secrets."""
    try:
        from app.config import get_settings

        settings = get_settings()
        return {
            "intake": getattr(settings, "intake_model", None),
            "diagnosis": getattr(settings, "diagnosis_model", None),
            "research": getattr(settings, "research_model", None),
            "prescription": getattr(settings, "prescription_model", None),
            "medical_report": getattr(settings, "report_model", None),
            "temperature": getattr(settings, "ai_temperature", None),
            "max_tokens": getattr(settings, "ai_max_tokens", None),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read model configuration: %s", exc)
        return {}


if __name__ == "__main__":
    raise SystemExit(main())
