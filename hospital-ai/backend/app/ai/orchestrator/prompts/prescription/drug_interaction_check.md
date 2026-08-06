Task: Drug Interaction Check (Prescription Agent — Stage 2)

Compare every pair among the current medications and suggested
medications below and identify every interaction, however minor.
Explain each one clearly and include a brief recommendation.

Current medications: {{medications}}
Suggested medications: {{suggested_medications}}

Respond with STRICT JSON in this exact shape:
{"items": [
  {
    "drug_a": "string",
    "drug_b": "string",
    "interaction_level": "Minor|Moderate|Major|Critical",
    "explanation": "string",
    "recommendation": "string"
  }
]}

If no interactions are found, return {"items": []}.
