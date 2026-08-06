"""
Stub provider — `AI_PROVIDER=stub`, used only by automated tests and by
developers running without a real provider API key.

This is NOT a reintroduction of the old rule-based decision engines — it
is a fake network layer only. It returns deterministic, clearly-labeled
canned JSON so the rest of the orchestrator pipeline (prompt rendering,
caching, memory, retries, response parsing, logging) can be exercised
end-to-end without a real model.

Each entry below is keyed by `"<agent>/<task>"` and shaped to satisfy the
exact Pydantic `response_model` the calling strategy validates against
(see `app/ai/<agent>/*.py`), so smoke tests can assert on non-empty,
schema-correct — if obviously fake — content.

The copy is written in deliberately silly pirate-speak so nobody can
mistake stub output for a real clinical result. Two rules the joke never
breaks, because this data still flows into clinical tables:
  * never insulting or demeaning toward a patient or clinician, and
  * never implying urgency, deterioration, or danger — severity stays
    Low, urgency stays Routine, and every string carries `_STUB_NOTE`.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple  # noqa: F401

from app.ai.orchestrator.providers.base import (
    BaseAIProvider,
    ProviderCompletion,
    ProviderMessage,
)

_STUB_NOTE = "AI_PROVIDER=stub test fixture — not a real model response."

# Canned, schema-correct JSON per "<agent>/<task>", covering every prompt
# in `app/ai/orchestrator/prompts/`. Keep in sync when a new task is added.
_TASK_RESPONSES: Dict[str, Dict[str, Any]] = {
    # --- Intake (no response_model — any valid JSON is accepted) ---
    "intake/entity_enrichment": {
        "summary": f"Arrr, the ship's manifest be logged. {_STUB_NOTE}",
        "additional_entities": [],
    },
    # --- Diagnosis Agent ---
    "diagnosis/symptom_analysis": {
        "clusters": [
            {
                "body_system": "Cardiovascular",
                "symptoms": ["a wee flutter in the chest locker"],
                "duration_hint": "2 tides",
                "severity_hint": "Low",
                "related_conditions": ["Landlubber's Mild Grumble"],
            }
        ],
        "total_symptoms": 1,
        "notable_vitals": [],
        "notable_labs": [],
        "narrative": (
            "Arrr, the crew charted the symptoms and found naught but calm "
            f"seas ahead. {_STUB_NOTE}"
        ),
    },
    "diagnosis/differential_diagnosis": {
        "items": [
            {
                "condition": "Stub Landlubber's Mild Grumble",
                "confidence": 0.6,
                "supporting_symptoms": ["a wee flutter in the chest locker"],
                "supporting_labs": [],
                "supporting_history": [],
                "contradicting_evidence": [],
                "recommended_specialists": ["Ship's Surgeon"],
                "body_system": "Cardiovascular",
            }
        ]
    },
    "diagnosis/disease_probability_scoring": {
        "items": [
            {
                "condition": "Stub Landlubber's Mild Grumble",
                "probability_pct": 60.0,
                "confidence": 0.6,
                "evidence_used": ["Stub spyglass readings"],
                "risk_contribution": 10.0,
                "risk_category": "Low",
            }
        ]
    },
    "diagnosis/severity_prediction": {
        "level": "Low",
        "score": 20.0,
        "explanation": (
            "Steady as she goes — the stub seas be calm and the patient be "
            f"shipshape. {_STUB_NOTE}"
        ),
        "contributing_factors": ["Too much hardtack at the galley"],
    },
    "diagnosis/treatment_path_recommendation": {
        "recommended_specialists": ["Ship's Surgeon"],
        "recommended_department": "Internal Medicine",
        "diagnostic_tests": ["Complete Blood Count"],
        "imaging": [],
        "urgency": "Routine",
        "notes": f"Chart a leisurely course to the sickbay. {_STUB_NOTE}",
    },
    "diagnosis/clinical_decision_support": {
        "possible_diagnoses": ["Stub Landlubber's Mild Grumble"],
        "supporting_evidence": ["Stub message in a bottle"],
        "suggested_tests": ["Complete Blood Count"],
        "risk_factors": ["Excessive shanty singing"],
        "relevant_history": ["Stub logbook entry"],
        "clinical_notes": [
            f"Arrr, a physician still be the captain of this decision. {_STUB_NOTE}"
        ],
    },
    # --- Research Agent ---
    "research/pubmed_search": {
        "items": [
            {
                "reference_id": "STUB-PMID-000001",
                "title": "Arrr: A Systematic Review of Seafarin' Wellness",
                "authors": ["Cap'n Stub"],
                "journal": "The Salty Journal of Make-Believe Medicine",
                "publication_year": 2024,
                "study_type": "Review Article",
                "summary": f"Ahoy, this paper be entirely fictional. {_STUB_NOTE}",
                "url": "",
                "condition": "Stub Condition",
                "relevance_score": 0.5,
            }
        ]
    },
    "research/clinical_trials": {
        "items": [
            {
                "trial_id": "STUB-NCT00000001",
                "title": "A Phase 3 Voyage Evaluatin' Imaginary Grog",
                "status": "Completed",
                "phase": "Phase 3",
                "outcome_summary": f"The crew reported jolly spirits. {_STUB_NOTE}",
                "eligibility_summary": "Must be able to tie a bowline. Fictional.",
                "condition": "Stub Condition",
                "url": "",
                "relevance_score": 0.5,
            }
        ]
    },
    "research/treatment_guidelines": {
        "items": [
            {
                "source": "WHO",
                "title": "Stub Pirate Code of Clinical Practice",
                "recommendation": (
                    "The Code be more what ye'd call guidelines than actual "
                    f"rules. {_STUB_NOTE}"
                ),
                "condition": "Stub Condition",
                "published_year": 2023,
                "url": "",
                "relevance_score": 0.5,
            }
        ]
    },
    "research/drug_analysis": {
        "drug_name": "Stub Grog (not a real medicine)",
        "condition": "Stub Condition",
        "effectiveness_summary": f"Works wonders in fiction only. {_STUB_NOTE}",
        "known_side_effects": ["An irresistible urge to say 'arrr'"],
        "contraindications": [],
        "drug_interactions": [],
        "supporting_evidence": "One (1) fictional message in a bottle.",
        "relevance_score": 0.5,
    },
    "research/evidence_ranking": {
        "items": [
            {
                "evidence_type": "pubmed",
                "condition": "Stub Condition",
                "title": "Arrr: A Systematic Review of Seafarin' Wellness",
                "source": "PubMed",
                "reference_id": "STUB-PMID-000001",
                "url": "",
                "publication_date": None,
                "summary": f"Ranked by the parrot. Not real evidence. {_STUB_NOTE}",
                "evidence_level": "Medium",
                "relevance_score": 0.5,
                "confidence": 0.5,
                "raw": {},
            }
        ]
    },
    "research/recommendation_generation": {
        "condition": "Stub Condition",
        "supporting_literature": ["Arrr: A Systematic Review of Seafarin' Wellness"],
        "clinical_guidelines": ["Stub Pirate Code of Clinical Practice"],
        "evidence_summary": f"X marks the spot, but the map be fake. {_STUB_NOTE}",
        "recommended_diagnostic_tests": ["Complete Blood Count"],
        "research_highlights": ["Stub treasure map fragment"],
        "confidence_score": 0.5,
    },
    # --- Prescription Agent ---
    "prescription/medication_selection": {
        "items": [
            {
                "condition": "Stub Condition",
                "medication_name": "Stub Placebo Doubloon",
                "drug_class": "Stub Drug Class",
                "purpose": "To keep the smoke tests jolly.",
                "evidence_source": "Stub message in a bottle",
                "clinical_guideline": "Stub Pirate Code of Clinical Practice",
                "confidence": 0.6,
                "alternative_drugs": ["Stub Alternative Doubloon"],
                "expected_outcome": (
                    "A hearty 'arrr' and naught else — fictional. "
                    f"{_STUB_NOTE}"
                ),
            }
        ]
    },
    "prescription/drug_interaction_check": {
        "items": [
            {
                "drug_a": "Stub Placebo Doubloon",
                "drug_b": "Stub Alternative Doubloon",
                "interaction_level": "Minor",
                "explanation": f"Two fictional coins, one fictional pouch. {_STUB_NOTE}",
                "recommendation": "Consult the ship's surgeon, as always.",
            }
        ]
    },
    "prescription/allergy_verification": {
        "items": [
            {
                "medication_name": "Stub Placebo Doubloon",
                "status": "Safe",
                "reason": f"No allergies in this here fictional logbook. {_STUB_NOTE}",
                "cross_reactivity": [],
            }
        ]
    },
    "prescription/dosage_optimization": {
        "items": [
            {
                "medication_name": "Stub Placebo Doubloon",
                "starting_dose": "One (1) imaginary doubloon",
                "maintenance_dose": "One (1) imaginary doubloon",
                "maximum_dose": "Still just the one imaginary doubloon",
                "dose_adjustment": ["Adjust by parrot's discretion — fictional"],
                "adjustment_factors": ["Stub adjustment factor"],
            }
        ]
    },
    "prescription/treatment_plan": {
        "medication_plan": ["Stub Placebo Doubloon"],
        "lifestyle_advice": ["More sea air, fewer barnacles"],
        "monitoring_plan": ["Check the compass twice a voyage"],
        "recommended_lab_tests": ["Complete Blood Count"],
        "recommended_imaging": [],
        "recommended_specialists": ["Ship's Surgeon"],
        "follow_up_interval": "2 weeks",
        "emergency_advice": (
            "In any real situation, contact real emergency services. "
            f"{_STUB_NOTE}"
        ),
    },
    "prescription/validation": {
        "duplicate_drugs": [],
        "contraindications_found": [],
        "max_dose_exceeded": [],
        "allergy_conflicts": [],
        "drug_warnings": [],
        "confidence_score": 0.6,
        "approval_status": "Requires Physician Review",
        "notes": [
            f"The captain (a real physician) must sign off. {_STUB_NOTE}"
        ],
    },
    # --- Medical Report Agent ---
    "medical_report/clinical_summary": {
        "patient_overview": (
            f"Ahoy! A fictional sailor in fine and steady health. {_STUB_NOTE}"
        ),
        "chief_complaint": "A wee flutter in the chest locker.",
        "history": "Sailed many a calm sea. Fictional.",
        "diagnosis_summary": "Stub Landlubber's Mild Grumble.",
        "current_status": "Shipshape and steady.",
        "key_findings": ["Stub finding: the parrot approves"],
    },
    "medical_report/doctor_notes": {
        "subjective": "Patient reports feelin' generally jolly.",
        "objective": "Vitals be steady as a lighthouse.",
        "assessment": "Stub Landlubber's Mild Grumble — fictional.",
        "plan": "Routine follow-up at the next port.",
        "clinical_reasoning": f"Reasoned by parrot, verified by no one. {_STUB_NOTE}",
    },
    "medical_report/discharge_summary": {
        "admission_reason": "A wee flutter in the chest locker.",
        "hospital_course": f"Smooth sailin' throughout the stay. {_STUB_NOTE}",
        "procedures": ["Stub procedure: walked the (very short) plank"],
        "medications": ["Stub Placebo Doubloon"],
        "condition_on_discharge": "Stable",
        "follow_up": "Return to port in two weeks.",
        "emergency_instructions": (
            "For any real concern, contact real emergency services."
        ),
    },
    "medical_report/referral_letter": {
        "receiving_specialist": "Ship's Surgeon",
        "reason": "Routine second opinion from a fellow mariner.",
        "history": "Sailed many a calm sea. Fictional.",
        "important_findings": ["Stub finding: the parrot approves"],
        "investigations": ["Complete Blood Count"],
        "requested_evaluation": "A friendly look-over at your convenience.",
        "letter_body": (
            "Dear esteemed colleague, ahoy. This letter be entirely fictional "
            f"and generated by a test fixture. {_STUB_NOTE}"
        ),
    },
    "medical_report/insurance_documentation": {
        "diagnosis_codes": ["STUB.001"],
        "procedure_codes": ["STUB-PROC-001"],
        "supporting_documents": ["Stub treasure map (not admissible)"],
        "medical_necessity": f"Necessary only for smoke tests. {_STUB_NOTE}",
        "claim_summary": "Payable in imaginary doubloons.",
        "supporting_evidence": ["Stub message in a bottle"],
    },
    "medical_report/patient_report": {
        "diagnosis_summary": "Stub Landlubber's Mild Grumble — fictional.",
        "treatment_summary": f"Rest, sea air, and good spirits. {_STUB_NOTE}",
        "current_medicines": ["Stub Placebo Doubloon"],
        "lifestyle_advice": ["More sea air, fewer barnacles"],
        "diet": ["Fewer biscuits, more citrus (scurvy be no joke)"],
        "exercise": ["A brisk turn about the deck"],
        "follow_up": "Return to port in two weeks.",
        "emergency_contact_instructions": (
            "For any real concern, contact real emergency services."
        ),
        "faq": [
            {
                "question": "Be this a real medical report?",
                "answer": "Nay! It be a test fixture. Ask a real physician.",
            }
        ],
    },
}

_DEFAULT_RESPONSE: Dict[str, Any] = {
    "summary": f"Arrr, a stub AI Orchestrator response. {_STUB_NOTE}",
    "confidence": 0.5,
    "recommendations": [],
    "citations": [],
    "items": [],
    "warnings": [
        "AI_PROVIDER=stub is active — this is a deterministic test fixture "
        "written in pirate-speak so it can never be mistaken for a real "
        "clinical result. Set AI_PROVIDER=groq for real results."
    ],
}


class StubProvider(BaseAIProvider):
    name = "stub"
    base_url = "in-memory (no network)"

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config

    def generate(
        self,
        messages: List[ProviderMessage],
        *,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: Optional[float] = None,
        agent: str = "",
        task: str = "",
    ) -> ProviderCompletion:
        user_text = next((m.content for m in reversed(messages) if m.role == "user"), "")
        key = f"{agent}/{task}" if agent and task else ""
        payload = _TASK_RESPONSES.get(key, _DEFAULT_RESPONSE)
        content = json.dumps(payload)
        return ProviderCompletion(
            content=content,
            provider=self.name,
            model="stub-local",
            prompt_tokens=len(user_text.split()),
            completion_tokens=len(content.split()),
            raw=payload,
        )

    def health_check(self, model: str) -> Tuple[bool, Optional[str]]:
        return True, None

    def list_models(self) -> List[str]:
        return ["stub-local"]
