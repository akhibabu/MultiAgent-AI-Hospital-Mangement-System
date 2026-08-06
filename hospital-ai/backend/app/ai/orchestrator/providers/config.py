"""
Provider fleet configuration — loads and validates `providers.yaml`.

This is the boundary between "how the fleet is declared" (YAML, reviewable,
env-interpolated) and "how the fleet is used" (typed objects consumed by
`ProviderRouter`, `ProviderOrchestrator`, `LoadBalancer`, and
`ProviderHealthMonitor`).

Design notes
------------
* **No hardcoded fleet.** The provider list, their priorities, base URLs,
  models, capabilities, and pricing all come from YAML. If the file is
  missing or malformed the loader falls back to a minimal single-provider
  fleet derived from `Settings` so the API still boots — a misconfigured
  YAML must never take the hospital system offline.
* **Secrets never live in YAML.** Values are written as `${GROQ_API_KEY}`
  and resolved from the process environment at load time. `.env` is loaded
  by pydantic-settings before this runs, so `.env` values are visible here.
* **Everything is immutable after load** (frozen dataclasses) and cached, so
  callers can hold references without worrying about mutation.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger

logger = get_logger("hospital_ai.orchestrator.providers.config")

# Matches ${VAR} and ${VAR:-fallback}. The fallback may itself contain any
# character except a closing brace, which covers URLs, model ids, and numbers.
_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off", ""}


# ---------------------------------------------------------------------------
# Typed configuration objects
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ProviderCapabilities:
    """What a provider can do — surfaced through `BaseAIProvider.supports_*()`."""

    streaming: bool = False
    vision: bool = False
    long_context: bool = False


@dataclass(frozen=True)
class ProviderLimits:
    """How much a provider will accept in a single request.

    `max_request_tokens` is the ceiling on `prompt_tokens + max_tokens`,
    because that sum — not the prompt alone — is what providers meter. Groq's
    free tier is the clearest example: a 6 000 token-per-minute allowance
    against a default 4 096-token completion reservation leaves under 2 000
    tokens for the actual prompt, and exceeding it returns HTTP 413 rather
    than truncating.

    `0` means "no declared limit", which is how every provider behaved before
    this existed and remains the safe default for one we haven't measured.
    """

    max_request_tokens: int = 0
    #: Never shrink a completion below this — a reply truncated mid-JSON is
    #: worse than a clean failover, since it surfaces as a parse error.
    min_completion_tokens: int = 700

    @property
    def declared(self) -> bool:
        return self.max_request_tokens > 0

    def fits(self, prompt_tokens: int) -> bool:
        """Can this provider serve `prompt_tokens` and still say something useful?"""
        if not self.declared:
            return True
        return prompt_tokens + self.min_completion_tokens <= self.max_request_tokens

    def completion_budget(self, prompt_tokens: int, requested: int) -> int:
        """Largest completion this provider will accept alongside the prompt."""
        if not self.declared:
            return requested
        return min(requested, max(0, self.max_request_tokens - prompt_tokens))

    def prompt_budget_tokens(self, requested_completion: int) -> int:
        """Room left for the prompt once a completion is reserved."""
        if not self.declared:
            return 0
        reserved = max(self.min_completion_tokens, min(requested_completion, self.max_request_tokens))
        return max(0, self.max_request_tokens - reserved)


@dataclass(frozen=True)
class ProviderPricing:
    """USD per 1M tokens. Estimates for the dashboard only, never billing."""

    input_per_1m: float = 0.0
    output_per_1m: float = 0.0

    def estimate(self, prompt_tokens: int, completion_tokens: int) -> float:
        cost = (prompt_tokens / 1_000_000) * self.input_per_1m + (
            completion_tokens / 1_000_000
        ) * self.output_per_1m
        return round(cost, 6)


@dataclass(frozen=True)
class ProviderConfig:
    """One entry from the `providers:` block of `providers.yaml`."""

    name: str
    enabled: bool = False
    priority: int = 100
    api_key: str = ""
    base_url: str = ""
    timeout_seconds: float = 120.0
    console_url: str = ""
    requires_api_key: bool = True
    exclude_from_failover: bool = False
    models: Dict[str, str] = field(default_factory=dict)
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)
    pricing: ProviderPricing = field(default_factory=ProviderPricing)
    limits: ProviderLimits = field(default_factory=ProviderLimits)
    extra: Dict[str, str] = field(default_factory=dict)

    @property
    def configured(self) -> bool:
        """True when this provider has everything it needs to be called.

        A provider missing its API key is not an error — it just means the
        operator hasn't set that one up, so the fleet silently routes around
        it. This is what lets a teammate run the system with only a Groq key.
        """
        if not self.enabled:
            return False
        if self.requires_api_key and not self.api_key:
            return False
        return bool(self.base_url) or not self.requires_api_key

    @property
    def eligible_for_failover(self) -> bool:
        return self.configured and not self.exclude_from_failover

    def model_for(self, agent: str) -> str:
        """Model this provider should use for `agent`, falling back to its
        `models.default`. Keeps per-agent model routing working across every
        provider in the failover chain — Groq's diagnosis model and Gemini's
        diagnosis model can differ without any agent knowing."""
        key = (agent or "").strip().lower()
        return self.models.get(key) or self.models.get("default") or ""

    def redacted(self) -> Dict[str, Any]:
        """Safe-for-API view. The API key is NEVER serialized — the frontend
        only learns whether a credential is present, never its value."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "priority": self.priority,
            "configured": self.configured,
            "has_api_key": bool(self.api_key) or not self.requires_api_key,
            "requires_api_key": self.requires_api_key,
            "base_url": self.base_url,
            "console_url": self.console_url,
            "timeout_seconds": self.timeout_seconds,
            "models": dict(self.models),
            "capabilities": {
                "streaming": self.capabilities.streaming,
                "vision": self.capabilities.vision,
                "long_context": self.capabilities.long_context,
            },
            "pricing": {
                "input_per_1m": self.pricing.input_per_1m,
                "output_per_1m": self.pricing.output_per_1m,
            },
            "limits": {
                "max_request_tokens": self.limits.max_request_tokens,
                "min_completion_tokens": self.limits.min_completion_tokens,
            },
        }


