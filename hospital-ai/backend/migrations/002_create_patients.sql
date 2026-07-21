-- =============================================================================
-- Hospital AI — Patients table migration
-- Run in Supabase SQL Editor after 001_create_users.sql
-- =============================================================================

CREATE SEQUENCE IF NOT EXISTS public.patients_number_seq START WITH 1001 INCREMENT BY 1;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'patient_gender') THEN
    CREATE TYPE public.patient_gender AS ENUM ('Male', 'Female', 'Other');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'blood_group') THEN
    CREATE TYPE public.blood_group AS ENUM (
      'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'
    );
  END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.patients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_number TEXT NOT NULL DEFAULT '' UNIQUE,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  date_of_birth DATE NOT NULL,
  gender public.patient_gender NOT NULL,
  blood_group public.blood_group,
  phone TEXT NOT NULL,
  email TEXT,
  address TEXT,
  city TEXT,
  state TEXT,
  country TEXT DEFAULT 'India',
  emergency_contact_name TEXT,
  emergency_contact_phone TEXT,
  allergies TEXT,
  medical_history TEXT,
  current_medications TEXT,
  insurance_provider TEXT,
  insurance_number TEXT,
  -- Future AI agent extension points (unused for now)
  ai_context JSONB,
  latest_diagnosis TEXT,
  latest_report JSONB,
  prediction_history JSONB,
  created_by UUID REFERENCES public.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT patients_phone_not_empty CHECK (length(trim(phone)) > 0),
  CONSTRAINT patients_first_name_not_empty CHECK (length(trim(first_name)) > 0),
  CONSTRAINT patients_last_name_not_empty CHECK (length(trim(last_name)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_patients_patient_number ON public.patients (patient_number);
CREATE INDEX IF NOT EXISTS idx_patients_phone ON public.patients (phone);
CREATE INDEX IF NOT EXISTS idx_patients_name ON public.patients (last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_patients_gender ON public.patients (gender);
CREATE INDEX IF NOT EXISTS idx_patients_blood_group ON public.patients (blood_group);
CREATE INDEX IF NOT EXISTS idx_patients_created_at ON public.patients (created_at DESC);

-- Auto patient number: PAT-000001
CREATE OR REPLACE FUNCTION public.set_patient_number()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.patient_number IS NULL OR NEW.patient_number = '' THEN
    NEW.patient_number := 'PAT-' || LPAD(nextval('public.patients_number_seq')::TEXT, 6, '0');
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_patients_number ON public.patients;
CREATE TRIGGER trg_patients_number
  BEFORE INSERT ON public.patients
  FOR EACH ROW
  EXECUTE FUNCTION public.set_patient_number();

DROP TRIGGER IF EXISTS trg_patients_updated_at ON public.patients;
CREATE TRIGGER trg_patients_updated_at
  BEFORE UPDATE ON public.patients
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Row Level Security — authenticated hospital staff can manage patients
-- ---------------------------------------------------------------------------
ALTER TABLE public.patients ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can view patients" ON public.patients;
CREATE POLICY "Authenticated users can view patients"
  ON public.patients
  FOR SELECT
  TO authenticated
  USING (true);

DROP POLICY IF EXISTS "Authenticated users can insert patients" ON public.patients;
CREATE POLICY "Authenticated users can insert patients"
  ON public.patients
  FOR INSERT
  TO authenticated
  WITH CHECK (true);

DROP POLICY IF EXISTS "Authenticated users can update patients" ON public.patients;
CREATE POLICY "Authenticated users can update patients"
  ON public.patients
  FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

DROP POLICY IF EXISTS "Authenticated users can delete patients" ON public.patients;
CREATE POLICY "Authenticated users can delete patients"
  ON public.patients
  FOR DELETE
  TO authenticated
  USING (true);

COMMENT ON TABLE public.patients IS 'Hospital patient registry for clinical and AI agent workflows';
COMMENT ON COLUMN public.patients.ai_context IS 'Reserved for future AI agent context payloads';
COMMENT ON COLUMN public.patients.latest_diagnosis IS 'Reserved for future AI diagnosis summaries';
COMMENT ON COLUMN public.patients.latest_report IS 'Reserved for future AI report payloads';
COMMENT ON COLUMN public.patients.prediction_history IS 'Reserved for future AI prediction history';
