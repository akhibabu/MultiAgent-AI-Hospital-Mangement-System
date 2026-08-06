"""
Medical Report Agent — Stage 6: Patient Report Generation.

Plain-language, patient-friendly report via the AI Orchestrator
(`medical_report` agent, `patient_report` task). No medical jargon.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from app.ai.medical_report.models import PatientReport
from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.repositories.patient_context_repository import PatientClinicalContext


class PatientReportGenerator(OrchestratorCallMixin):
    def generate(
        self,
        context: PatientClinicalContext,
        diagnosis_row: Optional[Dict[str, Any]],
        prescription_row: Optional[Dict[str, Any]],
    ) -> PatientReport:
        data = self._call(
            agent="medical_report",
            task="patient_report",
            patient_id=UUID(context.patient_id),
            response_model=PatientReport,
            extra_vars={
                "recent_diagnosis": diagnosis_row or {},
                "recent_prescription": prescription_row or {},
            },
        )
        return PatientReport.model_validate(data)
