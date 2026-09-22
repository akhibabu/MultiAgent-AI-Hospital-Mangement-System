Task: Treatment Path Recommendation (Diagnosis Agent — Stage 5)

Note: this task prompt was added to fully cover the 6-stage Diagnosis
pipeline (the original spec listed 5 diagnosis prompts, covering 5 of 6
stages).

Recommend a referral/treatment pathway ONLY — never a medication or dosage — for
the leading differential diagnoses and severity level below.

When procedural or surgical intervention is explicitly indicated by the clinical
evidence, set surgery_required to true, list the recommended procedure(s), and
provide an estimated duration only when it is defensible from the available
clinical context. Otherwise set surgery_required to false, recommended_procedures
to [], and estimated_duration_minutes to null. Do not invent procedures or timing.

Leading differentials: {{differentials}}
Severity: {{severity}}

Respond with STRICT JSON:
{"recommended_specialists": ["string"], "recommended_department": "string or null", "diagnostic_tests": ["string"], "imaging": ["string"], "urgency": "Routine|Urgent|Emergency", "notes": "string", "surgery_required": true/false, "recommended_procedures": ["string"], "estimated_duration_minutes": "integer or null"}
