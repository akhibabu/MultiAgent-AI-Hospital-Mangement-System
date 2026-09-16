"""Medical Report Agent — Stage 4: Referral Letter Creation."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional
from uuid import UUID

from app.ai.medical_report.models import ReferralLetter
from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.repositories.patient_context_repository import PatientClinicalContext


class ReferralLetterGenerator(OrchestratorCallMixin):
    """Generates a referral letter via the AI Orchestrator (`medical_report` agent, `referral_letter` task)."""

    def generate(
        self,
        context: PatientClinicalContext,
        diagnosis_row: Optional[Dict[str, Any]],
        *,
        receiving_specialist: Optional[str] = None,
    ) -> ReferralLetter:
        treatment_path = (diagnosis_row or {}).get("treatment_path_json") or {}
        specialists = treatment_path.get("recommended_specialists") or []
        default_specialist = receiving_specialist or (specialists[0] if specialists else "General Physician")

        data = self._call(
            agent="medical_report",
            task="referral_letter",
            patient_id=UUID(context.patient_id),
            response_model=ReferralLetter,
            extra_vars={
                "recent_diagnosis": diagnosis_row or {},
                "recommended_specialists": [default_specialist] + specialists,
            },
        )
        letter = ReferralLetter.model_validate(data)
        letter.receiving_specialist = letter.receiving_specialist or default_specialist
        if not letter.letter_body:
            letter.letter_body = (
                f"Date: {date.today().isoformat()}\n\nTo: {letter.receiving_specialist}\n\n"
                f"Re: {context.patient_name}\n\n{letter.reason}\n\n{letter.history}"
            )
        return letter
