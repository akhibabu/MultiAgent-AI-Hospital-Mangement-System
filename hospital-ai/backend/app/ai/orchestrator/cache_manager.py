"""
CacheManager — intelligent response cache for identical AI requests.

A cache hit costs no tokens, no provider quota, and no latency, which makes
this the cheapest availability measure in the system: repeated work simply
never reaches a provider. It is also why the cache key includes the fully
rendered prompt — two requests only share a result when the model would
genuinely have seen identical input.

Per-category TTLs
-----------------
Different AI outputs go stale at very different rates, so a single global TTL
is either too aggressive for research or too lax for a prescription check:

    research        long   — literature and guidelines barely move day to day
    medical_report  medium — reports are regenerated from settled facts
    diagnosis       short  — must reflect the newest vitals and labs
    prescription    short  — safety-critical; a stale interaction check is
                             the one thing this cache must never serve

Invalidation
------------
Beyond TTL expiry, entries can be dropped explicitly by key, by agent, by
patient, or wholesale. Per-patient invalidation is the important one: when
new labs or a new diagnosis land, every cached AI answer about that patient
is immediately suspect, and the ingesting service can drop them in one call.

Backed by a dict + lock. There is no Redis dependency in this project today;
swapping in a distributed cache later means writing one new `ICacheManager`,
with no orchestrator or agent change.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.ai.orchestrator.interfaces import ICacheManager
from app.ai.orchestrator.utils import stable_hash
from app.core.logging import get_logger

logger = get_logger("hospital_ai.orchestrator.cache")

#: TTL multipliers applied to the configured base TTL, per agent category.
_CATEGORY_TTL_MULTIPLIER: Dict[str, float] = {
    "research": 6.0,
    "medical_report": 3.0,
    "intake": 2.0,
    "diagnosis": 1.0,
    "prescription": 0.5,
}


@dataclass
class CacheEntry:
    value: Dict[str, Any]
    expires_at: float
    agent: str = ""
    task: str = ""
    patient_id: str = ""
    created_at: float = field(default_factory=time.time)
    hits: int = 0

    @property
    def expired(self) -> bool:
        return self.expires_at < time.time()


class InMemoryTTLCache(ICacheManager):
    def __init__(self, ttl_seconds: int = 300, max_entries: int = 500) -> None:
        self._ttl = max(ttl_seconds, 0)
        self._max_entries = max(max_entries, 1)
        self._lock = threading.Lock()
        self._store: Dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._invalidations = 0

    # ------------------------------------------------------------------
    # Keys
    # ------------------------------------------------------------------
    @staticmethod
    def build_key(agent: str, task: str, rendered_prompt: str) -> str:
        """Identity of a request: agent + task + the fully rendered prompt.

        The model deliberately is *not* part of the key. In a failover system
        the same question may be answered by Groq today and Gemini tomorrow,
        and a cached clinical answer is valid content regardless of which
        provider produced it. Keying on the model would miss on every
        failover — exactly when quota pressure makes cache hits most
        valuable. The producing provider/model is recorded in the entry's
        value so Developer Mode can still show where an answer came from.
        """
        return stable_hash(agent, task, rendered_prompt)

    def ttl_for(self, agent: str) -> int:
        multiplier = _CATEGORY_TTL_MULTIPLIER.get((agent or "").strip().lower(), 1.0)
        return int(self._ttl * multiplier)

    # ------------------------------------------------------------------
    # Read / write
    # ------------------------------------------------------------------
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if self._ttl <= 0:
            return None
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.expired:
                self._store.pop(key, None)
                self._misses += 1
                return None
            entry.hits += 1
            self._hits += 1
            return entry.value

    def set(
        self,
        key: str,
        value: Dict[str, Any],
        *,
        agent: str = "",
        task: str = "",
        patient_id: str = "",
    ) -> None:
        ttl = self.ttl_for(agent) if agent else self._ttl
        if ttl <= 0:
            return
        with self._lock:
            self._evict_if_needed(key)
            self._store[key] = CacheEntry(
                value=value,
                expires_at=time.time() + ttl,
                agent=agent,
                task=task,
                patient_id=patient_id,
            )

    def _evict_if_needed(self, incoming_key: str) -> None:
        """Drop expired entries first; only then evict the oldest. Called with
        the lock held."""
        if len(self._store) < self._max_entries or incoming_key in self._store:
            return
        expired = [k for k, e in self._store.items() if e.expired]
        for key in expired:
            self._store.pop(key, None)
        if len(self._store) >= self._max_entries:
            oldest = min(self._store, key=lambda k: self._store[k].created_at)
            self._store.pop(oldest, None)
            self._evictions += 1

    # ------------------------------------------------------------------
    # Invalidation
    # ------------------------------------------------------------------
    def invalidate(self, key: str) -> int:
        with self._lock:
            removed = 1 if self._store.pop(key, None) else 0
            self._invalidations += removed
            return removed

    def invalidate_agent(self, agent: str) -> int:
        return self._invalidate_where(lambda e: e.agent == (agent or "").strip().lower())

    def invalidate_patient(self, patient_id: str) -> int:
        """Drop every cached AI answer about one patient.

        Call this whenever new clinical data lands (labs, vitals, a new
        diagnosis): the patient's context changed, so every cached answer
        derived from the old context is stale by definition.
        """
        target = str(patient_id or "").strip()
        return self._invalidate_where(lambda e: e.patient_id == target)

    def _invalidate_where(self, predicate) -> int:
        with self._lock:
            keys = [k for k, e in self._store.items() if predicate(e)]
            for key in keys:
                self._store.pop(key, None)
            self._invalidations += len(keys)
        if keys:
            logger.info("Invalidated %s cached AI response(s).", len(keys))
        return len(keys)

    def clear(self) -> int:
        with self._lock:
            count = len(self._store)
            self._store.clear()
            self._invalidations += count
            return count

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            by_agent: Dict[str, int] = {}
            for entry in self._store.values():
                if not entry.expired:
                    by_agent[entry.agent or "unknown"] = (
                        by_agent.get(entry.agent or "unknown", 0) + 1
                    )
            return {
                "entries": len(self._store),
                "ttl_seconds": self._ttl,
                "max_entries": self._max_entries,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 3) if total else 0.0,
                "evictions": self._evictions,
                "invalidations": self._invalidations,
                "entries_by_agent": by_agent,
                "category_ttl_seconds": {
                    agent: self.ttl_for(agent) for agent in _CATEGORY_TTL_MULTIPLIER
                },
            }

    def keys_for_patient(self, patient_id: str) -> List[str]:
        with self._lock:
            return [
                k for k, e in self._store.items() if e.patient_id == str(patient_id)
            ]


_cache: InMemoryTTLCache | None = None


def get_cache_manager() -> InMemoryTTLCache:
    global _cache
    if _cache is None:
        from app.config import get_settings

        settings = get_settings()
        _cache = InMemoryTTLCache(
            ttl_seconds=getattr(settings, "ai_cache_ttl_seconds", 300)
        )
    return _cache
