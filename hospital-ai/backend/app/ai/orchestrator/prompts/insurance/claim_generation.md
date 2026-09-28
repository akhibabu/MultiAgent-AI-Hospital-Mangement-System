Task: Claim Generation

Service: {{service_name}}
Service date: {{service_date}}
Billed amount: {{billed_amount}}
Policy: {{policy}}
Policy verification: {{policy_verification}}
Coverage estimate: {{coverage_estimate}}
Clinical and hospital context: {{clinical_context}}

Create a conservative CLAIM DRAFT. Never invent exact billing codes. Use a
code only when it is explicitly supported by the supplied clinical context;
otherwise leave the code list empty and put "Coder verification required" in
missing_documents.

Return STRICT JSON:
{
  "claim_status": "DRAFT — PHYSICIAN/BILLING REVIEW REQUIRED",
  "claim_narrative": "string",
  "diagnosis_codes": ["string"],
  "procedure_codes": ["string"],
  "lines": [
    {
      "service_name": "string",
      "procedure_code": "string or null",
      "diagnosis_codes": ["string"],
      "amount": 0,
      "documentation_required": ["string"]
    }
  ],
  "supporting_documents": ["string"],
  "missing_documents": ["string"],
  "total_billed_amount": 0,
  "review_required": true
}
