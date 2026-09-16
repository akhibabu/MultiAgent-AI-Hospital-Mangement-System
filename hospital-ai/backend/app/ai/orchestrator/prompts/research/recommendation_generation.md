Task: Recommendation Generation (Research Agent — Stage 6, final)

For condition "{{condition}}", synthesize the ranked evidence below into
a physician-facing research recommendation summary. Never prescribe.

Ranked evidence for this condition: {{condition_evidence}}

Respond with STRICT JSON in this exact shape:
{
  "condition": "{{condition}}",
  "supporting_literature": ["string"],
  "clinical_guidelines": ["string"],
  "evidence_summary": "string",
  "recommended_diagnostic_tests": ["string"],
  "research_highlights": ["string"],
  "confidence_score": 0.0
}

Every field marked `["string"]` must be a JSON array, even when you have only
one item to report. Never collapse it into a bare string. Use `[]` when you
have nothing to report, and never use `null`.
