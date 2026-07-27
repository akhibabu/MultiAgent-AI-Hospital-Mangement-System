-- =============================================================================
-- Hospital AI — OCR results: clean text + processing metadata (Stage 3 redesign)
-- Run after 010_ocr_extraction_metadata.sql
-- =============================================================================

ALTER TABLE public.ocr_results
  ADD COLUMN IF NOT EXISTS processing_method TEXT;

ALTER TABLE public.ocr_results
  ADD COLUMN IF NOT EXISTS ocr_provider TEXT;

ALTER TABLE public.ocr_results
  ADD COLUMN IF NOT EXISTS clean_text TEXT;

ALTER TABLE public.ocr_results
  ADD COLUMN IF NOT EXISTS character_count INTEGER;

ALTER TABLE public.ocr_results
  ADD COLUMN IF NOT EXISTS word_count INTEGER;

ALTER TABLE public.ocr_results
  ADD COLUMN IF NOT EXISTS status TEXT;

-- Backfill from 010 columns when present
UPDATE public.ocr_results
SET processing_method = COALESCE(processing_method, extraction_method)
WHERE processing_method IS NULL AND extraction_method IS NOT NULL;

UPDATE public.ocr_results
SET clean_text = COALESCE(clean_text, raw_text)
WHERE clean_text IS NULL AND raw_text IS NOT NULL;

UPDATE public.ocr_results
SET status = COALESCE(status, document_status, 'Completed')
WHERE status IS NULL;

UPDATE public.ocr_results
SET ocr_provider = COALESCE(ocr_provider, provider)
WHERE ocr_provider IS NULL AND provider IS NOT NULL;

COMMENT ON COLUMN public.ocr_results.processing_method IS
  'embedded_text | ocr — how readable text was obtained';
COMMENT ON COLUMN public.ocr_results.clean_text IS
  'Clean human-readable text for NER. Never PDF binary.';
COMMENT ON COLUMN public.ocr_results.raw_text IS
  'Pre-clean extracted text (still human-readable). Never PDF binary.';
