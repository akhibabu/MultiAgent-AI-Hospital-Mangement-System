Task: Patient Report Generation (Medical Report Agent — Stage 6, final)

Write this ENTIRELY in simple, friendly, jargon-free language for the
patient themselves — no medical abbreviations, no clinical jargon.

Diagnosis: {{recent_diagnosis}}
Prescription: {{recent_prescription}}

Respond with STRICT JSON:
{
  "diagnosis_summary": "string",
  "treatment_summary": "string",
  "current_medicines": ["string"],
  "lifestyle_advice": ["string"],
  "diet": ["string"],
  "exercise": ["string"],
  "follow_up": "string",
  "emergency_contact_instructions": "string",
  "faq": [{"question": "string", "answer": "string"}]
}
