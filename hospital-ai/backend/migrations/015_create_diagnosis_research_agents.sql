-- =============================================================================
-- Hospital AI — Diagnosis Agent + Research Agent
-- Run in Supabase SQL Editor after 014_create_patient_knowledge_graphs.sql
--
-- Diagnosis Agent and Research Agent consume Intake Agent output ONLY
-- (patient_ai_context, patient_medical_history, patient_risk_profiles,
-- patient_knowledge_graphs) — read only. They never write to those tables.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- DIAGNOSIS RESULTS
-- Append-only run history. One row per Diagnosis Agent execution.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.diagnosis_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  processing_job_id UUID REFERENCES public.document_processing_jobs (id) ON DELETE SET NULL,
  chief_complaint TEXT,
  focus_symptoms_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  symptom_analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  differential_diagnoses_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  probability_scores_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  severity_assessment_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  treatment_path_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  clinical_decision_support_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  summary TEXT,
  engine TEXT NOT NULL DEFAULT 'rule_based',
  status TEXT NOT NULL DEFAULT 'Completed',
  error_message TEXT,
  processing_time_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_diagnosis_results_patient
  ON public.diagnosis_results (patient_id);
CREATE INDEX IF NOT EXISTS idx_diagnosis_results_created
  ON public.diagnosis_results (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_diagnosis_results_job
  ON public.diagnosis_results (processing_job_id);

DROP TRIGGER IF EXISTS trg_diagnosis_results_updated_at ON public.diagnosis_results;
CREATE TRIGGER trg_diagnosis_results_updated_at
  BEFORE UPDATE ON public.diagnosis_results
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.diagnosis_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "diagnosis_results_select_authenticated" ON public.diagnosis_results;
CREATE POLICY "diagnosis_results_select_authenticated"
  ON public.diagnosis_results FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "diagnosis_results_insert_authenticated" ON public.diagnosis_results;
CREATE POLICY "diagnosis_results_insert_authenticated"
  ON public.diagnosis_results FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "diagnosis_results_update_authenticated" ON public.diagnosis_results;
CREATE POLICY "diagnosis_results_update_authenticated"
  ON public.diagnosis_results FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "diagnosis_results_delete_authenticated" ON public.diagnosis_results;
CREATE POLICY "diagnosis_results_delete_authenticated"
  ON public.diagnosis_results FOR DELETE TO authenticated USING (true);

-- ---------------------------------------------------------------------------
-- RESEARCH RESULTS
-- Append-only run history. One row per Research Agent execution.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.research_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  diagnosis_result_id UUID REFERENCES public.diagnosis_results (id) ON DELETE SET NULL,
  conditions_researched_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  pubmed_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  clinical_trials_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  guidelines_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  drug_efficacy_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  evidence_ranking_summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  recommendation_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  summary TEXT,
  provider TEXT NOT NULL DEFAULT 'mock',
  status TEXT NOT NULL DEFAULT 'Completed',
  error_message TEXT,
  processing_time_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_results_patient
  ON public.research_results (patient_id);
CREATE INDEX IF NOT EXISTS idx_research_results_created
  ON public.research_results (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_results_diagnosis
  ON public.research_results (diagnosis_result_id);

DROP TRIGGER IF EXISTS trg_research_results_updated_at ON public.research_results;
CREATE TRIGGER trg_research_results_updated_at
  BEFORE UPDATE ON public.research_results
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.research_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "research_results_select_authenticated" ON public.research_results;
CREATE POLICY "research_results_select_authenticated"
  ON public.research_results FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "research_results_insert_authenticated" ON public.research_results;
CREATE POLICY "research_results_insert_authenticated"
  ON public.research_results FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "research_results_update_authenticated" ON public.research_results;
CREATE POLICY "research_results_update_authenticated"
  ON public.research_results FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "research_results_delete_authenticated" ON public.research_results;
CREATE POLICY "research_results_delete_authenticated"
  ON public.research_results FOR DELETE TO authenticated USING (true);

-- ---------------------------------------------------------------------------
-- CLINICAL EVIDENCE
-- One row per ranked evidence item (PubMed, clinical trial, guideline, drug
-- efficacy) produced by a Research Agent run.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.clinical_evidence (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  research_result_id UUID NOT NULL REFERENCES public.research_results (id) ON DELETE CASCADE,
  evidence_type TEXT NOT NULL CHECK (
    evidence_type IN ('pubmed', 'clinical_trial', 'guideline', 'drug_efficacy')
  ),
  condition TEXT NOT NULL,
  title TEXT NOT NULL,
  source TEXT NOT NULL,
  reference_id TEXT,
  url TEXT,
  publication_date DATE,
  summary TEXT,
  evidence_level TEXT NOT NULL DEFAULT 'Medium' CHECK (
    evidence_level IN ('High', 'Medium', 'Low')
  ),
  relevance_score NUMERIC(5, 4) NOT NULL DEFAULT 0,
  confidence NUMERIC(5, 4) NOT NULL DEFAULT 0,
  raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clinical_evidence_research_result
  ON public.clinical_evidence (research_result_id);
CREATE INDEX IF NOT EXISTS idx_clinical_evidence_condition
  ON public.clinical_evidence (condition);
CREATE INDEX IF NOT EXISTS idx_clinical_evidence_level
  ON public.clinical_evidence (evidence_level);

ALTER TABLE public.clinical_evidence ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "clinical_evidence_select_authenticated" ON public.clinical_evidence;
CREATE POLICY "clinical_evidence_select_authenticated"
  ON public.clinical_evidence FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "clinical_evidence_insert_authenticated" ON public.clinical_evidence;
CREATE POLICY "clinical_evidence_insert_authenticated"
  ON public.clinical_evidence FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "clinical_evidence_update_authenticated" ON public.clinical_evidence;
CREATE POLICY "clinical_evidence_update_authenticated"
  ON public.clinical_evidence FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "clinical_evidence_delete_authenticated" ON public.clinical_evidence;
CREATE POLICY "clinical_evidence_delete_authenticated"
  ON public.clinical_evidence FOR DELETE TO authenticated USING (true);

COMMENT ON TABLE public.diagnosis_results IS
  'Diagnosis Agent — clinical decision-support output. Assists, never replaces, a physician. No medication is prescribed.';
COMMENT ON TABLE public.research_results IS
  'Research Agent — evidence enrichment for Diagnosis Agent results. Never invents medical information.';
COMMENT ON TABLE public.clinical_evidence IS
  'Ranked evidence items (PubMed, clinical trials, guidelines, drug efficacy) backing a research_results run.';
