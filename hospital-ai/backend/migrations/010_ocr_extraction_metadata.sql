-- =============================================================================
-- Hospital AI — OCR results: extraction method metadata
-- Run after 009_create_ocr_results.sql
-- =============================================================================

ALTER TABLE public.ocr_results
  ADD COLUMN IF NOT EXISTS extraction_method TEXT;

ALTER TABLE public.ocr_results
  ADD COLUMN IF NOT EXISTS document_type TEXT;

ALTER TABLE public.ocr_results
  ADD COLUMN IF NOT EXISTS library_used TEXT;

ALTER TABLE public.ocr_results
  ADD COLUMN IF NOT EXISTS fallback_used BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.ocr_results
  ADD COLUMN IF NOT EXISTS document_status TEXT;

ALTER TABLE public.ocr_results
  ADD COLUMN IF NOT EXISTS processing_logs JSONB NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN public.ocr_results.extraction_method IS
  'embedded_text | ocr — how readable text was obtained';
COMMENT ON COLUMN public.ocr_results.raw_text IS
  'Human-readable document text only. Never PDF binary or object streams.';
