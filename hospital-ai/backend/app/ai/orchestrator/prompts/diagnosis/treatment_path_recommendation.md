Task: Treatment Path Recommendation (Diagnosis Agent — Stage 5)

Note: this task prompt was added to fully cover the 6-stage Diagnosis
pipeline (the original spec listed 5 diagnosis prompts, covering 5 of 6
stages).

Recommend a referral pathway ONLY — never a medication or dosage — for
the leading differential diagnoses and severity level below.

Leading differentials: {{differentials}}
Severity: {{severity}}

Respond with STRICT JSON:
{"recommended_specialists": ["string"], "recommended_department": "string or null", "diagnostic_tests": ["string"], "imaging": ["string"], "urgency": "Routine|Urgent|Emergency", "notes": "string", "surgery_required": true/false, "recommended_procedures": ["string"], "estimated_duration_minutes": "integer or null"}
