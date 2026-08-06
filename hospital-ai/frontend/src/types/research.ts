/** Research Agent types — evidence enrichment for Diagnosis Agent results. */
import type { OrchestratorDebugInfo } from '@/types/aiOrchestrator';

export type EvidenceLevel = 'High' | 'Medium' | 'Low';

export const EVIDENCE_LEVEL_TONE: Record<
  string,
  'green' | 'blue' | 'amber' | 'red' | 'gray'
> = {
  High: 'green',
  Medium: 'amber',
  Low: 'gray',
};

export interface LiteratureItem {
  reference_id: string;
  title: string;
  authors: string[];
  journal: string;
  publication_year: number;
  study_type: string;
  summary: string;
  url: string;
  condition: string;
  relevance_score: number;
}

export interface ClinicalTrialItem {
  trial_id: string;
  title: string;
  status: string;
  phase: string;
  outcome_summary: string;
  eligibility_summary: string;
  condition: string;
  url: string;
  relevance_score: number;
}

export interface GuidelineItem {
  source: string;
  title: string;
  recommendation: string;
  condition: string;
  published_year: number;
  url: string;
  relevance_score: number;
}

export interface DrugEvidenceItem {
  drug_name: string;
  condition: string;
  effectiveness_summary: string;
  known_side_effects: string[];
  contraindications: string[];
  drug_interactions: string[];
  supporting_evidence: string;
  relevance_score: number;
}

export interface ClinicalEvidence {
  id?: string;
  evidence_type: 'pubmed' | 'clinical_trial' | 'guideline' | 'drug_efficacy';
  condition: string;
  title: string;
  source: string;
  reference_id: string;
  url: string;
  publication_date?: string | null;
  summary: string;
  evidence_level: EvidenceLevel | string;
  relevance_score: number;
  confidence: number;
}

export interface ResearchRecommendation {
  condition: string;
  supporting_literature: string[];
  clinical_guidelines: string[];
  evidence_summary: string;
  recommended_diagnostic_tests: string[];
  research_highlights: string[];
  confidence_score: number;
}

export interface ResearchResult {
  id: string;
  patient_id: string;
  diagnosis_result_id?: string | null;
  conditions_researched_json: string[];
  pubmed_json: LiteratureItem[];
  clinical_trials_json: ClinicalTrialItem[];
  guidelines_json: GuidelineItem[];
  drug_efficacy_json: DrugEvidenceItem[];
  evidence_ranking_summary_json: Record<string, number>;
  recommendation_json: ResearchRecommendation[];
  summary?: string | null;
  provider: string;
  status: string;
  error_message?: string | null;
  processing_time_ms?: number | null;
  created_at: string;
  updated_at?: string | null;
}

export interface ResearchStartResult {
  patient_id: string;
  diagnosis_result_id?: string | null;
  status: string;
  processing_time_ms: number;
  summary: string;
  provider: string;
  warnings: string[];
  conditions_researched: string[];
  pubmed_results: LiteratureItem[];
  clinical_trials: ClinicalTrialItem[];
  guidelines: GuidelineItem[];
  drug_efficacy: DrugEvidenceItem[];
  evidence: ClinicalEvidence[];
  evidence_level_counts: Record<string, number>;
  recommendations: ResearchRecommendation[];
  research_result: ResearchResult;
  ai_debug: OrchestratorDebugInfo[];
}

export interface ResearchHistoryItem {
  id: string;
  created_at: string;
  summary?: string | null;
  conditions_researched: string[];
  status: string;
}
