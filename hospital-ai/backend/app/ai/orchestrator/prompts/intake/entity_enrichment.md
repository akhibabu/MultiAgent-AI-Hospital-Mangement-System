Task: Entity Enrichment (Intake Agent — optional NER enrichment)

Below is the raw clinical text and the entities already recognized by
the rule-based extractor. Provide a short supplementary narrative
summary only — do not invent new diagnoses or medications.

Recognized entities: {{recognized_entities}}
Source text: {{source_text}}

Respond with STRICT JSON:
{"summary": "string", "confidence": 0.0, "notes": ["string"]}
