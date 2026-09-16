"""
ContextManager — assembles every variable an AI Agent's prompts may need.

Centralizes what used to be manually re-assembled per agent: Patient
Context, Knowledge Graph, Medical History, Timeline, Risk Profile,
Medical Entities, Recent Diagnoses, Recent Research. AI Agents pass only
`patient_id` (+ small task-specific `extra_vars`) into
`AIOrchestrator.run()` — they never build prompt context themselves.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from app.ai.orchestrator.interfaces import IContextManager
from app.core.logging import get_logger
from app.repositories.diagnosis_repository import DiagnosisResultRepository
from app.repositories.patient_context_repository import (
    PatientClinicalContextRepository,
)
from app.repositories.research_repository import ResearchResultRepository

logger = get_logger("hospital_ai.orchestrator.context")


class ContextManager(IContextManager):
    def __init__(
        self,
        *,
        context_repo: Optional[PatientClinicalContextRepository] = None,
        diagnosis_repo: Optional[DiagnosisResultRepository] = None,
        research_repo: Optional[ResearchResultRepository] = None,
    ) -> None:
        self._context_repo = context_repo or PatientClinicalContextRepository()
        self._diagnosis_repo = diagnosis_repo or DiagnosisResultRepository()
        self._research_repo = research_repo or ResearchResultRepository()

    def build(
        self,
        agent: str,
        patient_id: Optional[UUID],
        extra_vars: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        variables: Dict[str, Any] = {"agent": agent}

        if patient_id is not None:
            clinical_context = self._context_repo.load(patient_id)
            variables.update(clinical_context.to_dict())
            variables["patient_id"] = str(patient_id)

            try:
                latest_diagnosis = self._diagnosis_repo.get_latest_for_patient(patient_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("ContextManager: could not load diagnosis history: %s", exc)
                latest_diagnosis = None
            if latest_diagnosis:
                variables["recent_diagnosis"] = latest_diagnosis

            try:
                latest_research = self._research_repo.get_latest_for_patient(patient_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("ContextManager: could not load research history: %s", exc)
                latest_research = None
            if latest_research:
                variables["recent_research"] = latest_research

        if extra_vars:
            variables.update(extra_vars)

        return variables
