"""
AIOrchestrator — the single entry point for every AI request in the system.

Every AI Agent calls exactly one method:

    AIOrchestrator.run(agent="diagnosis", task="differential_diagnosis",
                       patient_id=patient_id, response_model=SomeSchema)

An agent never learns which provider answered, which model was used, whether
a fallback took over, how many times the call was retried, where prompts live,
or whether the result came from cache. That ignorance is the point: it is what
lets the entire provider fleet be re-shaped from `providers.yaml` without a
single line changing in Intake, Diagnosis, Research, Prescription, or Medical
Report.

Run pipeline
------------
     1. Queue Admission     — bounded concurrency, priority ordering
     2. Context Management  — patient context, KG, history, timeline, risk
     3. Conversation Memory — recent prior turns for this patient/agent
     4. Context Compression — token optimization before anything is sent
     5. Prompt Loading      — load + version + render the markdown template
     6. Caching (read)      — identical request served without a provider call
     7. Provider Execution  — model routing, provider selection, retries, and
                              automatic failover (see ProviderOrchestrator)
     8. Response Parsing    — strict JSON, validated against `response_model`
     9. Logging / Usage     — one row per call for the dashboard
    10. Conversation Memory — persist this turn
    11. Caching (write)

Steps 1, 4, and 7 are what make this highly available: work is bounded,
prompts are trimmed to what actually matters, and no single provider outage
or exhausted quota can fail a clinical request while any other provider in
the fleet still has capacity.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional, Type
from uuid import UUID

from pydantic import BaseModel

from app.ai.orchestrator.cache_manager import InMemoryTTLCache, get_cache_manager
from app.ai.orchestrator.context_compressor import (
    ContextCompressor,
    get_context_compressor,
)
from app.ai.orchestrator.context_manager import ContextManager
from app.ai.orchestrator.conversation_manager import (
    ConversationManager,
    get_conversation_manager,
)
from app.ai.orchestrator.interfaces import ProviderMessage
from app.ai.orchestrator.logger import AIInteractionLogger, get_ai_interaction_logger
from app.ai.orchestrator.models import AIResponse, OrchestratorDebugInfo
from app.ai.orchestrator.prompt_manager import PromptManager, get_prompt_manager
from app.ai.orchestrator.provider_orchestrator import (
    AllProvidersFailedError,
    ProviderOrchestrator,
    get_provider_orchestrator,
)
from app.ai.orchestrator.request_queue import (
    RequestPriority,
    RequestQueue,
    get_request_queue,
)
from app.ai.orchestrator.response_parser import (
    AIResponseParseError,
    ResponseParser,
    get_response_parser,
)
from app.ai.orchestrator.router import ModelRouter, get_model_router
from app.ai.orchestrator.utils import truncate
from app.core.logging import get_logger

logger = get_logger("hospital_ai.orchestrator")

#: Queue priority per agent. Prescription safety checks must never wait behind
#: a batch of routine report generation.
_AGENT_PRIORITY = {
    "prescription": RequestPriority.CRITICAL,
    "diagnosis": RequestPriority.HIGH,
    "intake": RequestPriority.HIGH,
    "research": RequestPriority.NORMAL,
    "medical_report": RequestPriority.NORMAL,
}

#: Share of the prompt budget reserved for the prompt template and system
#: message. The compressor only sees the *variables*, but what the provider
#: meters is the rendered result, so budgeting the variables at 100% would
#: reliably overshoot by the size of the template.
_TEMPLATE_OVERHEAD_RATIO = 0.25

#: Floor for that reservation, for agents whose templates are short.
_TEMPLATE_OVERHEAD_MIN_CHARS = 2_000


def _variable_budget_chars(budget_tokens: int) -> Optional[int]:
    """Convert a provider prompt budget into a character ceiling for context.

    Returns None when no provider declares a limit, which the compressor
    reads as "prune waste, but don't trim for size".
    """
    if not budget_tokens:
        return None
    # ~4 characters per token, the same heuristic the providers' own
    # pre-flight estimates use.
    total_chars = budget_tokens * 4
    overhead = max(
        _TEMPLATE_OVERHEAD_MIN_CHARS, int(total_chars * _TEMPLATE_OVERHEAD_RATIO)
    )
    return max(1_000, total_chars - overhead)


class AIOrchestratorError(RuntimeError):
    """An orchestrator run failed.

    The message is written for a human — provider outages, exhausted quotas,
    and parse failures all arrive here already translated into something an
    operator can act on. Raw provider payloads stay in the logs.
    """


class AIOrchestrator:
    def __init__(
        self,
        *,
        context_manager: Optional[ContextManager] = None,
        prompt_manager: Optional[PromptManager] = None,
        router: Optional[ModelRouter] = None,
        provider_orchestrator: Optional[ProviderOrchestrator] = None,
        compressor: Optional[ContextCompressor] = None,
        queue: Optional[RequestQueue] = None,
        cache: Optional[InMemoryTTLCache] = None,
        memory: Optional[ConversationManager] = None,
        parser: Optional[ResponseParser] = None,
        interaction_logger: Optional[AIInteractionLogger] = None,
    ) -> None:
        self._context_manager = context_manager or ContextManager()
        self._prompt_manager = prompt_manager or get_prompt_manager()
        self._router = router or get_model_router()
        self._providers = provider_orchestrator or get_provider_orchestrator()
        self._compressor = compressor or get_context_compressor()
        self._queue = queue or get_request_queue()
        self._cache = cache or get_cache_manager()
        self._memory = memory or get_conversation_manager()
        self._parser = parser or get_response_parser()
        self._interaction_logger = interaction_logger or get_ai_interaction_logger()

    def run(
        self,
        *,
        agent: str,
        task: str,
        patient_id: Optional[UUID] = None,
        response_model: Optional[Type[BaseModel]] = None,
        extra_vars: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        use_memory: bool = True,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        priority: Optional[RequestPriority] = None,
    ) -> AIResponse:
        from app.config import get_settings

        settings = get_settings()
        started = time.monotonic()
        queue_priority = priority or _AGENT_PRIORITY.get(
            (agent or "").strip().lower(), RequestPriority.NORMAL
        )

        # 1. Queue Admission — bounds concurrent provider calls.
        with self._queue.slot(
            agent=agent,
            task=task,
            priority=queue_priority,
            patient_id=str(patient_id) if patient_id else "",
            timeout=getattr(settings, "ai_queue_wait_timeout_seconds", 60.0),
        ) as request:
            queue_wait_ms = request.wait_ms

            # 2. Context Management
            request.progress("assembling context", 0.1)
            variables = self._context_manager.build(agent, patient_id, extra_vars)

            # 3. Conversation Memory (read)
            if use_memory and patient_id is not None:
                variables["recent_conversation"] = self._memory.recent(
                    patient_id, agent, limit=getattr(settings, "ai_memory_turns", 5)
                )

            # 4. Context Compression — token optimization
            #
            # Sized to the fleet we actually have: the budget is the prompt
            # capacity of the roomiest usable provider, so a Gemini-backed
            # deployment keeps its full context while a Groq-only one trims
            # to fit rather than sending a request that will be rejected.
            compression: Dict[str, Any] = {}
            pinned = self._pinned_provider(settings)
            if getattr(settings, "ai_context_compression", True):
                request.progress("compressing context", 0.2)
                budget_tokens = self._providers.prompt_budget_tokens(
                    agent=agent,
                    pinned=pinned,
                    reserved_completion_tokens=(
                        max_tokens if max_tokens is not None else settings.ai_max_tokens
                    ),
                )
                variables, report = self._compressor.compress(
                    variables,
                    budget_chars=_variable_budget_chars(budget_tokens),
                )
                compression = report.as_dict()

            # 5. Prompt Loading
            request.progress("rendering prompt", 0.3)
            system_prompt, rendered_prompt, prompt_version = self._prompt_manager.render(
                agent, task, variables
            )

            # 6. Caching (read)
            cache_key = self._cache.build_key(agent, task, rendered_prompt)
            if use_cache:
                cached = self._cache.get(cache_key)
                if cached is not None:
                    return self._from_cache(
                        cached,
                        agent=agent,
                        task=task,
                        patient_id=patient_id,
                        prompt_version=prompt_version,
                        started=started,
                        queue_wait_ms=queue_wait_ms,
                        compression=compression,
                    )

            # 7. Provider Execution — routing, retries, automatic failover
            request.progress("calling AI provider", 0.5)
            try:
                execution = self._providers.execute(
                    [
                        ProviderMessage(role="system", content=system_prompt),
                        ProviderMessage(role="user", content=rendered_prompt),
                    ],
                    agent=agent,
                    task=task,
                    temperature=(
                        temperature if temperature is not None else settings.ai_temperature
                    ),
                    max_tokens=(
                        max_tokens if max_tokens is not None else settings.ai_max_tokens
                    ),
                    timeout=getattr(settings, "ai_timeout_seconds", 120.0),
                    max_retries=settings.ai_max_retries,
                    base_delay_ms=settings.ai_retry_base_delay_ms,
                    pinned_provider=pinned,
                    # AI_FAILOVER_ENABLED=false collapses the chain to a single
                    # provider — useful when reproducing a provider-specific bug.
                    max_providers=(
                        None if getattr(settings, "ai_failover_enabled", True) else 1
                    ),
                )
            except AllProvidersFailedError as exc:
                duration_ms = int((time.monotonic() - started) * 1000)
                primary = exc.attempts[0].provider if exc.attempts else "none"
                self._interaction_logger.log(
                    agent=agent,
                    task=task,
                    provider=primary,
                    model=exc.attempts[0].model if exc.attempts else "",
                    status="error",
                    duration_ms=duration_ms,
                    retry_count=sum(a.retries for a in exc.attempts),
                    error_message=str(exc),
                    patient_id=patient_id,
                    primary_provider=primary,
                    fallback_used=len({a.provider for a in exc.attempts}) > 1,
                    fallback_reason=next(
                        (a.reason for a in exc.attempts if a.reason), ""
                    ),
                    attempts=[a.as_dict() for a in exc.attempts],
                )
                raise AIOrchestratorError(str(exc)) from exc

            completion = execution.completion

            # 8. Response Parsing
            request.progress("parsing response", 0.8)
            try:
                if response_model is not None:
                    parsed = self._parser.parse(completion.content, response_model)
                    data = parsed.model_dump(mode="json")
                else:
                    data = self._parser.extract_json(completion.content)
            except AIResponseParseError as exc:
                duration_ms = int((time.monotonic() - started) * 1000)
                self._interaction_logger.log(
                    agent=agent,
                    task=task,
                    provider=execution.provider,
                    model=execution.model,
                    status="parse_error",
                    duration_ms=duration_ms,
                    retry_count=execution.total_retries,
                    prompt_tokens=completion.prompt_tokens,
                    completion_tokens=completion.completion_tokens,
                    error_message=str(exc),
                    patient_id=patient_id,
                    primary_provider=execution.primary_provider,
                    fallback_used=execution.fallback_used,
                    fallback_reason=execution.fallback_reason,
                    attempts=[a.as_dict() for a in execution.attempts],
                )
                raise AIOrchestratorError(str(exc)) from exc

            duration_ms = int((time.monotonic() - started) * 1000)

            # 9. Logging / Usage Tracking
            self._interaction_logger.log(
                agent=agent,
                task=task,
                provider=execution.provider,
                model=execution.model,
                status="success",
                duration_ms=duration_ms,
                retry_count=execution.total_retries,
                prompt_tokens=completion.prompt_tokens,
                completion_tokens=completion.completion_tokens,
                patient_id=patient_id,
                estimated_cost_usd=execution.estimated_cost_usd,
                primary_provider=execution.primary_provider,
                fallback_used=execution.fallback_used,
                fallback_reason=execution.fallback_reason,
                attempts=[a.as_dict() for a in execution.attempts],
            )

            # 10. Conversation Memory (write)
            if use_memory and patient_id is not None:
                self._memory.append(
                    patient_id,
                    agent,
                    task,
                    rendered_prompt,
                    completion.content,
                    data,
                    execution.model,
                    execution.provider,
                )

            # 11. Caching (write)
            if use_cache:
                self._cache.set(
                    cache_key,
                    {
                        "_data": data,
                        "_raw_response": truncate(completion.content, 4000),
                        "_provider": execution.provider,
                        "_model": execution.model,
                    },
                    agent=agent,
                    task=task,
                    patient_id=str(patient_id) if patient_id else "",
                )

            debug = OrchestratorDebugInfo(
                agent=agent,
                task=task,
                provider=execution.provider,
                model=execution.model,
                prompt_name=f"{agent}/{task}",
                prompt_version=prompt_version,
                processing_time_ms=duration_ms,
                prompt_tokens=completion.prompt_tokens,
                completion_tokens=completion.completion_tokens,
                total_tokens=completion.prompt_tokens + completion.completion_tokens,
                retry_count=execution.total_retries,
                cache_hit=False,
                estimated_cost_usd=execution.estimated_cost_usd,
                primary_provider=execution.primary_provider,
                fallback_used=execution.fallback_used,
                fallback_reason=execution.fallback_reason,
                attempts=[a.as_dict() for a in execution.attempts],
                context_compression=compression,
                queue_wait_ms=queue_wait_ms,
                raw_response=truncate(completion.content, 4000),
                status="success",
            )
            return AIResponse(data=data, debug=debug)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _pinned_provider(settings) -> Optional[str]:
        """`AI_PROVIDER` names the *preferred* primary, not a lock — the
        Provider Orchestrator still fails over past it to keep the system
        available. The single exception is a provider marked
        `exclude_from_failover` in providers.yaml (currently only `stub`),
        which the load balancer treats as an exclusive pin."""
        preferred = (getattr(settings, "ai_provider", "") or "").strip().lower()
        return preferred or None

    def _from_cache(
        self,
        cached: Dict[str, Any],
        *,
        agent: str,
        task: str,
        patient_id: Optional[UUID],
        prompt_version: str,
        started: float,
        queue_wait_ms: int,
        compression: Dict[str, Any],
    ) -> AIResponse:
        duration_ms = int((time.monotonic() - started) * 1000)
        provider = cached.get("_provider", "cache")
        model = cached.get("_model", "")
        self._interaction_logger.log(
            agent=agent,
            task=task,
            provider=provider,
            model=model,
            status="success",
            duration_ms=duration_ms,
            cache_hit=True,
            patient_id=patient_id,
        )
        debug = OrchestratorDebugInfo(
            agent=agent,
            task=task,
            provider=provider,
            model=model,
            prompt_name=f"{agent}/{task}",
            prompt_version=prompt_version,
            processing_time_ms=duration_ms,
            cache_hit=True,
            queue_wait_ms=queue_wait_ms,
            context_compression=compression,
            raw_response=cached.get("_raw_response", ""),
            status="success",
        )
        return AIResponse(data=cached.get("_data", {}), debug=debug)


_orchestrator: AIOrchestrator | None = None


def get_orchestrator() -> AIOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AIOrchestrator()
    return _orchestrator
