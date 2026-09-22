Task: Treatment Plan Creation (Prescription Agent — Stage 5)

Build a holistic treatment plan from everything generated so far.
Exclude any medication flagged "Contraindicated" in the allergy report
and note its alternative(s) instead.

Target conditions: {{target_conditions}}
Recommended medications: {{medications}}
Allergy report: {{allergy_checks}}
Dosage suggestions: {{dosages}}
Severity: {{severity_level}}
Diagnosis Agent recommended specialists: {{diagnosis_specialists}}
Diagnosis Agent recommended tests: {{diagnosis_tests}}
Diagnosis Agent recommended imaging: {{diagnosis_imaging}}

Respond with STRICT JSON in this exact shape:
{
  "medication_plan": ["string"],
  "lifestyle_advice": ["string"],
  "monitoring_plan": ["string"],
  "recommended_lab_tests": ["string"],
  "recommended_imaging": ["string"],
  "recommended_specialists": ["string"],
  "follow_up_interval": "string",
  "emergency_advice": "string",
  "surgery_required": true/false,
  "procedure_recommendations": ["string"],
  "estimated_duration_minutes": "integer or null"
}
