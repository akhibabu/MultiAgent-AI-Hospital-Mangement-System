"""
Standalone smoke test for the Prescription Agent and Medical Report Agent
pipelines.

Runs entirely in-memory using fake repositories so it requires no Supabase
connection, and routes every AI Orchestrator call through `AI_PROVIDER=stub`
(deterministic canned JSON, no Groq/network required). Prints a compact
summary of each stage.
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

from app.ai.medical_report.pipeline import MedicalReportPipeline  # noqa: E402
from app.ai.orchestrator import orchestrator as _orchestrator_module  # noqa: E402
from app.ai.orchestrator.orchestrator import AIOrchestrator  # noqa: E402
from app.ai.prescription.pipeline import PrescriptionPipeline  # noqa: E402
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
            patient_number="PAT-000123",
            age_years=68,
            gender="Female",
            symptoms=["chest pain", "shortness of breath", "fatigue"],
            conditions=["Hypertension", "Coronary Artery Disease"],
            medications=[{"name": "Aspirin"}],
            allergies=["Penicillin"],
            vitals=[
                {"name": "blood pressure", "value": "148", "unit": "mmHg"},
                {"name": "heart rate", "value": "102", "unit": "bpm"},
            ],
            lab_values=[
                {"name": "creatinine", "value": "1.5", "unit": "mg/dL"},
                {"name": "troponin", "value": "0.02", "unit": "ng/mL"},
            ],
            lab_tests=["troponin", "cholesterol"],
            procedures=["ECG"],
            previous_diagnoses=["Hypertension"],
            risk_overall_level="High",
            risk_overall_score=72.0,
            is_valid=True,
        )


class FakeResultRepository:
    """Generic fake repository — behaves like Diagnosis/Research/Prescription repos."""

    def __init__(self, row):
        self._row = row

    def get_by_id(self, row_id, select="*"):
        return self._row

    def get_latest_for_patient(self, patient_id):
        return self._row

    def list_for_patient(self, patient_id, limit=20):
        return [self._row] if self._row else []

    def count_for_patient(self, patient_id):
        return 1 if self._row else 0


def main() -> None:
    _seed_offline_orchestrator()
    patient_id = uuid4()

    diagnosis_row = {
        "id": uuid4(),
        "chief_complaint": "Chest discomfort for 2 days",
        "symptom_analysis_json": {
            "narrative": "Cardiovascular and respiratory symptom cluster identified.",
            "clusters": [],
        },
        "differential_diagnoses_json": [
            {"condition": "Coronary Artery Disease", "confidence": 0.64},
            {"condition": "Hypertension", "confidence": 0.52},
        ],
        "probability_scores_json": [
            {"condition": "Coronary Artery Disease", "probability_pct": 64.0, "confidence": 0.64},
            {"condition": "Hypertension", "probability_pct": 52.0, "confidence": 0.52},
        ],
        "severity_assessment_json": {"level": "High", "score": 62.7, "explanation": "Elevated risk."},
        "treatment_path_json": {
            "recommended_specialists": ["Cardiologist", "General Physician"],
            "diagnostic_tests": ["Troponin", "Lipid panel", "ECG"],
            "imaging": ["Echocardiogram"],
            "urgency": "Urgent",
        },
        "clinical_decision_support_json": {
            "supporting_evidence": ["Elevated blood pressure", "Chest pain with exertion"],
            "clinical_notes": ["Recommend urgent cardiology referral."],
        },
    }

    research_row = {
        "id": uuid4(),
        "recommendation_json": [
            {
                "condition": "Coronary Artery Disease",
                "confidence_score": 0.8,
                "supporting_literature": ["Cohort study on statin therapy outcomes"],
                "clinical_guidelines": ["ACC/AHA Cholesterol Management Guideline"],
            },
        ],
    }

    prescription_pipeline = PrescriptionPipeline(
        context_repo=FakeContextRepository(),
        diagnosis_repo=FakeResultRepository(diagnosis_row),
        research_repo=FakeResultRepository(research_row),
    )
    prescription_report = prescription_pipeline.run(patient_id)

    print("=== Prescription Agent ===")
    print("Summary:", prescription_report.summary)
    print("Medications:")
    for m in prescription_report.medication_recommendations:
        print(f"  - {m.medication_name} ({m.drug_class}) for {m.condition}: confidence={m.confidence}")
    print("Interactions:", [(i.drug_a, i.drug_b, i.interaction_level) for i in prescription_report.drug_interactions])
    print("Allergy checks:", [(a.medication_name, a.status) for a in prescription_report.allergy_checks])
    print("Validation:", prescription_report.validation.approval_status, prescription_report.validation.confidence_score)
    assert prescription_report.medication_recommendations, "Expected at least one medication recommendation"
    assert prescription_report.validation.approval_status in {
        "Approved",
        "Requires Physician Review",
        "Rejected",
    }

    prescription_row = {
        "id": uuid4(),
        "treatment_plan_json": prescription_report.treatment_plan.model_dump(mode="json"),
    }

    report_pipeline = MedicalReportPipeline(
        context_repo=FakeContextRepository(),
        diagnosis_repo=FakeResultRepository(diagnosis_row),
        research_repo=FakeResultRepository(research_row),
        prescription_repo=FakeResultRepository(prescription_row),
    )
    bundle = report_pipeline.run(patient_id, version=1)

    print("\n=== Medical Report Agent ===")
    print("Summary:", bundle.summary)
    print("Clinical summary overview:", bundle.clinical_summary.patient_overview)
    print("Doctor notes assessment:", bundle.doctor_notes.assessment)
    print("Discharge condition:", bundle.discharge_summary.condition_on_discharge)
    print("Referral to:", bundle.referral_letter.receiving_specialist)
    print("Insurance diagnosis codes:", bundle.insurance_documentation.diagnosis_codes)
    print("Patient report diagnosis summary:", bundle.patient_report.diagnosis_summary)
    assert bundle.clinical_summary.patient_overview
    assert bundle.referral_letter.letter_body
    assert bundle.insurance_documentation.diagnosis_codes
    assert bundle.patient_report.faq

    print("\nSMOKE TEST PASSED")


if __name__ == "__main__":
    main()
