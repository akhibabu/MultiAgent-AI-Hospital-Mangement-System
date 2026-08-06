Task: Treatment Guideline Retrieval (Research Agent — Stage 3)

Note: this task prompt was added to fully cover the 6-stage Research
pipeline (the original spec's 5 research prompts did not include a
guideline-retrieval stage prompt).

For the condition "{{condition}}", summarize plausible treatment
guideline recommendations in the style of WHO/CDC/hospital/medical
society guidance. Label clearly as an AI-generated summary, not a
verified citation.

Respond with STRICT JSON:
{"items": [
  {
    "source": "string",
    "title": "string",
    "recommendation": "string",
    "condition": "{{condition}}",
    "published_year": 2023,
    "url": "string or null",
    "relevance_score": 0.0
  }
]}

Return up to {{limit}} items ordered by descending relevance_score.
