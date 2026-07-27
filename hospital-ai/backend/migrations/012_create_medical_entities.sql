-- =============================================================================
-- Hospital AI — Intake Agent Stage 4: Medical Entity Recognition
-- Run in Supabase SQL Editor after 011_ocr_clean_text_metadata.sql
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.medical_entities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  processing_job_id UUID NOT NULL REFERENCES public.document_processing_jobs (id) ON DELETE CASCADE,
  document_id UUID,
  ocr_result_id UUID REFERENCES public.ocr_results (id) ON DELETE SET NULL,
  entity_type TEXT NOT NULL,
  entity_value TEXT NOT NULL,
  confidence NUMERIC(5, 4) NOT NULL DEFAULT 0
    CHECK (confidence >= 0 AND confidence <= 1),
  page_number INTEGER NOT NULL DEFAULT 1 CHECK (page_number >= 1),
  sentence TEXT,
  char_start INTEGER,
  char_end INTEGER,
  source_document TEXT,
  extraction_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_medical_entities_patient
  ON public.medical_entities (patient_id);
CREATE INDEX IF NOT EXISTS idx_medical_entities_job
  ON public.medical_entities (processing_job_id);
CREATE INDEX IF NOT EXISTS idx_medical_entities_type
  ON public.medical_entities (entity_type);
CREATE INDEX IF NOT EXISTS idx_medical_entities_created
  ON public.medical_entities (created_at DESC);

-- Run summary per job (statistics + grouped buckets)
CREATE TABLE IF NOT EXISTS public.medical_entity_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  processing_job_id UUID NOT NULL UNIQUE
    REFERENCES public.document_processing_jobs (id) ON DELETE CASCADE,
  patient_id UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  ocr_result_id UUID REFERENCES public.ocr_results (id) ON DELETE SET NULL,
  entity_count INTEGER NOT NULL DEFAULT 0,
  statistics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  entities_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  source_text_preview TEXT,
  confidence NUMERIC(5, 4),
  processing_time_ms INTEGER,
  status TEXT NOT NULL DEFAULT 'Completed',
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_medical_entity_results_patient
  ON public.medical_entity_results (patient_id);

ALTER TABLE public.medical_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.medical_entity_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "medical_entities_select_authenticated" ON public.medical_entities;
CREATE POLICY "medical_entities_select_authenticated"
  ON public.medical_entities FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "medical_entities_insert_authenticated" ON public.medical_entities;
CREATE POLICY "medical_entities_insert_authenticated"
  ON public.medical_entities FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "medical_entities_update_authenticated" ON public.medical_entities;
CREATE POLICY "medical_entities_update_authenticated"
  ON public.medical_entities FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "medical_entities_delete_authenticated" ON public.medical_entities;
CREATE POLICY "medical_entities_delete_authenticated"
  ON public.medical_entities FOR DELETE TO authenticated USING (true);

DROP POLICY IF EXISTS "medical_entity_results_select_authenticated" ON public.medical_entity_results;
CREATE POLICY "medical_entity_results_select_authenticated"
  ON public.medical_entity_results FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "medical_entity_results_insert_authenticated" ON public.medical_entity_results;
CREATE POLICY "medical_entity_results_insert_authenticated"
  ON public.medical_entity_results FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "medical_entity_results_update_authenticated" ON public.medical_entity_results;
CREATE POLICY "medical_entity_results_update_authenticated"
  ON public.medical_entity_results FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "medical_entity_results_delete_authenticated" ON public.medical_entity_results;
CREATE POLICY "medical_entity_results_delete_authenticated"
  ON public.medical_entity_results FOR DELETE TO authenticated USING (true);

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS ner_completed BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS ner_confidence NUMERIC(5, 4);

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS ner_timestamp TIMESTAMPTZ;

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS ner_entity_count INTEGER NOT NULL DEFAULT 0;

COMMENT ON TABLE public.medical_entities IS
  'Intake Stage 4 — recognized medical entities only. No diagnosis or treatment advice.';
COMMENT ON TABLE public.medical_entity_results IS
  'Intake Stage 4 run summary: entity statistics and patient-facing summary buckets.';
