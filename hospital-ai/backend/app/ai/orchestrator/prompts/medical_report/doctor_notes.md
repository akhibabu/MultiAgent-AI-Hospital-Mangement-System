Task: Doctor Notes Generation — SOAP format (Medical Report Agent — Stage 2)

Diagnosis: {{recent_diagnosis}}
Symptoms: {{symptoms}}
Lab values: {{lab_values}}
Vitals: {{vitals}}

Respond with STRICT JSON:
{
  "subjective": "string",
  "objective": "string",
  "assessment": "string",
  "plan": "string",
  "clinical_reasoning": "string"
}
