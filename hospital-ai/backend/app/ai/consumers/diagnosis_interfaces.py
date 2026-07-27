"""Diagnosis Agent consumer interfaces — Intake output only. Do not implement Diagnosis."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel, Field

from app.ai.intake.patient_context import PatientContext


class DiagnosisRequest(BaseModel):
    """Payload Diagnosis Agent will accept — built from PatientContext only."""

    patient_context: PatientContext
    chief_complaint: Optional[str] = None
    focus_symptoms: List[str] = Field(default_factory=list)


class DiagnosisHypothesis(BaseModel):
    condition: str
    confidence: float
    supporting_evidence: List[str] = Field(default_factory=list)


class DiagnosisResult(BaseModel):
    """Placeholder result shape for future Diagnosis Agent."""

    hypotheses: List[DiagnosisHypothesis] = Field(default_factory=list)
    recommended_tests: List[str] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)
    narrative: Optional[str] = None


class DiagnosisAgentConsumer(Protocol):
    """
    Interface that Diagnosis Agent must implement.

    It MUST NOT read raw documents or call OCR — only PatientContext.
    """

    def diagnose(self, request: DiagnosisRequest) -> DiagnosisResult: ...


class DiagnosisAgentNotImplemented:
    """Stub so Intake can export a stable DI point."""

    def diagnose(self, request: DiagnosisRequest) -> DiagnosisResult:
        raise NotImplementedError(
            "Diagnosis Agent is not implemented yet. "
            "Consume PatientContext via DiagnosisRequest when Week 2 starts."
        )


def build_diagnosis_request_from_context(
    context: PatientContext,
    *,
    chief_complaint: Optional[str] = None,
) -> DiagnosisRequest:
    """Helper for future Diagnosis Agent wiring."""
    return DiagnosisRequest(
        patient_context=context,
        chief_complaint=chief_complaint,
        focus_symptoms=list(context.current_symptoms),
    )


def patient_context_as_agent_input(context: PatientContext) -> Dict[str, Any]:
    """Serialize canonical context for any downstream agent."""
    return context.to_dict()
