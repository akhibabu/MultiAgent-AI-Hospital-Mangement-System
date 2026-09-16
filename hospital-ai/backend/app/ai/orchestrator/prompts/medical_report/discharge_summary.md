Task: Discharge Summary (Medical Report Agent — Stage 3)

Diagnosis: {{recent_diagnosis}}
Prescription: {{recent_prescription}}
Timeline: {{timeline}}

Respond with STRICT JSON:
{
  "admission_reason": "string",
  "hospital_course": "string",
  "procedures": ["string"],
  "medications": ["string"],
  "condition_on_discharge": "string",
  "follow_up": "string",
  "emergency_instructions": "string"
}
