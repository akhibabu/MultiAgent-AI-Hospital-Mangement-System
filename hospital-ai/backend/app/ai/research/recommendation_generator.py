"""Research Agent — Step 6: Recommendation Generation."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.ai.research.models import RankedEvidence, ResearchRecommendation


class RecommendationGenerator(OrchestratorCallMixin):
    """
    Synthesizes ranked evidence into a clinician-friendly recommendation
    via the AI Orchestrator (`research` agent,
    `recommendation_generation` task).
    """

    def __init__(self, patient_id: Optional[UUID] = None) -> None:
        self._patient_id = patient_id

    def generate(
        self, condition: str, evidence: List[RankedEvidence]
    ) -> ResearchRecommendation:
        condition_evidence = [e for e in evidence if e.condition == condition]
        data = self._call(
            agent="research",
            task="recommendation_generation",
            patient_id=self._patient_id,
            response_model=ResearchRecommendation,
            extra_vars={
                "condition": condition,
                "condition_evidence": [e.model_dump(mode="json") for e in condition_evidence],
            },
        )
        return ResearchRecommendation.model_validate(data)
