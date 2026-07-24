-- =============================================================================
-- Hospital AI — Medical Records, Documents, Audit + Storage
-- Run in Supabase SQL Editor after 004_create_appointments.sql
-- =============================================================================

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'medical_record_type') THEN
    CREATE TYPE public.medical_record_type AS ENUM (
      'Consultation',
      'Prescription',
      'Lab Report',
      'X-Ray',
      'MRI',
      'CT Scan',
      'Ultrasound',
      'Discharge Summary',
      'Vaccination',
      'Other'
    );
  END IF;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'medical_audit_action') THEN
    CREATE TYPE public.medical_audit_action AS ENUM (
      'Created',
      'Updated',
      'Deleted',
      'Uploaded File',
      'Deleted File'
    );
  END IF;
END
$$;

-- ---------------------------------------------------------------------------
-- MEDICAL RECORDS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.medical_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES public.patients (id) ON DELETE RESTRICT,
  appointment_id UUID REFERENCES public.appointments (id) ON DELETE SET NULL,
  doctor_id UUID REFERENCES public.doctors (id) ON DELETE SET NULL,
  record_type public.medical_record_type NOT NULL DEFAULT 'Consultation',
  title TEXT NOT NULL,
  description TEXT,
  diagnosis TEXT,
  treatment TEXT,
  notes TEXT,
  -- Future AI / RAG extension points (unused)
  ai_summary TEXT,
  detected_conditions JSONB,
  risk_score NUMERIC(8, 2),
  recommended_tests JSONB,
  embedding_id TEXT,
  vector_status TEXT,
  ocr_status TEXT,
  created_by UUID REFERENCES public.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT medical_records_title_not_empty CHECK (length(trim(title)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_medical_records_patient ON public.medical_records (patient_id);
CREATE INDEX IF NOT EXISTS idx_medical_records_doctor ON public.medical_records (doctor_id);
CREATE INDEX IF NOT EXISTS idx_medical_records_appointment ON public.medical_records (appointment_id);
CREATE INDEX IF NOT EXISTS idx_medical_records_type ON public.medical_records (record_type);
CREATE INDEX IF NOT EXISTS idx_medical_records_created ON public.medical_records (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_medical_records_title ON public.medical_records (title);

DROP TRIGGER IF EXISTS trg_medical_records_updated_at ON public.medical_records;
CREATE TRIGGER trg_medical_records_updated_at
  BEFORE UPDATE ON public.medical_records
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.medical_records ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "medical_records_select_authenticated" ON public.medical_records;
CREATE POLICY "medical_records_select_authenticated"
  ON public.medical_records FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "medical_records_insert_authenticated" ON public.medical_records;
CREATE POLICY "medical_records_insert_authenticated"
  ON public.medical_records FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "medical_records_update_authenticated" ON public.medical_records;
CREATE POLICY "medical_records_update_authenticated"
  ON public.medical_records FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "medical_records_delete_authenticated" ON public.medical_records;
CREATE POLICY "medical_records_delete_authenticated"
  ON public.medical_records FOR DELETE TO authenticated USING (true);

-- ---------------------------------------------------------------------------
-- MEDICAL DOCUMENTS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.medical_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  medical_record_id UUID NOT NULL REFERENCES public.medical_records (id) ON DELETE CASCADE,
  file_name TEXT NOT NULL,
  file_url TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  file_type TEXT NOT NULL,
  file_size BIGINT NOT NULL CHECK (file_size > 0 AND file_size <= 20971520),
  uploaded_by UUID REFERENCES public.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT medical_documents_file_name_not_empty CHECK (length(trim(file_name)) > 0),
  CONSTRAINT medical_documents_unique_path UNIQUE (storage_path)
);

CREATE INDEX IF NOT EXISTS idx_medical_documents_record ON public.medical_documents (medical_record_id);
CREATE INDEX IF NOT EXISTS idx_medical_documents_uploaded_by ON public.medical_documents (uploaded_by);
CREATE INDEX IF NOT EXISTS idx_medical_documents_created ON public.medical_documents (created_at DESC);

ALTER TABLE public.medical_documents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "medical_documents_select_authenticated" ON public.medical_documents;
CREATE POLICY "medical_documents_select_authenticated"
  ON public.medical_documents FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "medical_documents_insert_authenticated" ON public.medical_documents;
CREATE POLICY "medical_documents_insert_authenticated"
  ON public.medical_documents FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "medical_documents_update_authenticated" ON public.medical_documents;
CREATE POLICY "medical_documents_update_authenticated"
  ON public.medical_documents FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "medical_documents_delete_authenticated" ON public.medical_documents;
CREATE POLICY "medical_documents_delete_authenticated"
  ON public.medical_documents FOR DELETE TO authenticated USING (true);

-- ---------------------------------------------------------------------------
-- AUDIT LOG
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.medical_record_audit (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  record_id UUID REFERENCES public.medical_records (id) ON DELETE SET NULL,
  document_id UUID,
  action public.medical_audit_action NOT NULL,
  performed_by UUID REFERENCES public.users (id) ON DELETE SET NULL,
  details JSONB,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_medical_audit_record ON public.medical_record_audit (record_id);
CREATE INDEX IF NOT EXISTS idx_medical_audit_timestamp ON public.medical_record_audit (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_medical_audit_action ON public.medical_record_audit (action);

ALTER TABLE public.medical_record_audit ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "medical_audit_select_authenticated" ON public.medical_record_audit;
CREATE POLICY "medical_audit_select_authenticated"
  ON public.medical_record_audit FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "medical_audit_insert_authenticated" ON public.medical_record_audit;
CREATE POLICY "medical_audit_insert_authenticated"
  ON public.medical_record_audit FOR INSERT TO authenticated WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- Storage: medical-records (private; access via signed URLs / authenticated)
-- ---------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'medical-records',
  'medical-records',
  false,
  20971520,
  ARRAY[
    'application/pdf',
    'image/png',
    'image/jpeg',
    'image/jpg',
    'image/webp'
  ]::text[]
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

DROP POLICY IF EXISTS "Authenticated users can upload medical records" ON storage.objects;
CREATE POLICY "Authenticated users can upload medical records"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'medical-records');

DROP POLICY IF EXISTS "Authenticated users can update medical records" ON storage.objects;
CREATE POLICY "Authenticated users can update medical records"
  ON storage.objects FOR UPDATE TO authenticated
  USING (bucket_id = 'medical-records')
  WITH CHECK (bucket_id = 'medical-records');

DROP POLICY IF EXISTS "Authenticated users can delete medical records" ON storage.objects;
CREATE POLICY "Authenticated users can delete medical records"
  ON storage.objects FOR DELETE TO authenticated
  USING (bucket_id = 'medical-records');

DROP POLICY IF EXISTS "Authenticated users can read medical records" ON storage.objects;
CREATE POLICY "Authenticated users can read medical records"
  ON storage.objects FOR SELECT TO authenticated
  USING (bucket_id = 'medical-records');

COMMENT ON TABLE public.medical_records IS
  'EMR clinical records linked to patients (and optional appointments/doctors).';
COMMENT ON COLUMN public.medical_records.ai_summary IS 'Reserved for MedicalSummaryService — unused.';
COMMENT ON COLUMN public.medical_records.detected_conditions IS 'Reserved for clinical AI — unused.';
COMMENT ON COLUMN public.medical_records.risk_score IS 'Reserved for risk scoring agents — unused.';
COMMENT ON COLUMN public.medical_records.recommended_tests IS 'Reserved for care-path agents — unused.';
COMMENT ON COLUMN public.medical_records.embedding_id IS 'Reserved for EmbeddingService / RAG — unused.';
COMMENT ON COLUMN public.medical_records.vector_status IS 'Reserved for VectorIndexService — unused.';
COMMENT ON COLUMN public.medical_records.ocr_status IS 'Reserved for OCRService — unused.';
COMMENT ON TABLE public.medical_documents IS
  'Files stored under medical-records/{patient_id}/{appointment_id|general}/…';
COMMENT ON TABLE public.medical_record_audit IS
  'Audit trail for EMR create/update/delete and file operations.';
