Task: Drug Efficacy Analysis (Research Agent — Stage 4)

Analyze published-style evidence for drug "{{drug_name}}" in the context
of condition "{{condition}}". This is EVIDENCE ANALYSIS ONLY — never a
prescription or dosing recommendation.

Respond with STRICT JSON:
{
  "drug_name": "{{drug_name}}",
  "condition": "{{condition}}",
  "effectiveness_summary": "string",
  "known_side_effects": ["string"],
  "contraindications": ["string"],
  "drug_interactions": ["string"],
  "supporting_evidence": "string",
  "relevance_score": 0.0
}
