/** Intake Stage 5 — Patient Risk Profiling types. */

export type RiskLevel = 'Very Low' | 'Low' | 'Moderate' | 'High' | 'Critical';

export interface CategoryRisk {
  name: string;
  level: RiskLevel | string;
  score: number;
  reason: string;
  evidence: string[];
  confidence: number;
  factors: string[];
}

export interface RiskAlert {
  severity: 'info' | 'warning' | 'critical' | string;
  message: string;
  category?: string | null;
}

export interface RiskProfile {
  id: string;
  processing_job_id: string;
  patient_id: string;
  overall_level: string;
  overall_score: number;
  overall_confidence?: number | null;
  categories_json: CategoryRisk[];
  top_risk_factors_json: string[];
  important_findings_json: string[];
  alerts_json: RiskAlert[];
  distribution_json: Record<string, number>;
  timeline_json: Array<Record<string, unknown>>;
  disclaimer?: string | null;
  processing_time_ms?: number | null;
  status: string;
  error_message?: string | null;
  created_at: string;
}

export interface RiskStartResult {
  job_id: string;
  patient_id: string;
  status: string;
  current_stage: string;
  next_stage: string;
  overall_level: string;
  overall_score: number;
  overall_confidence: number;
  processing_time_ms: number;
  categories: CategoryRisk[];
  top_risk_factors: string[];
  important_findings: string[];
  alerts: RiskAlert[];
  distribution: Record<string, number>;
  timeline: Array<Record<string, unknown>>;
  disclaimer: string;
  warnings: string[];
  risk_profile: RiskProfile;
  processing_job: { id: string; current_stage: string; status: string };
  patient_context_version: number;
}

export interface RiskStatus {
  job_id: string;
  status: string;
  current_stage: string;
  next_stage: string;
  progress_pct: number;
  risk_completed: boolean;
  overall_level?: string | null;
  overall_score?: number | null;
  error_message?: string | null;
}

export const RISK_LEVEL_TONE: Record<
  string,
  'green' | 'blue' | 'amber' | 'red' | 'gray'
> = {
  'Very Low': 'green',
  Low: 'green',
  Moderate: 'amber',
  High: 'red',
  Critical: 'red',
};
