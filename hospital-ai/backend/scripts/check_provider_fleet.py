"""
Diagnostic: print the resolved AI provider fleet.

Answers "which providers will actually serve traffic, in what order, and
why is one of them being skipped" without starting the API or spending a
single token. Run from `backend/`:

    python scripts/check_provider_fleet.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.orchestrator.load_balancer import get_load_balancer  # noqa: E402
from app.ai.orchestrator.provider_orchestrator import (  # noqa: E402
    get_provider_orchestrator,
)
from app.ai.orchestrator.provider_router import get_provider_router  # noqa: E402
from app.ai.orchestrator.providers.config import get_fleet_config  # noqa: E402
from app.ai.orchestrator.router import get_model_router  # noqa: E402


def main() -> int:
    fleet = get_fleet_config()
    router = get_provider_router()
    balancer = get_load_balancer()

    print("=" * 78)
    print("AI PROVIDER FLEET")
    print("=" * 78)
    print(f"config file : {fleet.source_path or '(none — using fallback)'}")
    if fleet.load_error:
        print(f"LOAD ERROR  : {fleet.load_error}")
    print(f"strategy    : {fleet.routing.strategy}")
    print(f"max chain   : {fleet.routing.max_providers_per_request}")
    print(f"adapters    : {', '.join(router.registered_adapters())}")
    print()

    print(f"{'PROVIDER':<16}{'ENABLED':<9}{'PRIO':<6}{'KEY':<6}{'USABLE':<8}MODEL (diagnosis)")
    print("-" * 78)
    for config in fleet.ordered():
        has_key = "yes" if (config.api_key or not config.requires_api_key) else "no"
        print(
            f"{config.name:<16}"
            f"{str(config.enabled).lower():<9}"
            f"{config.priority:<6}"
            f"{has_key:<6}"
            f"{str(config.configured).lower():<8}"
            f"{config.model_for('diagnosis') or '-'}"
        )
    print()

    chain = balancer.select()
    if chain:
        print("FAILOVER ORDER for a diagnosis request:")
        model_router = get_model_router()
        for position, config in enumerate(chain, start=1):
            label = "primary" if position == 1 else f"fallback {position - 1}"
            model = model_router.resolve_for_provider("diagnosis", config.name)
            print(f"  {position}. {config.name:<14} ({label})  ->  {model}")
    else:
        print("NO PROVIDER IS USABLE.")
        print("Set at least one API key in backend/.env:")
        for config in fleet.ordered():
            if config.requires_api_key and config.enabled and not config.api_key:
                print(f"  {config.name.upper()}_API_KEY   {config.console_url}")
        return 1

    print()
    print("Fleet snapshot (as served to the dashboard):")
    for row in get_provider_orchestrator().fleet_snapshot():
        position = row["failover_position"]
        print(
            f"  {row['name']:<16} status={row['health']['status']:<8}"
            f" chain_position={position if position else '-'}"
            f" streaming={row['capabilities']['streaming']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
