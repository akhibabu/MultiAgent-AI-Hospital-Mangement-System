Task: Clinical Summary (Medical Report Agent — Stage 1)

Diagnosis: {{recent_diagnosis}}
Medical history: {{medical_history_summary}}
Conditions: {{conditions}}

Respond with STRICT JSON:
{
  "patient_overview": "string",
  "chief_complaint": "string",
  "history": "string",
  "diagnosis_summary": "string",
  "current_status": "string",
  "key_findings": ["string"]
}
