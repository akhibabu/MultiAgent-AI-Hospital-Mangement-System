"""
RequestQueue — admission control for in-flight AI requests.

Every provider enforces concurrency limits, and free tiers enforce tight
ones. Without a gate, twenty clinicians pressing "Run Diagnosis" at once
produce twenty simultaneous provider calls, most of which come back as 429s
and burn quota achieving nothing. This queue bounds concurrency so surplus
work waits its turn instead of failing.

It is a *priority* queue, which matters clinically: a prescription safety
check must not sit behind a batch of routine report generations. Waiters are
admitted in `(priority, arrival)` order, so a high-priority request jumps
ahead of queued lower-priority ones while never preempting work already
running.

Usage — the slot is a context manager, so the counter can't leak on an
exception path::

    with queue.slot(agent="diagnosis", task="severity", priority=RequestPriority.HIGH) as req:
        req.progress("calling provider", 0.5)
        ...

Design constraints
------------------
* The orchestrator's request path is synchronous (FastAPI runs sync endpoints
  in a threadpool), so this is a threading primitive, not an asyncio one.
* Waiting is bounded — a request that cannot get a slot within its timeout
  fails fast with a clear message rather than holding a worker thread open
  indefinitely.
* Cancellation is cooperative: cancelling a queued request stops it from ever
  starting, and cancelling a running one raises at the next checkpoint the
  orchestrator reaches. Nothing is killed mid-flight.
"""
from __future__ import annotations

import enum
import itertools
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from app.core.logging import get_logger

logger = get_logger("hospital_ai.orchestrator.queue")


class RequestPriority(enum.IntEnum):
    """Lower value = admitted sooner."""

    CRITICAL = 0  # safety-critical checks (drug interactions, allergies)
    HIGH = 1  # clinician is actively waiting
    NORMAL = 2  # standard agent runs
    LOW = 3  # background/batch work


class RequestCancelledError(RuntimeError):
    """Raised when a queued or running request was cancelled."""


class RequestQueueTimeoutError(TimeoutError):
    """Raised when a request could not be admitted before its deadline."""


@dataclass
class QueuedRequest:
    """Live state for one request, from enqueue to completion."""

    id: str
    agent: str
    task: str
    priority: RequestPriority
    patient_id: str = ""
    enqueued_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    state: str = "queued"  # queued | running | done | cancelled | timeout | failed
    stage: str = ""
    percent: float = 0.0
    _cancelled: bool = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def wait_ms(self) -> int:
        started = self.started_at or time.time()
        return int((started - self.enqueued_at) * 1000)

    @property
    def running_ms(self) -> int:
        if self.started_at is None:
            return 0
        return int(((self.finished_at or time.time()) - self.started_at) * 1000)

    def progress(self, stage: str, percent: float = 0.0) -> None:
        """Report progress, and abort at this checkpoint if cancelled.

        Called at pipeline-stage boundaries, which is what makes cancellation
        cooperative rather than a hard kill.
        """
        self.stage = stage
        self.percent = max(0.0, min(1.0, percent))
        if self._cancelled:
            raise RequestCancelledError(
                f"AI request {self.id} was cancelled at stage '{stage}'."
            )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent": self.agent,
            "task": self.task,
            "priority": self.priority.name.lower(),
            "patient_id": self.patient_id,
            "state": self.state,
            "stage": self.stage,
            "percent": round(self.percent, 3),
            "wait_ms": self.wait_ms,
            "running_ms": self.running_ms,
            "enqueued_at": self.enqueued_at,
        }


