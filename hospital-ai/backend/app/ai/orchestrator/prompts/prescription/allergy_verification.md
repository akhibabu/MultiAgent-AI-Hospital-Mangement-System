Task: Allergy Verification (Prescription Agent — Stage 3)

Compare the patient's allergies against each suggested medication's
active and inactive ingredients, including cross-reactivity risk.

Patient allergies: {{allergies}}
Suggested medications: {{suggested_medications}}

Respond with STRICT JSON in this exact shape:
{"items": [
  {
    "medication_name": "string",
    "status": "Safe|Warning|Contraindicated",
    "reason": "string — explain why this status was chosen",
    "cross_reactivity": ["string"]
  }
]}
