export interface InsurancePolicy {
  provider_name: string;
  policy_number: string;
  member_id?: string | null;
  plan_name: string;
  status: 'active' | 'inactive' | 'expired' | 'unknown';
  effective_from?: string | null;
  effective_to?: string | null;
  coverage_percent: number;
  deductible_remaining: number;
  out_of_pocket_remaining?: number | null;
  annual_limit_remaining?: number | null;
  copay: number;
  covered_services: string[];
  excluded_services: string[];
  preauthorization_services: string[];
}

export interface PolicyVerification {
  verified: boolean;
  coverage_active: boolean;
  provider_name: string;
  policy_number: string;
  policy_status: string;
  service_name: string;
  checked_on: string;
  issues: string[];
  notes: string[];
}

export interface CoverageEstimate {
  service_name: string;
  billed_amount: number;
  eligible_amount: number;
  deductible_applied: number;
  coverage_percent: number;
  copay: number;
  insurer_estimate: number;
  patient_estimate: number;
  assumptions: string[];
}

export interface ClaimLine {
  service_name: string;
  procedure_code?: string | null;
  diagnosis_codes: string[];
  amount: number;
  documentation_required: string[];
}

export interface ClaimDraft {
  claim_status: string;
  claim_narrative: string;
  diagnosis_codes: string[];
  procedure_codes: string[];
  lines: ClaimLine[];
  supporting_documents: string[];
  missing_documents: string[];
  total_billed_amount: number;
  review_required: boolean;
}

export interface FraudScreening {
  risk_level: 'low' | 'medium' | 'high';
  risk_score: number;
  flags: string[];
  rule_findings: string[];
  rationale: string;
  recommendation: string;
  review_required: boolean;
}

export interface PreauthorizationReview {
  authorization_required: boolean;
  status: 'not_required' | 'ready_for_review' | 'insufficient_information' | 'review_required';
  service_name: string;
  estimated_cost: number;
  clinical_necessity_summary: string;
  required_documents: string[];
  recommendation: string;
  review_required: boolean;
}

export interface InsuranceStartRequest {
  patient_id: string;
  service_name: string;
  service_date: string;
  billed_amount: number;
  supporting_documents: string[];
  policy: InsurancePolicy;
}

export interface InsuranceResult {
  id: string;
  patient_id: string;
  service_name: string;
  service_date: string;
  billed_amount: number;
  policy_json: InsurancePolicy;
  policy_verification_json: PolicyVerification;
  coverage_estimate_json: CoverageEstimate;
  claim_draft_json: ClaimDraft;
  fraud_screening_json: FraudScreening;
  preauthorization_json: PreauthorizationReview;
  summary: string;
  engine: string;
  status: string;
  warnings_json: string[];
  processing_time_ms?: number | null;
  created_at: string;
  updated_at?: string | null;
}

export interface InsuranceStartResponse {
  patient_id: string;
  service_name: string;
  service_date: string;
  billed_amount: number;
  status: string;
  processing_time_ms: number;
  summary: string;
  policy: InsurancePolicy;
  policy_verification: PolicyVerification;
  coverage_estimate: CoverageEstimate;
  claim_draft: ClaimDraft;
  fraud_screening: FraudScreening;
  preauthorization: PreauthorizationReview;
  warnings: string[];
  insurance_result: InsuranceResult;
  ai_debug: unknown[];
}

export interface InsuranceHistoryItem {
  id: string;
  created_at: string;
  service_name: string;
  billed_amount: number;
  policy_number: string;
  status: string;
}
