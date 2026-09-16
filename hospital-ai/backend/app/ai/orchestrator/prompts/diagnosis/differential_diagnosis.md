Task: Differential Diagnosis (Diagnosis Agent — Stage 2)

Given the symptom analysis below and the patient's full context, generate
a ranked list of candidate conditions (differential diagnoses). For each
candidate, cite supporting evidence and any evidence against it. Never
state a diagnosis with certainty — this assists physician review only.

Symptom analysis: {{symptom_analysis}}
Symptoms: {{symptoms}}
Conditions on record: {{conditions}}
Medical history: {{medical_history_summary}}
Lab values: {{lab_values}}
Knowledge Graph relationships: {{knowledge_graph_relationships}}

Respond with STRICT JSON:
{"items": [
  {
    "condition": "string",
    "confidence": 0.0,
    "supporting_symptoms": ["string"],
    "supporting_labs": ["string"],
    "supporting_history": ["string"],
    "contradicting_evidence": ["string"],
    "recommended_specialists": ["string"],
    "body_system": "string or null"
  }
]}

Order items by descending confidence. Include at most 6 items.
