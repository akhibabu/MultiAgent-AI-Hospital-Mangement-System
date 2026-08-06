Task: Disease Probability Scoring (Diagnosis Agent — Stage 3)

Note: this task prompt was added to fully cover the 6-stage Diagnosis
pipeline (the original spec listed 5 diagnosis prompts, covering 5 of 6
stages).

Convert the differential diagnoses below into calibrated probability
scores, using the Knowledge Graph and risk profile as corroborating
evidence.

Differential diagnoses: {{differentials}}
Risk categories: {{risk_categories}}
Knowledge Graph nodes: {{knowledge_graph_nodes}}

Respond with STRICT JSON:
{"items": [
  {
    "condition": "string",
    "probability_pct": 0.0,
    "confidence": 0.0,
    "evidence_used": ["string"],
    "risk_contribution": 0.0,
    "risk_category": "string or null"
  }
]}

Probabilities across items do not need to sum to 100 — they are
independent likelihood estimates, not mutually exclusive posteriors.
