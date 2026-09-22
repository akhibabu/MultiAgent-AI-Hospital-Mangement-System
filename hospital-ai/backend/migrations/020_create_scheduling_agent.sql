-- Hospital AI — Scheduling Agent append-only results.
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
  status TEXT NOT NULL DEFAULT 'Completed',
  warnings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  processing_time_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_scheduling_results_patient_created ON public.scheduling_results(patient_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scheduling_results_doctor ON public.scheduling_results((doctor_assignment_json->>'selected_doctor_id'),created_at DESC);
ALTER TABLE public.scheduling_results ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "scheduling_results_select_authenticated" ON public.scheduling_results;
CREATE POLICY "scheduling_results_select_authenticated" ON public.scheduling_results FOR SELECT TO authenticated USING (true);
DROP POLICY IF EXISTS "scheduling_results_insert_authenticated" ON public.scheduling_results;
CREATE POLICY "scheduling_results_insert_authenticated" ON public.scheduling_results FOR INSERT TO authenticated WITH CHECK (true);
COMMENT ON TABLE public.scheduling_results IS 'Append-only Scheduling Agent decision-support plans. Booking remains an explicit user action.';
