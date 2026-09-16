"""Medical Report Agent — Stage 1: Clinical Summary."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from app.ai.medical_report.models import ClinicalSummary
from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.repositories.patient_context_repository import PatientClinicalContext


class ClinicalSummaryGenerator(OrchestratorCallMixin):
    """Generates the clinical summary via the AI Orchestrator (`medical_report` agent, `clinical_summary` task)."""

    def generate(
        self,
        context: PatientClinicalContext,
        diagnosis_row: Optional[Dict[str, Any]],
    ) -> ClinicalSummary:
        data = self._call(
            agent="medical_report",
            task="clinical_summary",
            patient_id=UUID(context.patient_id),
            response_model=ClinicalSummary,
            extra_vars={"recent_diagnosis": diagnosis_row or {}},
        )
        return ClinicalSummary.model_validate(data)