class RequestQueue:
    def __init__(
        self, max_concurrent: int = 4, default_wait_timeout: float = 60.0
    ) -> None:
        self._max_concurrent = max(1, max_concurrent)
        self._default_wait_timeout = max(1.0, default_wait_timeout)
        self._condition = threading.Condition()
        self._sequence = itertools.count()
        self._active: Dict[str, QueuedRequest] = {}
        self._waiting: Dict[str, QueuedRequest] = {}
        #: Admission tickets as (priority, arrival_sequence, request_id).
        self._tickets: List[tuple[int, int, str]] = []
        self._completed = 0
        self._cancelled = 0
        self._timed_out = 0
        self._failed = 0

    # ------------------------------------------------------------------
    # Admission
    # ------------------------------------------------------------------
    @contextmanager
    def slot(
        self,
        *,
        agent: str,
        task: str = "",
        priority: RequestPriority = RequestPriority.NORMAL,
        patient_id: str = "",
        timeout: Optional[float] = None,
        request_id: Optional[str] = None,
    ) -> Iterator[QueuedRequest]:
        request = QueuedRequest(
            id=request_id or uuid.uuid4().hex[:12],
            agent=agent,
            task=task,
            priority=priority,
            patient_id=str(patient_id or ""),
        )
        deadline = time.time() + (timeout or self._default_wait_timeout)
        ticket = (int(priority), next(self._sequence), request.id)

        with self._condition:
            self._waiting[request.id] = request
            self._tickets.append(ticket)
            self._tickets.sort()
            try:
                while not self._may_start(ticket):
                    if request.cancelled:
                        raise RequestCancelledError(
                            f"AI request {request.id} was cancelled while queued."
                        )
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        request.state = "timeout"
                        self._timed_out += 1
                        raise RequestQueueTimeoutError(
                            f"The AI system is busy — {len(self._active)} request(s) are "
                            f"already running and this one could not start within "
                            f"{int(timeout or self._default_wait_timeout)}s. Please retry."
                        )
                    self._condition.wait(timeout=min(remaining, 1.0))
            finally:
                self._waiting.pop(request.id, None)
                if request.state in {"timeout", "cancelled"}:
                    self._discard_ticket(ticket)
                    self._condition.notify_all()

            self._tickets.remove(ticket)
            request.state = "running"
            request.started_at = time.time()
            self._active[request.id] = request

        try:
            yield request
        except RequestCancelledError:
            request.state = "cancelled"
            self._cancelled += 1
            raise
        except BaseException:
            request.state = "failed"
            self._failed += 1
            raise
        else:
            request.state = "done"
            request.percent = 1.0
            self._completed += 1
        finally:
            with self._condition:
                request.finished_at = time.time()
                self._active.pop(request.id, None)
                self._condition.notify_all()

    def _may_start(self, ticket: tuple[int, int, str]) -> bool:
        """True when a slot is free and this ticket is next in line. Called
        with the condition held."""
        if len(self._active) >= self._max_concurrent:
            return False
        return bool(self._tickets) and self._tickets[0] == ticket

    def _discard_ticket(self, ticket: tuple[int, int, str]) -> None:
        try:
            self._tickets.remove(ticket)
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------
    def cancel(self, request_id: str) -> bool:
        """Cancel a queued or running request. Returns False if unknown."""
        with self._condition:
            request = self._active.get(request_id) or self._waiting.get(request_id)
            if request is None:
                return False
            request._cancelled = True
            if request.state == "queued":
                request.state = "cancelled"
                self._cancelled += 1
            self._condition.notify_all()
        logger.info("AI request %s cancellation requested.", request_id)
        return True

    def cancel_for_patient(self, patient_id: str) -> int:
        with self._condition:
            targets = [
                r.id
                for r in list(self._active.values()) + list(self._waiting.values())
                if r.patient_id == str(patient_id)
            ]
        return sum(1 for rid in targets if self.cancel(rid))

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        with self._condition:
            return {
                "max_concurrent": self._max_concurrent,
                "active": len(self._active),
                "queued": len(self._waiting),
                "completed": self._completed,
                "cancelled": self._cancelled,
                "timed_out": self._timed_out,
                "failed": self._failed,
                "active_requests": [r.as_dict() for r in self._active.values()],
                "queued_requests": sorted(
                    (r.as_dict() for r in self._waiting.values()),
                    key=lambda r: (r["priority"], r["enqueued_at"]),
                ),
            }


_queue: Optional[RequestQueue] = None


def get_request_queue() -> RequestQueue:
    global _queue
    if _queue is None:
        from app.config import get_settings

        settings = get_settings()
        _queue = RequestQueue(
            max_concurrent=getattr(settings, "ai_max_concurrent_requests", 4),
            default_wait_timeout=getattr(settings, "ai_queue_wait_timeout_seconds", 60.0),
        )
    return _queue
