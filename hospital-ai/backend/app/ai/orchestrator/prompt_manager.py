"""
PromptManager — loads, caches, versions, and renders markdown prompt
templates. Prompts are NEVER hardcoded inside Python.

Layout: `app/ai/orchestrator/prompts/<agent>/<task>.md`
Optional shared `app/ai/orchestrator/prompts/<agent>/system.md` is sent as
the `system` role message for every task belonging to that agent.

- Loads: reads the `.md` file for (agent, task).
- Caches: keeps file contents in-process keyed by (path, mtime) so a
  prompt edit is picked up without a backend restart, but a hot loop
  doesn't re-read disk on every call.
- Versions: a short content hash of the task template, surfaced in
  Developer Mode so the team can tell which prompt revision produced a
  given response.
- Variables: simple `{{variable}}` interpolation — no extra templating
  dependency needed for this project's scope.
"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any, Dict, Tuple

from app.ai.orchestrator.interfaces import IPromptManager
from app.ai.orchestrator.utils import stable_hash

_PROMPTS_ROOT = Path(__file__).resolve().parent / "prompts"
_VAR_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")

_DEFAULT_SYSTEM_PROMPT = (
    "You are a clinical decision-support AI assistant embedded in a "
    "hospital management system. You ALWAYS respond with strict JSON "
    "only — no markdown, no prose outside the JSON object — matching "
    "the schema requested in the task prompt. You assist clinicians; "
    "you NEVER claim diagnostic or prescribing certainty, you always "
    "include confidence scores and supporting evidence, and you never "
    "replace a physician's judgment."
)


class PromptNotFoundError(FileNotFoundError):
    pass


class PromptManager(IPromptManager):
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or _PROMPTS_ROOT
        self._lock = threading.Lock()
        self._cache: Dict[str, Tuple[float, str]] = {}

    def _read(self, agent: str, task: str) -> str:
        path = self._root / agent / f"{task}.md"
        if not path.exists():
            raise PromptNotFoundError(
                f"Prompt template not found: {path}. Create it under "
                f"app/ai/orchestrator/prompts/{agent}/{task}.md"
            )
        mtime = path.stat().st_mtime
        cache_key = str(path)
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached and cached[0] == mtime:
                return cached[1]
        text = path.read_text(encoding="utf-8")
        with self._lock:
            self._cache[cache_key] = (mtime, text)
        return text

    @staticmethod
    def _interpolate(template: str, variables: Dict[str, Any]) -> str:
        def _sub(match: "re.Match[str]") -> str:
            key = match.group(1)
            value = variables.get(key)
            if value is None:
                return ""
            if isinstance(value, (dict, list)):
                return json.dumps(value, default=str)
            return str(value)

        return _VAR_PATTERN.sub(_sub, template)

    def render(
        self, agent: str, task: str, variables: Dict[str, Any]
    ) -> Tuple[str, str, str]:
        task_template = self._read(agent, task)
        try:
            system_template = self._read(agent, "system")
        except PromptNotFoundError:
            system_template = _DEFAULT_SYSTEM_PROMPT

        version = stable_hash(task_template)[:10]
        system_prompt = self._interpolate(system_template, variables)
        rendered_prompt = self._interpolate(task_template, variables)
        return system_prompt, rendered_prompt, version

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()


_prompt_manager: PromptManager | None = None


def get_prompt_manager() -> PromptManager:
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
