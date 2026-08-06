Task: Symptom Analysis (Diagnosis Agent — Stage 1)

Analyze the patient's reported symptoms and cluster them by body system,
using the context below to infer duration and severity hints where
possible.

Symptoms: {{symptoms}}
Medical history summary: {{medical_history_summary}}
Timeline: {{timeline}}
Notable vitals: {{vitals}}
Notable lab values: {{lab_values}}
Previous diagnoses: {{previous_diagnoses}}
Knowledge Graph summary: {{knowledge_graph_summary}}

Respond with STRICT JSON matching exactly this shape:
{
  "clusters": [
    {
      "body_system": "string",
      "symptoms": ["string"],
      "duration_hint": "string or null",
      "severity_hint": "string or null",
      "related_conditions": ["string"]
    }
  ],
  "total_symptoms": 0,
  "notable_vitals": [{"...": "..."}],
  "notable_labs": [{"...": "..."}],
  "narrative": "2-4 sentence clinical narrative summarizing the symptom pattern"
}
