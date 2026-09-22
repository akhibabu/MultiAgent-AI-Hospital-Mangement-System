-- Scheduling Agent cross-agent context extension.
-- Run this AFTER 020_create_scheduling_agent.sql.
-- This migration intentionally contains no CREATE TABLE, CREATE INDEX, or RLS
-- statements, so the base scheduling schema is not unnecessarily relocked.

ALTER TABLE public.scheduling_results
  ADD COLUMN IF NOT EXISTS visit_type TEXT NOT NULL DEFAULT 'Consultation',
  ADD COLUMN IF NOT EXISTS derived_department TEXT,
  ADD COLUMN IF NOT EXISTS derived_specialists_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS procedures_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS surgery_recommendation_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS surgery_sources_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS surgery_conflict BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS source_result_ids_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS source_availability_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS recommended_tests_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS recommended_imaging_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS recommended_medications_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS treatment_modes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS resource_requirements_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS treatment_validation_status TEXT;

COMMENT ON COLUMN public.scheduling_results.source_result_ids_json IS
  'IDs of the latest upstream Diagnosis, Emergency, Prescription, and Medical Report results consumed by Scheduling.';

COMMENT ON COLUMN public.scheduling_results.surgery_recommendation_json IS
  'Evidence from upstream agents supporting surgery/procedure planning; not a definitive clinical order.';

COMMENT ON COLUMN public.scheduling_results.surgery_conflict IS
  'True when structured Diagnosis and Prescription surgery recommendations disagree and require clinician review.';
