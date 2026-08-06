"""
Medical Report Agent — Stage 5: Insurance Documentation.

Prepares diagnosis codes, procedure codes, supporting documents, medical
necessity, and claim summary via the AI Orchestrator (`medical_report`
agent, `insurance_documentation` task). This is ILLUSTRATIVE
documentation only — a certified medical coder must verify before any
claim submission (see the prompt's explicit disclaimer).
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.medical_report.models import InsuranceDocumentation
from app.ai.orchestrator.agent_helpers import OrchestratorCallMixin
from app.repositories.patient_context_repository import PatientClinicalContext


class _InsuranceLLMResponse(BaseModel):
    """The prompt returns flat code lists; mapped into the model's dict-list shape below."""

    diagnosis_codes: list[str] = Field(default_factory=list)
    procedure_codes: list[str] = Field(default_factory=list)
    supporting_documents: list[str] = Field(default_factory=list)
    medical_necessity: str = ""
    claim_summary: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)


class InsuranceDocumentationGenerator(OrchestratorCallMixin):
    def generate(
        self,
        context: PatientClinicalContext,
        diagnosis_row: Optional[Dict[str, Any]],
        research_row: Optional[Dict[str, Any]],
    ) -> InsuranceDocumentation:
        treatment_path = (diagnosis_row or {}).get("treatment_path_json") or {}
        procedures = list(treatment_path.get("diagnostic_tests") or []) + list(
            treatment_path.get("imaging") or []
        )
        data = self._call(
            agent="medical_report",
            task="insurance_documentation",
            patient_id=UUID(context.patient_id),
            response_model=_InsuranceLLMResponse,
            extra_vars={
                "recent_diagnosis": diagnosis_row or {},
                "procedures": procedures,
            },
        )
        parsed = _InsuranceLLMResponse.model_validate(data)
        return InsuranceDocumentation(
            diagnosis_codes=[{"code": c} for c in parsed.diagnosis_codes] or [
                {"code": "Pending coder verification"}
            ],
            procedure_codes=[{"code": c} for c in parsed.procedure_codes] or [
                {"code": "Pending coder verification"}
            ],
            supporting_documents=parsed.supporting_documents or ["Clinical Summary", "Doctor Notes"],
            medical_necessity=parsed.medical_necessity,
            claim_summary=parsed.claim_summary,
            supporting_evidence=parsed.supporting_evidence
            or ["No Research Agent evidence on record for this encounter."],
        )
