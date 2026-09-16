"""
Standalone smoke test for the Diagnosis Agent and Research Agent pipelines.

Runs entirely in-memory using a fake PatientClinicalContextRepository so it
requires no Supabase connection, and routes every AI Orchestrator call
through `AI_PROVIDER=stub` (deterministic canned JSON, no Groq/network
required). Prints a compact summary of each stage.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

# Must be set before any `app.*` module reads settings, so every strategy's
# AI Orchestrator call resolves to the deterministic stub provider instead
# of attempting a real network connection.
os.environ.setdefault("AI_PROVIDER", "stub")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.diagnosis.pipeline import DiagnosisPipeline  # noqa: E402
from app.ai.orchestrator import orchestrator as _orchestrator_module  # noqa: E402
from app.ai.orchestrator.orchestrator import AIOrchestrator  # noqa: E402
from app.ai.research.pipeline import ResearchPipeline  # noqa: E402
from app.repositories.patient_context_repository import (  # noqa: E402
    PatientClinicalContext,
)


class _NoopConversationMemory:
    """No-op conversation memory — keeps this smoke test fully offline
    (no Supabase `ai_conversation_memory` table required)."""

    def recent(self, patient_id, agent, limit):
        return []

    def append(self, *args, **kwargs):
        return None


class _NoopInteractionLogger:
    """No-op interaction logger — keeps this smoke test fully offline
    (no Supabase `ai_interaction_logs` table required)."""

    def log(self, **fields):
        return None


def _seed_offline_orchestrator() -> None:
    """
    Pre-seeds the AI Orchestrator singleton with no-op conversation
    memory / interaction logging so this script never touches Supabase —
    matching its "runs entirely in-memory" contract even though every AI
    Agent stage still round-trips through the real orchestrator pipeline
    (prompt loading, routing, the `stub` provider, caching, retries,
    response parsing).
    """
    _orchestrator_module._orchestrator = AIOrchestrator(
        memory=_NoopConversationMemory(),
        interaction_logger=_NoopInteractionLogger(),
    )


class FakeContextRepository:
    def load(self, patient_id):
        return PatientClinicalContext(
            patient_id=str(patient_id),
            patient_name="Jane Doe",
            age_years=52,
            gender="Female",
            symptoms=["chest pain", "shortness of breath", "fatigue", "palpitations"],
            conditions=["Hypertension"],
            medications=[{"name": "Lisinopril"}],
            vitals=[
                {"name": "blood pressure", "value": "148", "unit": "mmHg"},
                {"name": "heart rate", "value": "102", "unit": "bpm"},
            ],
            lab_values=[{"name": "troponin", "value": "0.02", "flag": "high"}],
            lab_tests=["troponin", "cholesterol"],
            previous_diagnoses=["Hypertension"],
            risk_overall_level="High",
            risk_overall_score=72.0,
            risk_categories=[{"name": "Cardiovascular Risk", "score": 80}],
            risk_factors=["Elevated blood pressure", "Sedentary lifestyle"],
            is_valid=True,
        )


class FakeDiagnosisRepo:
    def __init__(self, row):
        self._row = row

    def get_by_id(self, row_id, select="*"):
        return self._row

    def get_latest_for_patient(self, patient_id):
        return self._row


def main() -> None:
    _seed_offline_orchestrator()
    patient_id = uuid4()

    diagnosis_pipeline = DiagnosisPipeline(context_repo=FakeContextRepository())
    report = diagnosis_pipeline.run(patient_id, chief_complaint="Chest discomfort for 2 days")

    print("=== Diagnosis Agent ===")
    print("Summary:", report.summary)
    print("Top differentials:")
    for d in report.differential_diagnoses[:3]:
        print(f"  - {d.condition}: confidence={d.confidence}")
    print("Severity:", report.severity_assessment.level, report.severity_assessment.score)
    print("Treatment path specialists:", report.treatment_path.recommended_specialists)
    assert report.differential_diagnoses, "Expected at least one differential diagnosis"
    assert report.severity_assessment.level in {
        "Very Low",
        "Low",
        "Moderate",
        "High",
        "Critical",
    }

    diagnosis_row = {
        "id": uuid4(),
        "probability_scores_json": [p.model_dump(mode="json") for p in report.probability_scores],
    }

    research_pipeline = ResearchPipeline(
        diagnosis_repo=FakeDiagnosisRepo(diagnosis_row),
        context_repo=FakeContextRepository(),
    )
    research_report = research_pipeline.run(patient_id)

    print("\n=== Research Agent ===")
    print("Summary:", research_report.summary)
    print("Conditions researched:", research_report.conditions_researched)
    print("Evidence counts:", research_report.evidence_level_counts)
    print("Ranked evidence sample:")
    for e in research_report.ranked_evidence[:3]:
        print(f"  - [{e.evidence_level}] {e.evidence_type}: {e.title}")
    assert research_report.ranked_evidence, "Expected ranked evidence items"
    assert research_report.recommendations, "Expected recommendations"

    print("\nSMOKE TEST PASSED")


if __name__ == "__main__":
    main()