@dataclass(frozen=True)
class RoutingConfig:
    strategy: str = "priority"
    max_providers_per_request: int = 4


@dataclass(frozen=True)
class HealthConfig:
    failure_threshold: int = 3
    warning_error_rate: float = 0.25
    cooldown_seconds: float = 120.0
    quota_cooldown_seconds: float = 900.0
    sample_window: int = 50


@dataclass(frozen=True)
class FleetConfig:
    """The whole `providers.yaml`, parsed and validated."""

    routing: RoutingConfig = field(default_factory=RoutingConfig)
    health: HealthConfig = field(default_factory=HealthConfig)
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    source_path: str = ""
    load_error: Optional[str] = None

    def get(self, name: str) -> Optional[ProviderConfig]:
        return self.providers.get((name or "").strip().lower())

    def ordered(self) -> List[ProviderConfig]:
        """All declared providers sorted by priority (1 first), name as tiebreak."""
        return sorted(self.providers.values(), key=lambda p: (p.priority, p.name))

    def failover_chain(self) -> List[ProviderConfig]:
        """Configured, non-excluded providers in priority order — the default
        candidate list the LoadBalancer reorders according to its strategy."""
        return [p for p in self.ordered() if p.eligible_for_failover]


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
def _env_sources() -> Dict[str, str]:
    """Variable lookup table for `${VAR}` interpolation.

    pydantic-settings reads `backend/.env` into the `Settings` object without
    exporting anything to `os.environ`, so reading the process environment
    alone would silently miss every key a developer put in `.env`. We merge
    both, with the real environment taking precedence (so a shell export or a
    container secret always overrides a checked-out `.env`).
    """
    merged: Dict[str, str] = {}

    env_file = _default_config_path().with_name(".env")
    if env_file.exists():
        try:
            from dotenv import dotenv_values

            merged.update(
                {
                    k: v
                    for k, v in dotenv_values(env_file, encoding="utf-8").items()
                    if v is not None
                }
            )
        except Exception as exc:  # noqa: BLE001 - a bad .env must not break boot
            logger.warning("Could not read %s for provider interpolation: %s", env_file, exc)

    merged.update(os.environ)
    return merged


