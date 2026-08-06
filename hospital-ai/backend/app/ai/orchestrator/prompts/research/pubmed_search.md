Task: PubMed-style Literature Search (Research Agent — Stage 1)

For the condition "{{condition}}", produce a set of plausible,
clinically-grounded literature summaries in the style of PubMed
abstracts. You do not have live PubMed access — clearly label this as an
AI-generated evidence summary, not a verified citation.

Respond with STRICT JSON:
{"items": [
  {
    "reference_id": "string",
    "title": "string",
    "authors": ["string"],
    "journal": "string",
    "publication_year": 2023,
    "study_type": "string",
    "summary": "string",
    "url": "string or null",
    "condition": "{{condition}}",
    "relevance_score": 0.0
  }
]}

Return up to {{limit}} items ordered by descending relevance_score.
Keep each `summary` to 1–2 short sentences. Prefer fewer complete items
over many that get truncated mid-JSON.
