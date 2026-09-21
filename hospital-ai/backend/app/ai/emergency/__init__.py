"""Emergency Agent package.

Deterministic, explainable emergency decision-support components.
The v1 implementation intentionally avoids external LLM calls so critical
threshold detection remains reproducible and auditable.
"""

from app.ai.emergency.pipeline import EmergencyPipeline

__all__ = ["EmergencyPipeline"]
