-- Scheduling Agent cross-agent context extension.
-- Safe to run whether migration 020 has already been applied.
-- If scheduling_results does not exist yet, this migration creates its base table first.

CREATE TABLE IF NOT EXISTS public.scheduling_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
  processing_job_id UUID,
  doctor_assignment_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  appointment_scheduling_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  surgery_scheduling_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  follow_up_planning_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  queue_optimization_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  workload_balancing_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  summary TEXT,
  engine TEXT NOT NULL DEFAULT 'deterministic_scheduling_rules_v1',
  emergency_priority_level TEXT NOT NULL DEFAULT 'Routine',
  emergency_priority_score NUMERIC NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'Completed',
  warnings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  processing_time_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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

CREATE INDEX IF NOT EXISTS idx_scheduling_results_patient_created
  ON public.scheduling_results(patient_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_scheduling_results_doctor
  ON public.scheduling_results((doctor_assignment_json->>'selected_doctor_id'), created_at DESC);

ALTER TABLE public.scheduling_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "scheduling_results_select_authenticated" ON public.scheduling_results;
CREATE POLICY "scheduling_results_select_authenticated"
  ON public.scheduling_results FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "scheduling_results_insert_authenticated" ON public.scheduling_results;
CREATE POLICY "scheduling_results_insert_authenticated"
  ON public.scheduling_results FOR INSERT TO authenticated WITH CHECK (true);

COMMENT ON COLUMN public.scheduling_results.source_result_ids_json IS
  'IDs of the latest upstream Diagnosis, Emergency, Prescription, and Medical Report results consumed by Scheduling.';
COMMENT ON COLUMN public.scheduling_results.surgery_recommendation_json IS
  'Evidence from upstream agents supporting surgery/procedure planning; not a definitive clinical order.';
COMMENT ON COLUMN public.scheduling_results.surgery_conflict IS
  'True when structured Diagnosis and Prescription surgery recommendations disagree and require clinician review.';
