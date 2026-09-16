/** Prescription Agent types — physician-review treatment recommendations. Never a final prescription. */
import type { OrchestratorDebugInfo } from '@/types/aiOrchestrator';

export type ApprovalStatus = 'Approved' | 'Requires Physician Review' | 'Rejected';
export type InteractionLevel = 'Minor' | 'Moderate' | 'Major' | 'Critical';
export type AllergyStatus = 'Safe' | 'Warning' | 'Contraindicated';

export const APPROVAL_STATUS_TONE: Record<string, 'green' | 'blue' | 'amber' | 'red' | 'gray'> = {
  Approved: 'green',
  'Requires Physician Review': 'amber',
  Rejected: 'red',
};

export const INTERACTION_LEVEL_TONE: Record<string, 'green' | 'blue' | 'amber' | 'red' | 'gray'> = {
  Minor: 'blue',
  Moderate: 'amber',
  Major: 'red',
  Critical: 'red',
};

export const ALLERGY_STATUS_TONE: Record<string, 'green' | 'blue' | 'amber' | 'red' | 'gray'> = {
  Safe: 'green',
  Warning: 'amber',
  Contraindicated: 'red',
};

export interface MedicationRecommendation {
  condition: string;
  medication_name: string;
  drug_class: string;
  purpose: string;
  evidence_source: string;
  clinical_guideline: string;
  confidence: number;
  alternative_drugs: string[];
  expected_outcome: string;
}

export interface DrugInteraction {
  drug_a: string;
  drug_b: string;
  interaction_level: InteractionLevel;
  explanation: string;
  recommendation: string;
}

export interface AllergyCheckItem {
  medication_name: string;
  status: AllergyStatus;
  reason: string;
  cross_reactivity: string[];
}

export interface DosageRecommendation {
  medication_name: string;
  starting_dose: string;
  maintenance_dose: string;
  maximum_dose: string;
  dose_adjustment: string[];
  adjustment_factors: string[];
}

export interface TreatmentPlan {
  medication_plan: string[];
  lifestyle_advice: string[];
  monitoring_plan: string[];
  recommended_lab_tests: string[];
  recommended_imaging: string[];
  recommended_specialists: string[];
  follow_up_interval: string;
  emergency_advice: string;
}

export interface PrescriptionValidation {
  duplicate_drugs: string[];
  contraindications_found: string[];
  max_dose_exceeded: string[];
  allergy_conflicts: string[];
  drug_warnings: string[];
  confidence_score: number;
  approval_status: ApprovalStatus;
  notes: string[];
}

export interface PrescriptionResult {
  id: string;
  patient_id: string;
  diagnosis_result_id?: string | null;
  research_result_id?: string | null;
  target_conditions_json: string[];
  medication_recommendations_json: MedicationRecommendation[];
  drug_interactions_json: DrugInteraction[];
  allergy_checks_json: AllergyCheckItem[];
  dosage_recommendations_json: DosageRecommendation[];
  treatment_plan_json: TreatmentPlan;
  validation_summary_json: PrescriptionValidation;
  summary?: string | null;
  engine: string;
  status: string;
  error_message?: string | null;
  processing_time_ms?: number | null;
  created_at: string;
  updated_at?: string | null;
}

export interface PrescriptionStartResult {
  patient_id: string;
  diagnosis_result_id?: string | null;
  research_result_id?: string | null;
  status: string;
  processing_time_ms: number;
  summary: string;
  engine: string;
  warnings: string[];
  target_conditions: string[];
  medication_recommendations: MedicationRecommendation[];
  drug_interactions: DrugInteraction[];
  allergy_checks: AllergyCheckItem[];
  dosage_recommendations: DosageRecommendation[];
  treatment_plan: TreatmentPlan;
  validation: PrescriptionValidation;
  prescription_result: PrescriptionResult;
  ai_debug: OrchestratorDebugInfo[];
}

export interface PrescriptionHistoryItem {
  id: string;
  created_at: string;
  summary?: string | null;
  approval_status?: ApprovalStatus | null;
  target_conditions: string[];
  status: string;
}

export interface PrescriptionStatus {
  patient_id: string;
  has_result: boolean;
  status: string;
  approval_status?: ApprovalStatus | null;
  confidence_score?: number | null;
  target_conditions: string[];
  summary?: string | null;
  processing_time_ms?: number | null;
  created_at?: string | null;
}
