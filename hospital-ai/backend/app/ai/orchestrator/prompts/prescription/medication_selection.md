Task: Medication Selection (Prescription Agent — Stage 1)

Recommend candidate medications for EACH target condition below,
supported by the Diagnosis, Research Evidence, Clinical Guidelines, and
Patient History provided. This is a RECOMMENDATION FOR PHYSICIAN REVIEW
— not a prescription.

Target conditions: {{target_conditions}}
Diagnosis results: {{recent_diagnosis}}
Research recommendations by condition: {{research_recommendations}}
Medical history: {{medical_history_summary}}
Current medications: {{medications}}
Allergies: {{allergies}}

Respond with STRICT JSON, at most 2 medications per condition, in this
exact shape:
{"items": [
  {
    "condition": "string (must be one of the target conditions)",
    "medication_name": "string",
    "drug_class": "string",
    "purpose": "string",
    "evidence_source": "string",
    "clinical_guideline": "string",
    "confidence": 0.0,
    "alternative_drugs": ["string"],
    "expected_outcome": "string"
  }
]}