def _interpolate(value: Any, env: Dict[str, str]) -> Any:
    """Recursively resolve `${VAR}` / `${VAR:-fallback}` against `env`."""
    if isinstance(value, str):

        def _sub(match: re.Match) -> str:
            var, fallback = match.group(1), match.group(2)
            resolved = env.get(var)
            if resolved is None or resolved == "":
                return fallback if fallback is not None else ""
            return resolved

        return _ENV_PATTERN.sub(_sub, value)
    if isinstance(value, dict):
        return {k: _interpolate(v, env) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate(v, env) for v in value]
    return value


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in _TRUTHY:
        return True
    if text in _FALSY:
        return False
    return default


def _as_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _parse_provider(name: str, raw: Dict[str, Any]) -> ProviderConfig:
    caps = raw.get("capabilities") or {}
    pricing = raw.get("pricing") or {}
    limits = raw.get("limits") or {}
    models_raw = raw.get("models") or {}
    models = {
        str(k).strip().lower(): str(v).strip()
        for k, v in models_raw.items()
        if v is not None and str(v).strip()
    }
    extra = {
        str(k): str(v)
        for k, v in (raw.get("extra") or {}).items()
        if v is not None and str(v).strip()
    }
    return ProviderConfig(
        name=name,
        enabled=_as_bool(raw.get("enabled"), False),
        priority=_as_int(raw.get("priority"), 100),
        api_key=str(raw.get("api_key") or "").strip(),
        base_url=str(raw.get("base_url") or "").strip(),
        timeout_seconds=_as_float(raw.get("timeout_seconds"), 120.0),
        console_url=str(raw.get("console_url") or "").strip(),
        requires_api_key=_as_bool(raw.get("requires_api_key"), True),
        exclude_from_failover=_as_bool(raw.get("exclude_from_failover"), False),
        models=models,
        capabilities=ProviderCapabilities(
            streaming=_as_bool(caps.get("streaming"), False),
            vision=_as_bool(caps.get("vision"), False),
            long_context=_as_bool(caps.get("long_context"), False),
        ),
        pricing=ProviderPricing(
            input_per_1m=_as_float(pricing.get("input_per_1m"), 0.0),
            output_per_1m=_as_float(pricing.get("output_per_1m"), 0.0),
        ),
        limits=ProviderLimits(
            max_request_tokens=max(0, _as_int(limits.get("max_request_tokens"), 0)),
            min_completion_tokens=max(
                128, _as_int(limits.get("min_completion_tokens"), 700)
            ),
        ),
        extra=extra,
    )


def _honor_pinned_provider(providers: Dict[str, ProviderConfig]) -> None:
    """Force-enable the provider named by `AI_PROVIDER`, in place.

    Explicitly selecting a provider is an unambiguous statement of intent, and
    silently routing elsewhere because a YAML flag says `enabled: false` is a
    genuinely confusing failure — `AI_PROVIDER=stub` would quietly call the
    network, and `AI_PROVIDER=ollama` would quietly use Groq. Both providers
    ship disabled so they stay out of the automatic failover chain, so this
    rule is what makes pinning them work as written.
    """
    from app.config import get_settings

    try:
        pinned = (getattr(get_settings(), "ai_provider", "") or "").strip().lower()
    except Exception:  # noqa: BLE001 - settings problems surface elsewhere
        return

    config = providers.get(pinned)
    if config is None or config.enabled:
        return

    providers[pinned] = replace(config, enabled=True)
    logger.info(
        "Provider '%s' is disabled in providers.yaml but is pinned via "
        "AI_PROVIDER — enabling it for this process.",
        pinned,
    )


def _default_config_path() -> Path:
    """`backend/providers.yaml` — this module lives at
    backend/app/ai/orchestrator/providers/config.py, so the backend root is
    four directories up."""
    return Path(__file__).resolve().parents[4] / "providers.yaml"


