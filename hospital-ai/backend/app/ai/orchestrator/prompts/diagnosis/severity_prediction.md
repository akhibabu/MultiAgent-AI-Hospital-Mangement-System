Task: Severity Prediction (Diagnosis Agent — Stage 4)

Assess overall clinical severity for this patient given the leading
differential diagnoses and risk profile below.

Leading differentials: {{differentials}}
Risk level: {{risk_overall_level}} (score {{risk_overall_score}})
Risk factors: {{risk_factors}}
Risk alerts: {{risk_alerts}}
Vitals: {{vitals}}

Respond with STRICT JSON:
{"level": "Very Low|Low|Moderate|High|Critical", "score": 0.0, "explanation": "string", "contributing_factors": ["string"]}
