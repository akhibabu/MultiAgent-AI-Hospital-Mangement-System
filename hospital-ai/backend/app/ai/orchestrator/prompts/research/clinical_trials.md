Task: Clinical Trial Search (Research Agent — Stage 2)

For the condition "{{condition}}", produce plausible, clinically-grounded
clinical-trial-style summaries. Label clearly as AI-generated, not a live
ClinicalTrials.gov lookup.

Respond with STRICT JSON:
{"items": [
  {
    "trial_id": "string",
    "title": "string",
    "status": "string",
    "phase": "string",
    "outcome_summary": "string",
    "eligibility_summary": "string",
    "condition": "{{condition}}",
    "url": "string or null",
    "relevance_score": 0.0
  }
]}

Return up to {{limit}} items ordered by descending relevance_score.
