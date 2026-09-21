-- =============================================================================
-- Hospital AI — Emergency Agent
--
-- Stores append-only Emergency Agent runs. The agent reads the shared Intake
-- Patient Context and writes only its own result table.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.emergency_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
  processing_job_id UUID,
  vital_monitoring_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  triage_classification_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  critical_event_detection_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  icu_requirement_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  emergency_alerts_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  patient_priority_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  summary TEXT,
  engine TEXT NOT NULL DEFAULT 'deterministic_emergency_rules_v1',
  status TEXT NOT NULL DEFAULT 'Completed',
  warnings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  processing_time_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_emergency_results_patient_created
  ON public.emergency_results (patient_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_emergency_results_triage
  ON public.emergency_results ((triage_classification_json->>'category'), created_at DESC);

ALTER TABLE public.emergency_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "emergency_results_select_authenticated" ON public.emergency_results;
CREATE POLICY "emergency_results_select_authenticated"
  ON public.emergency_results FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "emergency_results_insert_authenticated" ON public.emergency_results;
CREATE POLICY "emergency_results_insert_authenticated"
  ON public.emergency_results FOR INSERT TO authenticated WITH CHECK (true);

COMMENT ON TABLE public.emergency_results IS
  'Append-only Emergency Agent decision-support results. Not a clinical record of definitive diagnosis or treatment.';
