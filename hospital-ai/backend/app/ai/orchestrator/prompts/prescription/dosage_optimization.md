Task: Dosage Optimization (Prescription Agent — Stage 4)

Estimate a SAFE DOSE RANGE — never a single final dose — for each
approved medication below, using age, weight, gender, kidney/liver
function, severity, and history. If a factor is unknown, use
conservative adult defaults and say so explicitly in
`adjustment_factors`.

Age: {{age_years}}, Gender: {{gender}}
Severity: {{severity_level}}
Medical history: {{medical_history_summary}}
Conditions: {{conditions}}
Lab values (renal/hepatic function if present): {{lab_values}}
Vitals (weight if present): {{vitals}}
Approved medications: {{suggested_medications}}

Respond with STRICT JSON in this exact shape:
{"items": [
  {
    "medication_name": "string",
    "starting_dose": "string",
    "maintenance_dose": "string",
    "maximum_dose": "string",
    "dose_adjustment": ["string — actionable adjustment notes"],
    "adjustment_factors": ["string — which patient factors drove the adjustment"]
  }
]}
