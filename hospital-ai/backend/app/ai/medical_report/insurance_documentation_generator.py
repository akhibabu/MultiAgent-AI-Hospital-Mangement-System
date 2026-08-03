"""
Medical Report Agent — Stage 5: Insurance Documentation.

Automatically prepares diagnosis codes, procedure codes, supporting
documents, medical necessity, and claim summary. Codes are illustrative
mock mappings — a certified medical coder must verify before claim submission.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.ai.medical_report.models import InsuranceDocumentation
from app.repositories.patient_context_repository import PatientClinicalContext

# Illustrative ICD-10-style mapping for the conditions known to the Diagnosis
# Agent's rule-based knowledge base. Must be verified by a certified coder.
_ICD10_CODES: Dict[str, str] = {
    "Type 2 Diabetes Mellitus": "E11.9",
    "Hypertension": "I10",
    "Coronary Artery Disease": "I25.10",
    "Asthma / Reactive Airway Disease": "J45.909",
    "Pneumonia / Respiratory Infection": "J18.9",
    "Chronic Kidney Disease": "N18.9",
    "Urinary Tract Infection": "N39.0",
    "Anemia": "D64.9",
    "Thyroid Disorder": "E07.9",
    "Gastritis / Peptic Ulcer Disease": "K29.70",
    "Migraine / Neurological Headache Disorder": "G43.909",
    "Sepsis / Systemic Infection": "A41.9",
}

# Illustrative CPT-style mapping for common diagnostic tests / procedures.
_CPT_CODES: Dict[str, str] = {
    "ECG": "93000",
    "Chest X-ray": "71046",
    "CBC": "85025",
    "Complete blood count": "85025",
    "Basic metabolic panel": "80048",
    "Lipid panel": "80061",
    "Troponin": "84484",
    "HbA1c": "83036",
    "Fasting blood glucose": "82947",
    "Urinalysis": "81003",
    "Echocardiogram": "93306",
    "Spirometry": "94010",
}


class InsuranceDocumentationGenerator:
    def generate(
        self,
        context: PatientClinicalContext,
        diagnosis_row: Optional[Dict[str, Any]],
        research_row: Optional[Dict[str, Any]],
    ) -> InsuranceDocumentation:
        probs = (diagnosis_row or {}).get("probability_scores_json") or []
        conditions = [p.get("condition") for p in probs if isinstance(p, dict) and p.get("condition")]
        if not conditions:
            conditions = context.conditions[:3]

        diagnosis_codes = [
            {"condition": c, "code": _ICD10_CODES.get(c, "Pending coder verification")}
            for c in conditions
        ] or [{"condition": "Not documented", "code": "N/A"}]

        treatment_path = (diagnosis_row or {}).get("treatment_path_json") or {}
        procedures = list(treatment_path.get("diagnostic_tests") or []) + list(
            treatment_path.get("imaging") or []
        )
        procedure_codes = [
            {"procedure": p, "code": _CPT_CODES.get(p, "Pending coder verification")}
            for p in procedures
        ] or [{"procedure": "Not documented", "code": "N/A"}]

        supporting_documents: List[str] = ["Clinical Summary", "Doctor Notes"]
        if diagnosis_row:
            supporting_documents.append("Diagnosis Agent Report")
        if research_row:
            supporting_documents.append("Research Agent Evidence Report")
        if context.lab_values:
            supporting_documents.append("Laboratory Results")
        if context.vitals:
            supporting_documents.append("Vitals Record")

        top_condition = conditions[0] if conditions else "the patient's presenting condition"
        severity = ((diagnosis_row or {}).get("severity_assessment_json") or {}).get("level")
        medical_necessity = (
            f"Services were medically necessary to evaluate and manage {top_condition}"
            f"{f' (severity: {severity})' if severity else ''}. Diagnostic testing and "
            "referral were ordered based on documented clinical findings and evidence-based "
            "guidelines. See attached Clinical Summary and Diagnosis Agent Report for full detail."
        )

        claim_summary = (
            f"Encounter for {top_condition} — {len(diagnosis_codes)} diagnosis code(s), "
            f"{len(procedure_codes)} procedure/test code(s) submitted for review."
        )

        supporting_evidence: List[str] = []
        recs = (research_row or {}).get("recommendation_json") or []
        for r in recs[:3]:
            if isinstance(r, dict):
                supporting_evidence.extend(r.get("clinical_guidelines") or [])
                supporting_evidence.extend(r.get("supporting_literature") or [])
        supporting_evidence = list(dict.fromkeys(supporting_evidence))[:6] or [
            "No Research Agent evidence on record for this encounter."
        ]

        return InsuranceDocumentation(
            diagnosis_codes=diagnosis_codes,
            procedure_codes=procedure_codes,
            supporting_documents=supporting_documents,
            medical_necessity=medical_necessity,
            claim_summary=claim_summary,
            supporting_evidence=supporting_evidence,
        )
