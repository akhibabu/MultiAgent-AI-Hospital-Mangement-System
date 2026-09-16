-- =============================================================================
-- Hospital AI — AI Orchestrator core tables
-- Run in Supabase SQL Editor after 016_create_prescription_medical_report_agents.sql
--
-- Backs the centralized AI Orchestrator (app/ai/orchestrator/). Every AI
-- Agent (Intake, Diagnosis, Research, Prescription, Medical Report) now
-- calls AIOrchestrator.run() instead of talking to an LLM provider
-- directly. This migration adds:
--   1. ai_conversation_memory — per-patient, per-agent AI memory (prompt +
--      response history), reused across agents.
--   2. ai_interaction_logs    — one row per orchestrator call, powering the
--      Usage Tracker / AI Orchestrator admin dashboard.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- AI CONVERSATION MEMORY
-- Append-only. One row per orchestrator call, per (patient, agent, task).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.ai_conversation_memory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  agent TEXT NOT NULL,
  task TEXT NOT NULL,
  prompt_rendered TEXT NOT NULL DEFAULT '',
  response_text TEXT NOT NULL DEFAULT '',
  response_json JSONB,
  model TEXT,
  provider TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_conversation_memory_patient_agent
  ON public.ai_conversation_memory (patient_id, agent, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_conversation_memory_created
  ON public.ai_conversation_memory (created_at DESC);

ALTER TABLE public.ai_conversation_memory ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "ai_conversation_memory_select_authenticated" ON public.ai_conversation_memory;
CREATE POLICY "ai_conversation_memory_select_authenticated"
  ON public.ai_conversation_memory FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "ai_conversation_memory_insert_authenticated" ON public.ai_conversation_memory;
CREATE POLICY "ai_conversation_memory_insert_authenticated"
  ON public.ai_conversation_memory FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "ai_conversation_memory_delete_authenticated" ON public.ai_conversation_memory;
CREATE POLICY "ai_conversation_memory_delete_authenticated"
  ON public.ai_conversation_memory FOR DELETE TO authenticated USING (true);

-- ---------------------------------------------------------------------------
-- AI INTERACTION LOGS
-- Append-only. One row per AIOrchestrator.run() call (success or failure).
-- Powers GET /api/ai/orchestrator/status, /stats, /logs.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.ai_interaction_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID REFERENCES public.patients (id) ON DELETE SET NULL,
  agent TEXT NOT NULL,
  task TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'success', -- success | error | parse_error
  duration_ms INTEGER NOT NULL DEFAULT 0,
  prompt_tokens INTEGER NOT NULL DEFAULT 0,
  completion_tokens INTEGER NOT NULL DEFAULT 0,
  total_tokens INTEGER NOT NULL DEFAULT 0,
  cache_hit BOOLEAN NOT NULL DEFAULT false,
  retry_count INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_interaction_logs_created
  ON public.ai_interaction_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_interaction_logs_agent
  ON public.ai_interaction_logs (agent, created_at DESC);

ALTER TABLE public.ai_interaction_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "ai_interaction_logs_select_authenticated" ON public.ai_interaction_logs;
CREATE POLICY "ai_interaction_logs_select_authenticated"
  ON public.ai_interaction_logs FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "ai_interaction_logs_insert_authenticated" ON public.ai_interaction_logs;
CREATE POLICY "ai_interaction_logs_insert_authenticated"
  ON public.ai_interaction_logs FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "ai_interaction_logs_delete_authenticated" ON public.ai_interaction_logs;
CREATE POLICY "ai_interaction_logs_delete_authenticated"
  ON public.ai_interaction_logs FOR DELETE TO authenticated USING (true);
