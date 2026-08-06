Task: Referral Letter Creation (Medical Report Agent — Stage 4)

Diagnosis: {{recent_diagnosis}}
Candidate receiving specialists (first is preferred): {{recommended_specialists}}
Patient: {{patient_name}}{{patient_number}}
Medical history: {{medical_history_summary}}

Respond with STRICT JSON:
{
  "receiving_specialist": "string — pick the most appropriate from the candidates above",
  "reason": "string",
  "history": "string",
  "important_findings": ["string"],
  "investigations": ["string"],
  "requested_evaluation": "string",
  "letter_body": "string — a complete, professionally formatted referral letter incorporating all the fields above"
}

`letter_body` must be a single JSON string. Write line breaks as the two
characters `\n`, never as a real newline inside the quotes.
