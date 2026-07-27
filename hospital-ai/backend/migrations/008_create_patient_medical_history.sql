-- =============================================================================
-- Hospital AI — Intake Agent: Medical History Extraction (Stage 2)
-- Run in Supabase SQL Editor after 007_create_intake_agent.sql
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.patient_medical_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  processing_job_id UUID REFERENCES public.document_processing_jobs (id) ON DELETE SET NULL,
  medical_history_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  timeline_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT patient_medical_history_patient_unique UNIQUE (patient_id)
);

CREATE INDEX IF NOT EXISTS idx_pmh_patient ON public.patient_medical_history (patient_id);
CREATE INDEX IF NOT EXISTS idx_pmh_job ON public.patient_medical_history (processing_job_id);
CREATE INDEX IF NOT EXISTS idx_pmh_history_gin ON public.patient_medical_history USING GIN (medical_history_json);
CREATE INDEX IF NOT EXISTS idx_pmh_timeline_gin ON public.patient_medical_history USING GIN (timeline_json);

DROP TRIGGER IF EXISTS trg_patient_medical_history_updated_at ON public.patient_medical_history;
CREATE TRIGGER trg_patient_medical_history_updated_at
  BEFORE UPDATE ON public.patient_medical_history
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.patient_medical_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "pmh_select_authenticated" ON public.patient_medical_history;
CREATE POLICY "pmh_select_authenticated"
  ON public.patient_medical_history FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "pmh_insert_authenticated" ON public.patient_medical_history;
CREATE POLICY "pmh_insert_authenticated"
  ON public.patient_medical_history FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "pmh_update_authenticated" ON public.patient_medical_history;
CREATE POLICY "pmh_update_authenticated"
  ON public.patient_medical_history FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "pmh_delete_authenticated" ON public.patient_medical_history;
CREATE POLICY "pmh_delete_authenticated"
  ON public.patient_medical_history FOR DELETE TO authenticated USING (true);

COMMENT ON TABLE public.patient_medical_history IS
  'Unified medical history extracted by Intake stage 2. Does not include OCR of the new upload.';
COMMENT ON COLUMN public.patient_medical_history.medical_history_json IS
  'Canonical history object: patient, allergies, conditions, medications, timeline, etc.';
COMMENT ON COLUMN public.patient_medical_history.timeline_json IS
  'Chronological event list (also embedded in medical_history_json.timeline).';
