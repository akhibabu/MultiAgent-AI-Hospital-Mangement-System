/** Diagnosis Agent types — clinical decision support (assists, never replaces, a physician). */

export type SeverityLevel = 'Very Low' | 'Low' | 'Moderate' | 'High' | 'Critical';

export const SEVERITY_LEVEL_TONE: Record<
  string,
  'green' | 'blue' | 'amber' | 'red' | 'gray'
> = {
  'Very Low': 'green',
  Low: 'green',
  Moderate: 'amber',
  High: 'red',
  Critical: 'red',
};

export interface SymptomCluster {
  body_system: string;
  symptoms: string[];
  duration_hint?: string | null;
  severity_hint?: string | null;
  related_conditions: string[];
}

export interface SymptomAnalysis {
  clusters: SymptomCluster[];
  total_symptoms: number;
  notable_vitals: Array<Record<string, unknown>>;
  notable_labs: Array<Record<string, unknown>>;
  narrative: string;
}

export interface DifferentialDiagnosis {
  condition: string;
  confidence: number;
  supporting_symptoms: string[];
  supporting_labs: string[];
  supporting_history: string[];
  contradicting_evidence: string[];
  recommended_specialists: string[];
  body_system?: string | null;
}

export interface DiseaseProbability {
  condition: string;
  probability_pct: number;
  confidence: number;
  evidence_used: string[];
  risk_contribution: number;
  risk_category?: string | null;
}

export interface SeverityAssessment {
  level: string;
  score: number;
  explanation: string;
  contributing_factors: string[];
}

export interface TreatmentPath {
  recommended_specialists: string[];
  recommended_department?: string | null;
  diagnostic_tests: string[];
  imaging: string[];
  urgency: string;
  notes: string;
}

export interface ClinicalDecisionSupport {
  possible_diagnoses: string[];
  supporting_evidence: string[];
  suggested_tests: string[];
  risk_factors: string[];
  relevant_history: string[];
  clinical_notes: string[];
  disclaimer: string;
}

export interface DiagnosisResult {
  id: string;
  patient_id: string;
  processing_job_id?: string | null;
  chief_complaint?: string | null;
  focus_symptoms_json: string[];
  symptom_analysis_json: SymptomAnalysis;
  differential_diagnoses_json: DifferentialDiagnosis[];
  probability_scores_json: DiseaseProbability[];
  severity_assessment_json: SeverityAssessment;
  treatment_path_json: TreatmentPath;
  clinical_decision_support_json: ClinicalDecisionSupport;
  summary?: string | null;
  engine: string;
  status: string;
  error_message?: string | null;
  processing_time_ms?: number | null;
  created_at: string;
  updated_at?: string | null;
}

export interface DiagnosisStartResult {
  patient_id: string;
  status: string;
  processing_time_ms: number;
  summary: string;
  engine: string;
  warnings: string[];
  symptom_analysis: SymptomAnalysis;
  differential_diagnoses: DifferentialDiagnosis[];
  probability_scores: DiseaseProbability[];
  severity_assessment: SeverityAssessment;
  treatment_path: TreatmentPath;
  clinical_decision_support: ClinicalDecisionSupport;
  diagnosis_result: DiagnosisResult;
}

export interface DiagnosisHistoryItem {
  id: string;
  created_at: string;
  summary?: string | null;
  severity_level?: string | null;
  top_condition?: string | null;
  status: string;
}
