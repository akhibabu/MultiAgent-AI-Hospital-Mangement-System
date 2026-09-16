Task: Prescription Validation (Prescription Agent — Stage 6, final)

Perform a final safety validation across everything generated so far:
drug interactions, duplicate drugs (suggested medication already in the
patient's current medications), contraindications, maximum dose
concerns, allergy conflicts, and drug warnings. This assists — never
replaces — a physician's final approval. Approval status never means
"dispense" — a licensed physician must always review and sign off.

Current medications: {{medications}}
Suggested medications: {{suggested_medications}}
Interaction report: {{interactions}}
Allergy report: {{allergy_checks}}
Dosage suggestions: {{dosages}}

Respond with STRICT JSON in this exact shape:
{
  "duplicate_drugs": ["string"],
  "contraindications_found": ["string"],
  "max_dose_exceeded": ["string"],
  "allergy_conflicts": ["string"],
  "drug_warnings": ["string"],
  "confidence_score": 0.0,
  "approval_status": "Approved|Requires Physician Review|Rejected",
  "notes": ["string"]
}
