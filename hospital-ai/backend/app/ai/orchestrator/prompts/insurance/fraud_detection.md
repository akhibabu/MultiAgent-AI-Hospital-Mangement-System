Task: Fraud Detection / Claim Anomaly Screening

Service: {{service_name}}
Service date: {{service_date}}
Billed amount: {{billed_amount}}
Policy: {{policy}}
Policy verification: {{policy_verification}}
Deterministic rule findings: {{rule_findings}}
Recent Insurance Agent runs: {{prior_claims}}

Screen for POSSIBLE claim anomalies only. A flag is not a fraud finding.
Give the most conservative risk level justified by the supplied evidence.
Do not infer intent or wrongdoing.

Return STRICT JSON:
{
  "risk_level": "low",
  "risk_score": 0,
  "flags": ["string"],
  "rule_findings": ["string"],
  "rationale": "string",
  "recommendation": "string",
  "review_required": true
}
