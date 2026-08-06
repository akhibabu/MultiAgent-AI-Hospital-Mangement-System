"""Medical Report Agent — Stage 2: Doctor Notes Generation (SOAP)."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from app.ai.medical_report.models import DoctorNotes
from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.repositories.patient_context_repository import PatientClinicalContext


class DoctorNotesGenerator(OrchestratorCallMixin):
    """Generates SOAP-format doctor notes via the AI Orchestrator (`medical_report` agent, `doctor_notes` task)."""

    def generate(
        self,
        context: PatientClinicalContext,
        diagnosis_row: Optional[Dict[str, Any]],
    ) -> DoctorNotes:
        data = self._call(
            agent="medical_report",
            task="doctor_notes",
            patient_id=UUID(context.patient_id),
            response_model=DoctorNotes,
            extra_vars={"recent_diagnosis": diagnosis_row or {}},
        )
        return DoctorNotes.model_validate(data)
