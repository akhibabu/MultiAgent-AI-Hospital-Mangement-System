Task: Preauthorization Review

Service: {{service_name}}
Estimated insurer-side amount: {{estimated_cost}}
Authorization required by supplied policy terms: {{authorization_required}}
Policy: {{policy}}
Policy verification: {{policy_verification}}
Clinical context: {{clinical_context}}

Assess whether the submitted information is sufficient to prepare a
preauthorization request. This is NOT an insurer authorization decision.

Return STRICT JSON:
{
  "authorization_required": true,
  "status": "review_required",
  "service_name": "string",
  "estimated_cost": 0,
  "clinical_necessity_summary": "string",
  "required_documents": ["string"],
  "recommendation": "string",
  "review_required": true
}

Allowed status values:
- not_required
- ready_for_review
- insufficient_information
- review_required
