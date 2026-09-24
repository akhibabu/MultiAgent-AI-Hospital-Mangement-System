-- Resource Allocation Agent result history.
-- Run after the Scheduling Agent migration(s) are applied.
-- The agent is planning-only in v1 and does not mutate hospital_resources.

CREATE TABLE IF NOT EXISTS public.resource_allocation_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
  processing_job_id UUID,
  status TEXT NOT NULL DEFAULT 'Completed',
  engine TEXT NOT NULL DEFAULT 'deterministic_resource_allocation_rules_v1',
  planning_only BOOLEAN NOT NULL DEFAULT TRUE,
  priority_level TEXT NOT NULL DEFAULT 'Routine',
  priority_score NUMERIC NOT NULL DEFAULT 0,
  requirements_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  allocations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  conflicts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  allocation_score NUMERIC NOT NULL DEFAULT 0,
  source_result_ids_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  source_availability_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  summary TEXT,
  warnings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  processing_time_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resource_allocation_results_patient_created
  ON public.resource_allocation_results(patient_id, created_at DESC);

ALTER TABLE public.resource_allocation_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "resource_allocation_results_select_authenticated" ON public.resource_allocation_results;
CREATE POLICY "resource_allocation_results_select_authenticated"
  ON public.resource_allocation_results FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "resource_allocation_results_insert_authenticated" ON public.resource_allocation_results;
CREATE POLICY "resource_allocation_results_insert_authenticated"
  ON public.resource_allocation_results FOR INSERT TO authenticated WITH CHECK (true);

COMMENT ON TABLE public.resource_allocation_results IS
  'Append-only planning results produced by the Resource Allocation Agent. v1 does not reserve or mutate inventory.';
COMMENT ON COLUMN public.resource_allocation_results.source_result_ids_json IS
  'Latest Scheduling and Emergency result IDs consumed by Resource Allocation.';
COMMENT ON COLUMN public.resource_allocation_results.allocations_json IS
  'Recommended resource allocation based on the inventory snapshot; not a transactional reservation.';
