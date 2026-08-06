-- =============================================================================
-- Hospital AI — AI Provider Orchestrator (multi-provider failover)
-- Run in Supabase SQL Editor after 017_create_ai_orchestrator_tables.sql
--
-- The AI layer moved from a single provider (Groq) to a fleet with automatic
-- failover: Groq -> Gemini -> OpenRouter -> HuggingFace. `ai_interaction_logs`
-- already recorded *which* provider served a call; these columns record the
-- failover story around it — who was tried first, why the system switched,
-- and the full per-provider attempt timeline.
--
-- Without this an operator can see "Gemini answered 180 requests yesterday"
-- but not "…because Groq's daily token quota ran out at 14:20", which is the
-- question that actually gets asked after an incident.
--
-- Safe to re-run: every statement is IF NOT EXISTS / idempotent, and every
-- new column is nullable or defaulted so existing rows stay valid.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- FAILOVER TELEMETRY on ai_interaction_logs
-- ---------------------------------------------------------------------------

-- Provider the load balancer selected first. Equals `provider` when no
-- failover occurred, which keeps "was this a fallback?" a single comparison.
ALTER TABLE public.ai_interaction_logs
  ADD COLUMN IF NOT EXISTS primary_provider TEXT;

-- True when a provider other than `primary_provider` produced the response.
ALTER TABLE public.ai_interaction_logs
  ADD COLUMN IF NOT EXISTS fallback_used BOOLEAN NOT NULL DEFAULT false;

-- Machine-readable reason the primary was abandoned. Mirrors the taxonomy in
-- app/ai/orchestrator/providers/errors.py:
--   quota_exceeded | rate_limited | invalid_api_key | model_not_found
--   | timeout | network_failure | server_error | invalid_response
--   | provider_offline | malformed_request
ALTER TABLE public.ai_interaction_logs
  ADD COLUMN IF NOT EXISTS fallback_reason TEXT;

-- Ordered attempt timeline, one element per provider tried:
--   [{"provider","model","outcome","duration_ms","retries","reason","error"}]
-- Powers the Developer Mode "execution timeline" panel.
ALTER TABLE public.ai_interaction_logs
  ADD COLUMN IF NOT EXISTS attempts JSONB NOT NULL DEFAULT '[]'::jsonb;

-- Best-effort USD estimate from providers.yaml pricing. Free tiers record
-- 0.00; the column exists so the cost dashboard keeps working unchanged when
-- a paid provider is enabled later.
ALTER TABLE public.ai_interaction_logs
  ADD COLUMN IF NOT EXISTS estimated_cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 0;

-- Status values grew with the taxonomy; documented here rather than enforced
-- by a CHECK so a new failure mode can never reject a telemetry write:
--   success | error | parse_error | invalid_response | timeout | cancelled
COMMENT ON COLUMN public.ai_interaction_logs.status IS
  'success | error | parse_error | invalid_response | timeout | cancelled';

-- Partial index: failover rows are a small minority, and "show me every
-- failover in the last 24h" is the query the dashboard actually runs.
CREATE INDEX IF NOT EXISTS idx_ai_interaction_logs_fallback
  ON public.ai_interaction_logs (created_at DESC)
  WHERE fallback_used = true;

-- Backs the per-provider reliability breakdown on the dashboard.
CREATE INDEX IF NOT EXISTS idx_ai_interaction_logs_provider
  ON public.ai_interaction_logs (provider, created_at DESC);


-- ---------------------------------------------------------------------------
-- PROVIDER HEALTH EVENTS
-- Durable history of provider state transitions (went offline, quota
-- exhausted, recovered, failed over). The in-process ProviderHealthMonitor
-- keeps only a bounded rolling window and resets on restart; this table is
-- what survives a deploy so quota patterns can be reviewed over weeks.
-- Append-only.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.ai_provider_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL,
  -- offline | recovered | failover | quota_exhausted
  event TEXT NOT NULL,
  reason TEXT,
  detail TEXT,
  -- Provider traffic was redirected to, for `failover` events.
  target_provider TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_provider_events_created
  ON public.ai_provider_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_provider_events_provider
  ON public.ai_provider_events (provider, created_at DESC);

ALTER TABLE public.ai_provider_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "ai_provider_events_select_authenticated" ON public.ai_provider_events;
CREATE POLICY "ai_provider_events_select_authenticated"
  ON public.ai_provider_events FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "ai_provider_events_insert_authenticated" ON public.ai_provider_events;
CREATE POLICY "ai_provider_events_insert_authenticated"
  ON public.ai_provider_events FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "ai_provider_events_delete_authenticated" ON public.ai_provider_events;
CREATE POLICY "ai_provider_events_delete_authenticated"
  ON public.ai_provider_events FOR DELETE TO authenticated USING (true);
