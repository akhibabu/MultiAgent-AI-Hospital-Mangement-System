"""Small shared helpers used across the AI Orchestrator subsystems."""
from __future__ import annotations

import hashlib


def stable_hash(*parts: str) -> str:
    """Deterministic hash used for cache keys and prompt versioning."""
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def truncate(text: str, max_len: int = 4000) -> str:
    if not text:
        return ""
    return text if len(text) <= max_len else text[: max_len - 3] + "..."
