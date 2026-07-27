-- =============================================================================
-- Hospital AI — Intake Agent Stage 6: Patient Knowledge Graph
-- Run in Supabase SQL Editor after 013_create_patient_risk_profiles.sql
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.patient_knowledge_graphs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  processing_job_id UUID UNIQUE
    REFERENCES public.document_processing_jobs (id) ON DELETE SET NULL,
  patient_id UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  nodes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  relationships_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  statistics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  patient_summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  summary TEXT,
  graph_version INTEGER NOT NULL DEFAULT 1,
  node_count INTEGER NOT NULL DEFAULT 0,
  relationship_count INTEGER NOT NULL DEFAULT 0,
  builder_logs_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  validation_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'Completed',
  error_message TEXT,
  processing_time_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_patient_knowledge_graphs_patient
  ON public.patient_knowledge_graphs (patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_knowledge_graphs_updated
  ON public.patient_knowledge_graphs (updated_at DESC);

ALTER TABLE public.patient_knowledge_graphs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "patient_knowledge_graphs_select_authenticated"
  ON public.patient_knowledge_graphs;
CREATE POLICY "patient_knowledge_graphs_select_authenticated"
  ON public.patient_knowledge_graphs FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "patient_knowledge_graphs_insert_authenticated"
  ON public.patient_knowledge_graphs;
CREATE POLICY "patient_knowledge_graphs_insert_authenticated"
  ON public.patient_knowledge_graphs FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "patient_knowledge_graphs_update_authenticated"
  ON public.patient_knowledge_graphs;
CREATE POLICY "patient_knowledge_graphs_update_authenticated"
  ON public.patient_knowledge_graphs FOR UPDATE TO authenticated
  USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "patient_knowledge_graphs_delete_authenticated"
  ON public.patient_knowledge_graphs;
CREATE POLICY "patient_knowledge_graphs_delete_authenticated"
  ON public.patient_knowledge_graphs FOR DELETE TO authenticated USING (true);

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS kg_completed BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS kg_node_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS kg_relationship_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS kg_version INTEGER NOT NULL DEFAULT 0;

ALTER TABLE public.patient_ai_context
  ADD COLUMN IF NOT EXISTS kg_timestamp TIMESTAMPTZ;

COMMENT ON TABLE public.patient_knowledge_graphs IS
  'Intake Stage 6 — portable patient knowledge graph (JSON; Neo4j-ready shape).';
