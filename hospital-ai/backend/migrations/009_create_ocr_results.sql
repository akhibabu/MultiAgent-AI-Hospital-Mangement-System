-- =============================================================================
-- Hospital AI — Intake Agent Stage 3: OCR on Reports
-- Run in Supabase SQL Editor after 008_create_patient_medical_history.sql
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.ocr_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  processing_job_id UUID NOT NULL REFERENCES public.document_processing_jobs (id) ON DELETE CASCADE,
  patient_id UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  document_id UUID,
  provider TEXT NOT NULL,
  raw_text TEXT NOT NULL DEFAULT '',
  tables_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  images_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  detected_language TEXT,
  page_count INTEGER NOT NULL DEFAULT 1 CHECK (page_count >= 0),
  processing_time_ms INTEGER CHECK (processing_time_ms IS NULL OR processing_time_ms >= 0),
  confidence NUMERIC(5, 4) CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
  provenance_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ocr_results_job ON public.ocr_results (processing_job_id);
CREATE INDEX IF NOT EXISTS idx_ocr_results_patient ON public.ocr_results (patient_id);
CREATE INDEX IF NOT EXISTS idx_ocr_results_created ON public.ocr_results (created_at DESC);

ALTER TABLE public.ocr_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "ocr_results_select_authenticated" ON public.ocr_results;
CREATE POLICY "ocr_results_select_authenticated"
  ON public.ocr_results FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "ocr_results_insert_authenticated" ON public.ocr_results;
CREATE POLICY "ocr_results_insert_authenticated"
  ON public.ocr_results FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "ocr_results_update_authenticated" ON public.ocr_results;
CREATE POLICY "ocr_results_update_authenticated"
  ON public.ocr_results FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "ocr_results_delete_authenticated" ON public.ocr_results;
CREATE POLICY "ocr_results_delete_authenticated"
  ON public.ocr_results FOR DELETE TO authenticated USING (true);

-- Enrich Patient AI Context for OCR metadata (append-only JSON; never drops history)
ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS ocr_completed BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS ocr_provider TEXT;

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS ocr_confidence NUMERIC(5, 4);

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS ocr_timestamp TIMESTAMPTZ;

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS patient_context_json JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS context_version INTEGER NOT NULL DEFAULT 1;

COMMENT ON TABLE public.ocr_results IS
  'Intake Stage 3 OCR output — raw text/tables/images only. No medical interpretation.';
COMMENT ON COLUMN public.patient_ai_context.patient_context_json IS
  'Accumulated Patient Context. History is preserved; OCR appends under ocr_* keys.';
