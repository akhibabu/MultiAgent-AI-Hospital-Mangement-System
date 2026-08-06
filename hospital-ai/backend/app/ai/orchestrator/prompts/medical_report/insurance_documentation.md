Task: Insurance Documentation (Medical Report Agent — Stage 5)

Diagnosis: {{recent_diagnosis}}
Procedures: {{procedures}}

This is ILLUSTRATIVE documentation to assist a billing team — it is NOT
a certified coding submission. Always flag that a certified medical
coder must verify final codes before any claim is filed.

Respond with STRICT JSON:
{
  "diagnosis_codes": ["string"],
  "procedure_codes": ["string"],
  "supporting_documents": ["string"],
  "medical_necessity": "string",
  "claim_summary": "string",
  "supporting_evidence": ["string"]
}

Return only the code itself in each list entry, e.g. "I21.9". Put any
description in `claim_summary` or `supporting_evidence` instead — JSON has no
comment syntax, so never annotate a value with `//` or `/* */`.
