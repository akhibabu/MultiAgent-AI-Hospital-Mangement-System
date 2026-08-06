"""
ContextCompressor — token optimization applied before every provider call.

Sits between the `ContextManager` (which gathers everything about a patient)
and the `PromptManager` (which interpolates it into a template). Gathering
broadly and pruning centrally is deliberate: agents stay simple and
declarative, and the cost/latency tuning lives in one reviewable place.

Why this matters more than it looks
-----------------------------------
Free provider tiers are billed in tokens per day, so prompt bloat is the
difference between a system that runs all day and one that stops answering
by mid-afternoon. The dominant sink is conversation memory: each stored turn
keeps up to 8 000 characters of the *rendered prompt* plus 8 000 of response
text, and five turns are replayed into every new request. Left alone that is
tens of thousands of wasted characters per call — re-sending a patient's
context back to the model that already saw it.

What it does
------------
* **Prunes conversation memory** to a compact `{task, summary, when}` shape,
  dropping the replayed prompt entirely — the model needs to know what it
  previously *concluded*, not what it was previously *asked*.
* **Removes duplicate history**, comparing normalized text so
  "Chest pain" and "chest  pain." collapse to one entry.
* **Trims timelines and long lists** to the most recent/most relevant N.
* **Compresses the knowledge graph**, keeping the highest-weight nodes and
  edges and dropping bookkeeping fields (ids, timestamps, audit columns)
  that carry no clinical signal.
* **Truncates oversized strings** and drops empty values.

Everything is size-bounded rather than model-summarized: compression must
never itself cost an LLM call, and must never fail a request. It is
lossy by construction, so limits are set generously and the raw context
remains available to any agent that asks for it explicitly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger("hospital_ai.orchestrator.compressor")

#: Bookkeeping fields that cost tokens and carry no clinical meaning.
_NOISE_KEYS = frozenset(
    {
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "patient_id",
        "tenant_id",
        "raw",
        "embedding",
        "checksum",
    }
)

#: Keys whose values are lists that should be capped hardest — long,
#: append-only clinical histories where only the recent tail is actionable.
_TIMELINE_KEYS = frozenset(
    {"timeline", "medical_history_timeline", "history_timeline", "events"}
)

_WHITESPACE = re.compile(r"\s+")

#: Safety valve on the budget-enforcement loop. Halving the largest field each
#: round shrinks the context geometrically, so this many rounds is far more
#: than any real context needs — it exists so a pathological input can't spin.
_MAX_BUDGET_ROUNDS = 24

#: Collections smaller than this aren't worth trimming; the savings are noise
#: and the clinical cost of losing them is not.
_MIN_TRIM_CHARS = 500


@dataclass(frozen=True)
class CompressionLimits:
    """Tunable budgets. Defaults are deliberately generous — the goal is
    removing waste, not starving the model of clinical context."""

    max_memory_turns: int = 3
    max_memory_summary_chars: int = 600
    max_timeline_entries: int = 12
    max_list_entries: int = 25
    max_graph_nodes: int = 40
    max_graph_edges: int = 40
    max_string_chars: int = 4000
    max_total_chars: int = 60_000


@dataclass
class CompressionReport:
    """Before/after sizes, surfaced in Developer Mode so the savings are
    visible rather than an invisible behavior change."""

    original_chars: int = 0
    compressed_chars: int = 0
    #: Character ceiling that applied, when one was enforced.
    budget_chars: int = 0
    #: True when the aggressive second pass ran — i.e. the context did not fit
    #: the roomiest available provider and had to be trimmed further.
    budget_enforced: bool = False

    @property
    def saved_chars(self) -> int:
        return max(0, self.original_chars - self.compressed_chars)

    @property
    def ratio(self) -> float:
        if not self.original_chars:
            return 1.0
        return round(self.compressed_chars / self.original_chars, 3)

    @property
    def estimated_tokens_saved(self) -> int:
        """~4 characters per token, the same heuristic providers use for
        pre-flight estimates."""
        return self.saved_chars // 4

    def as_dict(self) -> Dict[str, Any]:
        return {
            "original_chars": self.original_chars,
            "compressed_chars": self.compressed_chars,
            "saved_chars": self.saved_chars,
            "ratio": self.ratio,
            "estimated_tokens_saved": self.estimated_tokens_saved,
            "budget_chars": self.budget_chars,
            "budget_enforced": self.budget_enforced,
        }


class ContextCompressor:
    def __init__(self, limits: Optional[CompressionLimits] = None) -> None:
        self._limits = limits or CompressionLimits()

    def compress(
        self, variables: Dict[str, Any], *, budget_chars: Optional[int] = None
    ) -> tuple[Dict[str, Any], CompressionReport]:
        """Return a pruned copy of `variables` plus a size report.

        `budget_chars` is a hard ceiling supplied by the caller — normally the
        prompt budget of the roomiest provider currently in the failover
        chain. When the standard pass leaves the context above it, a second
        and more aggressive pass runs, because the alternative is a request
        every provider will reject.

        Never raises: if anything unexpected turns up in the context we log
        it and hand back the original, because a compression bug must not be
        able to take down clinical AI features.
        """
        report = CompressionReport(original_chars=_rough_size(variables))
        try:
            compressed = {
                key: self._compress_value(key, value)
                for key, value in variables.items()
            }
            compressed = {
                key: value for key, value in compressed.items() if not _is_empty(value)
            }
        except Exception as exc:  # noqa: BLE001 - never break a clinical request
            logger.warning("Context compression failed, using raw context: %s", exc)
            report.compressed_chars = report.original_chars
            return variables, report

        ceiling = budget_chars if budget_chars and budget_chars > 0 else None
        ceiling = min(ceiling, self._limits.max_total_chars) if ceiling else self._limits.max_total_chars

        size = _rough_size(compressed)
        if size > ceiling:
            try:
                compressed = self._enforce_budget(compressed, ceiling)
                report.budget_chars = ceiling
                report.budget_enforced = True
            except Exception as exc:  # noqa: BLE001
                logger.warning("Budget enforcement failed, keeping full context: %s", exc)

        report.compressed_chars = _rough_size(compressed)
        if report.saved_chars:
            logger.debug(
                "Context compressed %s -> %s chars (~%s tokens saved)",
                report.original_chars,
                report.compressed_chars,
                report.estimated_tokens_saved,
            )
        return compressed, report

    # ------------------------------------------------------------------
    # Budget enforcement
    # ------------------------------------------------------------------
    def _enforce_budget(self, variables: Dict[str, Any], ceiling: int) -> Dict[str, Any]:
        """Shrink `variables` until it fits `ceiling` characters.

        Trims the biggest collections first and in rounds, so the reduction
        is spread across whatever is actually bulky instead of deleting one
        field wholesale. Scalars and short values are never touched — losing
        the patient's age to save 3 characters would be absurd, and the bulk
        is always in lists.

        This is a floor, not a target: it only engages when the context is
        genuinely too big for every available provider.
        """
        current = dict(variables)
        for _ in range(_MAX_BUDGET_ROUNDS):
            size = _rough_size(current)
            if size <= ceiling:
                return current

            # Rank collections by how many characters they contribute.
            costs = sorted(
                (
                    (_rough_size(value), key)
                    for key, value in current.items()
                    if isinstance(value, (list, dict)) and _rough_size(value) > _MIN_TRIM_CHARS
                ),
                reverse=True,
            )
            if not costs:
                break

            # Halve the largest contributor each round. Geometric decay
            # converges quickly without over-trimming on the first pass.
            _, biggest = costs[0]
            current[biggest] = _halve(current[biggest])

        final = _rough_size(current)
        if final > ceiling:
            logger.warning(
                "Context still %s chars after budget enforcement (ceiling %s) — "
                "the request may be rejected as too large.",
                final,
                ceiling,
            )
        else:
            logger.info(
                "Context trimmed to %s chars to fit the %s-char provider budget.",
                final,
                ceiling,
            )
        return current

    # ------------------------------------------------------------------
    # Per-key strategies
    # ------------------------------------------------------------------
    def _compress_value(self, key: str, value: Any) -> Any:
        normalized_key = (key or "").strip().lower()

        if normalized_key == "recent_conversation":
            return self._compress_memory(value)
        if "knowledge_graph" in normalized_key:
            return self._compress_graph(value)
        if normalized_key in _TIMELINE_KEYS:
            return self._compress_list(value, self._limits.max_timeline_entries)
        if isinstance(value, list):
            return self._compress_list(value, self._limits.max_list_entries)
        if isinstance(value, dict):
            return self._clean_dict(value)
        if isinstance(value, str):
            return _truncate(value, self._limits.max_string_chars)
        return value

    def _compress_memory(self, turns: Any) -> List[Dict[str, Any]]:
        """Keep what the model previously concluded; drop what it was asked.

        The replayed `prompt_rendered` is the single largest source of token
        waste in the system — it is the patient context the model is already
        being given fresh in this very request.
        """
        if not isinstance(turns, list):
            return []
        compact: List[Dict[str, Any]] = []
        for turn in turns[: self._limits.max_memory_turns]:
            if not isinstance(turn, dict):
                continue
            summary = turn.get("response_text") or ""
            if isinstance(turn.get("response_json"), dict):
                # Structured output is denser than the raw text form.
                summary = _stringify(turn["response_json"])
            compact.append(
                {
                    "task": turn.get("task") or "",
                    "when": turn.get("created_at") or "",
                    "summary": _truncate(summary, self._limits.max_memory_summary_chars),
                }
            )
        return [t for t in compact if t["summary"]]

    def _compress_graph(self, graph: Any) -> Any:
        """Keep the strongest signal in the knowledge graph and drop the rest.

        Graphs grow monotonically as a patient accumulates history, but the
        highest-weight nodes and edges carry nearly all the clinical meaning.
        """
        if not isinstance(graph, dict):
            return self._compress_value("", graph)

        compressed = dict(graph)
        for collection, cap in (
            ("nodes", self._limits.max_graph_nodes),
            ("edges", self._limits.max_graph_edges),
            ("relationships", self._limits.max_graph_edges),
        ):
            items = compressed.get(collection)
            if not isinstance(items, list):
                continue
            ranked = sorted(
                (i for i in items if isinstance(i, dict)),
                key=_weight_of,
                reverse=True,
            )
            compressed[collection] = [self._clean_dict(i) for i in ranked[:cap]]
        return self._clean_dict(compressed)

    def _compress_list(self, value: Any, cap: int) -> Any:
        if not isinstance(value, list):
            return value
        deduped = _dedupe(value)
        # Lists in this system are ordered most-recent-first, so the head is
        # the clinically relevant tail of the patient's history.
        trimmed = deduped[:cap]
        return [
            self._clean_dict(item)
            if isinstance(item, dict)
            else (
                _truncate(item, self._limits.max_string_chars)
                if isinstance(item, str)
                else item
            )
            for item in trimmed
        ]

    def _clean_dict(self, value: Dict[str, Any]) -> Dict[str, Any]:
        cleaned: Dict[str, Any] = {}
        for key, item in value.items():
            if str(key).strip().lower() in _NOISE_KEYS:
                continue
            if _is_empty(item):
                continue
            if isinstance(item, dict):
                nested = self._clean_dict(item)
                if nested:
                    cleaned[key] = nested
            elif isinstance(item, list):
                cleaned[key] = self._compress_list(item, self._limits.max_list_entries)
            elif isinstance(item, str):
                cleaned[key] = _truncate(item, self._limits.max_string_chars)
            else:
                cleaned[key] = item
        return cleaned


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _normalize(text: str) -> str:
    return _WHITESPACE.sub(" ", str(text)).strip().lower().rstrip(".")


def _dedupe(items: List[Any]) -> List[Any]:
    """Order-preserving dedupe that also catches near-duplicates differing
    only by whitespace, casing, or a trailing period."""
    seen: set[str] = set()
    unique: List[Any] = []
    for item in items:
        fingerprint = _normalize(_stringify(item))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique.append(item)
    return unique


def _weight_of(item: Dict[str, Any]) -> float:
    for key in ("weight", "score", "relevance", "confidence", "strength"):
        value = item.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (str, list, dict, tuple, set)):
        return len(value) == 0
    return False


def _truncate(text: Any, limit: int) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _halve(value: Any) -> Any:
    """Roughly halve a collection, keeping the head.

    Lists in this system are ordered most-relevant-first (recent history,
    highest-weight graph nodes, top-ranked evidence), so the head is what a
    clinician would keep. For dicts the biggest value is halved recursively
    rather than dropping keys, since a missing key can break prompt
    interpolation while a shorter value cannot.
    """
    if isinstance(value, list):
        if len(value) <= 1:
            # A single oversized element: shorten its content instead.
            return [_halve(value[0])] if value else value
        return value[: max(1, len(value) // 2)]
    if isinstance(value, dict):
        if not value:
            return value
        biggest = max(value, key=lambda k: _rough_size(value[k]))
        trimmed = dict(value)
        trimmed[biggest] = _halve(trimmed[biggest])
        return trimmed
    if isinstance(value, str):
        return _truncate(value, max(200, len(value) // 2))
    return value


def _stringify(value: Any) -> str:
    import json

    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str, separators=(",", ":"))
    except Exception:  # noqa: BLE001
        return str(value)


def _rough_size(value: Any) -> int:
    return len(_stringify(value))


_compressor: Optional[ContextCompressor] = None


def get_context_compressor() -> ContextCompressor:
    global _compressor
    if _compressor is None:
        _compressor = ContextCompressor()
    return _compressor