def _fallback_fleet(reason: str) -> FleetConfig:
    """Minimal single-provider fleet derived from `Settings`.

    Used only when `providers.yaml` is missing or unparseable. Failover is
    unavailable in this mode, but the system still serves requests through
    whatever `AI_PROVIDER` points at — degraded, never down.
    """
    from app.config import get_settings

    settings = get_settings()
    name = (getattr(settings, "ai_provider", "groq") or "groq").strip().lower()
    model = getattr(settings, "diagnosis_model", "") or "llama-3.3-70b-versatile"
    api_key = getattr(settings, f"{name}_api_key", "") or getattr(settings, "groq_api_key", "")
    base_url = getattr(settings, f"{name}_base_url", "") or getattr(
        settings, "groq_base_url", ""
    )
    logger.warning(
        "providers.yaml unavailable (%s) — falling back to a single-provider "
        "fleet (%s). Automatic failover is DISABLED until the file is fixed.",
        reason,
        name,
    )
    return FleetConfig(
        providers={
            name: ProviderConfig(
                name=name,
                enabled=True,
                priority=1,
                api_key=api_key,
                base_url=base_url,
                timeout_seconds=getattr(settings, "ai_timeout_seconds", 120.0),
                requires_api_key=name not in {"ollama", "stub"},
                models={"default": model},
                capabilities=ProviderCapabilities(streaming=True, long_context=True),
            )
        },
        load_error=reason,
    )


# ---------------------------------------------------------------------------
# Public loader
# ---------------------------------------------------------------------------
def load_fleet_config(path: Optional[str | Path] = None) -> FleetConfig:
    """Parse `providers.yaml` into a `FleetConfig`. Never raises."""
    config_path = Path(path) if path else _default_config_path()

    try:
        import yaml
    except ImportError:  # pragma: no cover - PyYAML ships with uvicorn[standard]
        return _fallback_fleet("PyYAML is not installed (pip install PyYAML)")

    if not config_path.exists():
        return _fallback_fleet(f"{config_path} not found")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001 - a bad YAML must not break boot
        return _fallback_fleet(f"could not parse {config_path}: {exc}")

    raw = _interpolate(raw, _env_sources())
    providers_raw = raw.get("providers") or {}
    if not isinstance(providers_raw, dict) or not providers_raw:
        return _fallback_fleet(f"{config_path} declares no providers")

    providers: Dict[str, ProviderConfig] = {}
    for name, block in providers_raw.items():
        if not isinstance(block, dict):
            logger.warning("Skipping malformed provider block '%s' in %s", name, config_path)
            continue
        key = str(name).strip().lower()
        providers[key] = _parse_provider(key, block)

    _honor_pinned_provider(providers)

    routing_raw = raw.get("routing") or {}
    health_raw = raw.get("health") or {}

    fleet = FleetConfig(
        routing=RoutingConfig(
            strategy=str(routing_raw.get("strategy") or "priority").strip().lower(),
            max_providers_per_request=max(
                1, _as_int(routing_raw.get("max_providers_per_request"), 4)
            ),
        ),
        health=HealthConfig(
            failure_threshold=max(1, _as_int(health_raw.get("failure_threshold"), 3)),
            warning_error_rate=_as_float(health_raw.get("warning_error_rate"), 0.25),
            cooldown_seconds=_as_float(health_raw.get("cooldown_seconds"), 120.0),
            quota_cooldown_seconds=_as_float(
                health_raw.get("quota_cooldown_seconds"), 900.0
            ),
            sample_window=max(5, _as_int(health_raw.get("sample_window"), 50)),
        ),
        providers=providers,
        source_path=str(config_path),
    )

    usable = [p.name for p in fleet.failover_chain()]
    logger.info(
        "Loaded AI provider fleet from %s — strategy=%s, usable=%s",
        config_path,
        fleet.routing.strategy,
        ", ".join(usable) if usable else "NONE (no credentials configured)",
    )
    return fleet


_fleet: Optional[FleetConfig] = None


def get_fleet_config() -> FleetConfig:
    """Process-wide cached fleet configuration."""
    global _fleet
    if _fleet is None:
        _fleet = load_fleet_config()
    return _fleet


def reload_fleet_config(path: Optional[str | Path] = None) -> FleetConfig:
    """Re-read `providers.yaml` (used by tests and the admin reload endpoint)."""
    global _fleet
    _fleet = load_fleet_config(path)
    return _fleet
