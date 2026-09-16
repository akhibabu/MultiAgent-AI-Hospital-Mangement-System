Task: Evidence Ranking (Research Agent — Stage 5)

Rank the {{candidate_count}} evidence candidates below by strength
(High/Medium/Low), assigning a calibrated confidence score to each.

Candidates (already slimmed — do not invent extra records):
{{evidence_candidates}}

Respond with STRICT JSON — one item per candidate, same order preference
by descending confidence. Keep each `summary` to ONE short sentence
(≤ 25 words) so the response fits the completion budget:

{"items": [
  {
    "evidence_type": "pubmed|clinical_trial|guideline|drug_efficacy",
    "condition": "string",
    "title": "string",
    "source": "string",
    "reference_id": "string",
    "url": "string",
    "publication_date": "YYYY-MM-DD or null",
    "summary": "string",
    "evidence_level": "High|Medium|Low",
    "relevance_score": 0.0,
    "confidence": 0.0
  }
]}

CRITICAL:
- `evidence_type` MUST be exactly one of `pubmed`, `clinical_trial`,
  `guideline`, `drug_efficacy` (copy from the candidate).
- Use `""` for unknown urls — never null.
- Prefer completing ALL candidates with short summaries over writing
  long summaries for only a few. Incomplete JSON is worse than a short
  summary.
