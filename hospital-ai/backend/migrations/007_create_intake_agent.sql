-- =============================================================================
-- Hospital AI — Intake Agent: Patient Registration (Stage 1 only)
-- Run in Supabase SQL Editor after 006_create_resources_announcements.sql
--
-- This script DROPS any older Intake tables/enums (OCR/KG schema) so the
-- Patient Registration schema can be created cleanly.
-- =============================================================================

-- 1) Remove previous Intake objects (safe if they never existed)
DROP TABLE IF EXISTS public.patient_ai_context CASCADE;
DROP TABLE IF EXISTS public.document_processing_jobs CASCADE;
DROP TABLE IF EXISTS public.patient_knowledge_graphs CASCADE;

DROP TYPE IF EXISTS public.document_job_status CASCADE;
DROP TYPE IF EXISTS public.patient_risk_level CASCADE;
DROP TYPE IF EXISTS public.patient_ai_context_status CASCADE;

-- 2) Enums for Patient Registration
CREATE TYPE public.document_job_status AS ENUM (
  'Pending',
  'Processing',
  'Completed',
  'Failed'
);

CREATE TYPE public.patient_ai_context_status AS ENUM (
  'Initialized',
  'Pending',
  'Ready',
  'Failed'
);

-- ---------------------------------------------------------------------------
-- DOCUMENT PROCESSING JOBS
-- Created at Patient Registration. Later stages update status/current_stage.
-- ---------------------------------------------------------------------------
CREATE TABLE public.document_processing_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  appointment_id UUID NOT NULL REFERENCES public.appointments (id) ON DELETE RESTRICT,
  doctor_id UUID NOT NULL REFERENCES public.doctors (id) ON DELETE RESTRICT,
  document_name TEXT NOT NULL,
  document_type TEXT NOT NULL,
  file_url TEXT NOT NULL,
  storage_path TEXT,
  file_size INTEGER CHECK (file_size IS NULL OR file_size >= 0),
  status public.document_job_status NOT NULL DEFAULT 'Pending',
  current_stage TEXT NOT NULL DEFAULT 'Patient Registration',
  processing_started_at TIMESTAMPTZ,
  processing_completed_at TIMESTAMPTZ,
  error_message TEXT,
  created_by UUID REFERENCES public.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_doc_jobs_patient ON public.document_processing_jobs (patient_id);
CREATE INDEX idx_doc_jobs_appointment ON public.document_processing_jobs (appointment_id);
CREATE INDEX idx_doc_jobs_doctor ON public.document_processing_jobs (doctor_id);
CREATE INDEX idx_doc_jobs_status ON public.document_processing_jobs (status);
CREATE INDEX idx_doc_jobs_created ON public.document_processing_jobs (created_at DESC);
CREATE INDEX idx_doc_jobs_dup
  ON public.document_processing_jobs (patient_id, document_name, file_size);

DROP TRIGGER IF EXISTS trg_document_processing_jobs_updated_at ON public.document_processing_jobs;
CREATE TRIGGER trg_document_processing_jobs_updated_at
  BEFORE UPDATE ON public.document_processing_jobs
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.document_processing_jobs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "document_jobs_select_authenticated" ON public.document_processing_jobs;
CREATE POLICY "document_jobs_select_authenticated"
  ON public.document_processing_jobs FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "document_jobs_insert_authenticated" ON public.document_processing_jobs;
CREATE POLICY "document_jobs_insert_authenticated"
  ON public.document_processing_jobs FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "document_jobs_update_authenticated" ON public.document_processing_jobs;
CREATE POLICY "document_jobs_update_authenticated"
  ON public.document_processing_jobs FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "document_jobs_delete_authenticated" ON public.document_processing_jobs;
CREATE POLICY "document_jobs_delete_authenticated"
  ON public.document_processing_jobs FOR DELETE TO authenticated USING (true);

-- ---------------------------------------------------------------------------
-- PATIENT AI CONTEXT (initialized at registration; filled by later stages)
-- ---------------------------------------------------------------------------
CREATE TABLE public.patient_ai_context (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL UNIQUE REFERENCES public.patients (id) ON DELETE CASCADE,
  processing_job_id UUID REFERENCES public.document_processing_jobs (id) ON DELETE SET NULL,
  status public.patient_ai_context_status NOT NULL DEFAULT 'Initialized',
  current_summary TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_patient_ai_context_patient ON public.patient_ai_context (patient_id);
CREATE INDEX idx_patient_ai_context_job ON public.patient_ai_context (processing_job_id);
CREATE INDEX idx_patient_ai_context_status ON public.patient_ai_context (status);

DROP TRIGGER IF EXISTS trg_patient_ai_context_updated_at ON public.patient_ai_context;
CREATE TRIGGER trg_patient_ai_context_updated_at
  BEFORE UPDATE ON public.patient_ai_context
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.patient_ai_context ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "patient_ai_context_select_authenticated" ON public.patient_ai_context;
CREATE POLICY "patient_ai_context_select_authenticated"
  ON public.patient_ai_context FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "patient_ai_context_insert_authenticated" ON public.patient_ai_context;
CREATE POLICY "patient_ai_context_insert_authenticated"
  ON public.patient_ai_context FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "patient_ai_context_update_authenticated" ON public.patient_ai_context;
CREATE POLICY "patient_ai_context_update_authenticated"
  ON public.patient_ai_context FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "patient_ai_context_delete_authenticated" ON public.patient_ai_context;
CREATE POLICY "patient_ai_context_delete_authenticated"
  ON public.patient_ai_context FOR DELETE TO authenticated USING (true);

COMMENT ON TABLE public.document_processing_jobs IS
  'Intake pipeline jobs. Patient Registration creates the row; later stages advance current_stage.';
COMMENT ON TABLE public.patient_ai_context IS
  'Patient AI context shell initialized at registration. Populated by subsequent Intake stages.';
COMMENT ON COLUMN public.document_processing_jobs.current_stage IS
  'Completed stage name after each step (e.g. Patient Registration).';
