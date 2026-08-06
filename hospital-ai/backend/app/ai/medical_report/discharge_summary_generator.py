"""Medical Report Agent — Stage 3: Discharge Summary."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from app.ai.medical_report.models import DischargeSummary
from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.repositories.patient_context_repository import PatientClinicalContext


class DischargeSummaryGenerator(OrchestratorCallMixin):
    """Generates the discharge summary via the AI Orchestrator (`medical_report` agent, `discharge_summary` task)."""

    def generate(
        self,
        context: PatientClinicalContext,
        diagnosis_row: Optional[Dict[str, Any]],
        prescription_row: Optional[Dict[str, Any]],
    ) -> DischargeSummary:
        data = self._call(
            agent="medical_report",
            task="discharge_summary",
            patient_id=UUID(context.patient_id),
            response_model=DischargeSummary,
            extra_vars={
                "recent_diagnosis": diagnosis_row or {},
                "recent_prescription": prescription_row or {},
            },
        )
        return DischargeSummary.model_validate(data)
