-- Hospital Digital Twin simulation history.
-- Read-only mirror + what-if simulation. No automatic resource mutation.

CREATE TABLE IF NOT EXISTS public.digital_twin_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  status TEXT NOT NULL DEFAULT 'Completed',
  engine TEXT NOT NULL DEFAULT 'deterministic_hospital_digital_twin_v1',
  horizon_hours INTEGER NOT NULL DEFAULT 24 CHECK (horizon_hours BETWEEN 1 AND 168),
  baseline_state_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  scenario_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  simulation_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  processing_time_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_digital_twin_runs_created
  ON public.digital_twin_runs(created_at DESC);

ALTER TABLE public.digital_twin_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "digital_twin_runs_select_authenticated" ON public.digital_twin_runs;
CREATE POLICY "digital_twin_runs_select_authenticated"
  ON public.digital_twin_runs FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "digital_twin_runs_insert_authenticated" ON public.digital_twin_runs;
CREATE POLICY "digital_twin_runs_insert_authenticated"
  ON public.digital_twin_runs FOR INSERT TO authenticated WITH CHECK (true);

DROP TRIGGER IF EXISTS trg_digital_twin_runs_updated_at ON public.digital_twin_runs;
CREATE TRIGGER trg_digital_twin_runs_updated_at
  BEFORE UPDATE ON public.digital_twin_runs
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

COMMENT ON TABLE public.digital_twin_runs IS
  'Append-only hospital Digital Twin snapshots and deterministic what-if simulations.';
COMMENT ON COLUMN public.digital_twin_runs.baseline_state_json IS
  'Read-only operational state assembled from live hospital resources and agent outputs.';
COMMENT ON COLUMN public.digital_twin_runs.simulation_json IS
  'Projected capacity, bottlenecks, and advisory feedback signals for operational agents.';
