-- =============================================================================
-- Hospital AI — Intake Agent Stage 5: Patient Risk Profiling
-- Run in Supabase SQL Editor after 012_create_medical_entities.sql
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.patient_risk_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  processing_job_id UUID NOT NULL UNIQUE
    REFERENCES public.document_processing_jobs (id) ON DELETE CASCADE,
  patient_id UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  overall_level TEXT NOT NULL,
  overall_score NUMERIC(6, 2) NOT NULL DEFAULT 0
    CHECK (overall_score >= 0 AND overall_score <= 100),
  overall_confidence NUMERIC(5, 4),
  categories_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  top_risk_factors_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  important_findings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  alerts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  distribution_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  timeline_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  disclaimer TEXT,
  processing_time_ms INTEGER,
  status TEXT NOT NULL DEFAULT 'Completed',
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_patient_risk_profiles_patient
  ON public.patient_risk_profiles (patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_risk_profiles_created
  ON public.patient_risk_profiles (created_at DESC);

ALTER TABLE public.patient_risk_profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "patient_risk_profiles_select_authenticated"
  ON public.patient_risk_profiles;
CREATE POLICY "patient_risk_profiles_select_authenticated"
  ON public.patient_risk_profiles FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "patient_risk_profiles_insert_authenticated"
  ON public.patient_risk_profiles;
CREATE POLICY "patient_risk_profiles_insert_authenticated"
  ON public.patient_risk_profiles FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "patient_risk_profiles_update_authenticated"
  ON public.patient_risk_profiles;
CREATE POLICY "patient_risk_profiles_update_authenticated"
  ON public.patient_risk_profiles FOR UPDATE TO authenticated
  USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "patient_risk_profiles_delete_authenticated"
  ON public.patient_risk_profiles;
CREATE POLICY "patient_risk_profiles_delete_authenticated"
  ON public.patient_risk_profiles FOR DELETE TO authenticated USING (true);

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS risk_completed BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS risk_level TEXT;

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS risk_score NUMERIC(6, 2);

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS risk_timestamp TIMESTAMPTZ;

COMMENT ON TABLE public.patient_risk_profiles IS
  'Intake Stage 5 — clinical decision-support risk estimates. Not diagnosis or treatment.';
