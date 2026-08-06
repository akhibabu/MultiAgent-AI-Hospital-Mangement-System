Task: Clinical Decision Support (Diagnosis Agent — Stage 6, final)

Synthesize the full diagnosis pipeline output into a clinician-facing
decision-support summary. Never replace clinical judgment; always
recommend physician review for any high-severity or low-confidence case.

Symptom analysis: {{symptom_analysis}}
Differential diagnoses: {{differentials}}
Probability scores: {{probabilities}}
Severity: {{severity}}
Treatment path (referral only, no medication): {{treatment_path}}

Respond with STRICT JSON:
{"possible_diagnoses": ["string"], "supporting_evidence": ["string"], "suggested_tests": ["string"], "risk_factors": ["string"], "relevant_history": ["string"], "clinical_notes": ["string"]}
