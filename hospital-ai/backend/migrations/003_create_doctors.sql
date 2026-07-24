-- =============================================================================
-- Hospital AI — Doctors, Departments, Availability + Storage
-- Run in Supabase SQL Editor after 002_create_patients.sql
-- =============================================================================

CREATE SEQUENCE IF NOT EXISTS public.doctors_number_seq START WITH 1001 INCREMENT BY 1;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'availability_status') THEN
    CREATE TYPE public.availability_status AS ENUM ('Available', 'Busy', 'On Leave');
  END IF;
END
$$;

-- ---------------------------------------------------------------------------
-- DEPARTMENTS (head_doctor_id FK added after doctors exists)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.departments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  floor_number INTEGER,
  head_doctor_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT departments_name_not_empty CHECK (length(trim(name)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_departments_name ON public.departments (name);

DROP TRIGGER IF EXISTS trg_departments_updated_at ON public.departments;
CREATE TRIGGER trg_departments_updated_at
  BEFORE UPDATE ON public.departments
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

-- ---------------------------------------------------------------------------
-- DOCTORS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.doctors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  doctor_number TEXT NOT NULL DEFAULT '' UNIQUE,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  phone TEXT NOT NULL,
  gender public.patient_gender NOT NULL,
  date_of_birth DATE,
  department_id UUID REFERENCES public.departments (id) ON DELETE SET NULL,
  specialization TEXT NOT NULL,
  qualification TEXT,
  experience_years INTEGER NOT NULL DEFAULT 0 CHECK (experience_years >= 0),
  license_number TEXT UNIQUE,
  consultation_fee NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (consultation_fee >= 0),
  availability_status public.availability_status NOT NULL DEFAULT 'Available',
  profile_photo_url TEXT,
  bio TEXT,
  -- Future AI agent extension points
  ai_summary TEXT,
  performance_metrics JSONB,
  predicted_workload JSONB,
  recommended_schedule JSONB,
  created_by UUID REFERENCES public.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT doctors_first_name_not_empty CHECK (length(trim(first_name)) > 0),
  CONSTRAINT doctors_last_name_not_empty CHECK (length(trim(last_name)) > 0),
  CONSTRAINT doctors_phone_not_empty CHECK (length(trim(phone)) > 0),
  CONSTRAINT doctors_specialization_not_empty CHECK (length(trim(specialization)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_doctors_doctor_number ON public.doctors (doctor_number);
CREATE INDEX IF NOT EXISTS idx_doctors_name ON public.doctors (last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_doctors_specialization ON public.doctors (specialization);
CREATE INDEX IF NOT EXISTS idx_doctors_department ON public.doctors (department_id);
CREATE INDEX IF NOT EXISTS idx_doctors_availability ON public.doctors (availability_status);
CREATE INDEX IF NOT EXISTS idx_doctors_experience ON public.doctors (experience_years);

CREATE OR REPLACE FUNCTION public.set_doctor_number()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.doctor_number IS NULL OR NEW.doctor_number = '' THEN
    NEW.doctor_number := 'DOC-' || LPAD(nextval('public.doctors_number_seq')::TEXT, 6, '0');
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_doctors_number ON public.doctors;
CREATE TRIGGER trg_doctors_number
  BEFORE INSERT ON public.doctors
  FOR EACH ROW
  EXECUTE FUNCTION public.set_doctor_number();

DROP TRIGGER IF EXISTS trg_doctors_updated_at ON public.doctors;
CREATE TRIGGER trg_doctors_updated_at
  BEFORE UPDATE ON public.doctors
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

-- Wire head_doctor FK now that doctors exists
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'departments_head_doctor_id_fkey'
  ) THEN
    ALTER TABLE public.departments
      ADD CONSTRAINT departments_head_doctor_id_fkey
      FOREIGN KEY (head_doctor_id) REFERENCES public.doctors (id) ON DELETE SET NULL;
  END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_departments_head_doctor ON public.departments (head_doctor_id);

-- ---------------------------------------------------------------------------
-- DOCTOR AVAILABILITY (for future Scheduling Agent)
-- day_of_week: 0=Monday … 6=Sunday
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.doctor_availability (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  doctor_id UUID NOT NULL REFERENCES public.doctors (id) ON DELETE CASCADE,
  day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  slot_duration INTEGER NOT NULL DEFAULT 30 CHECK (slot_duration > 0),
  is_available BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT availability_time_order CHECK (end_time > start_time),
  CONSTRAINT availability_unique_slot UNIQUE (doctor_id, day_of_week, start_time, end_time)
);

CREATE INDEX IF NOT EXISTS idx_doctor_availability_doctor
  ON public.doctor_availability (doctor_id);
CREATE INDEX IF NOT EXISTS idx_doctor_availability_day
  ON public.doctor_availability (day_of_week);

DROP TRIGGER IF EXISTS trg_doctor_availability_updated_at ON public.doctor_availability;
CREATE TRIGGER trg_doctor_availability_updated_at
  BEFORE UPDATE ON public.doctor_availability
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

-- ---------------------------------------------------------------------------
-- RLS
-- ---------------------------------------------------------------------------
ALTER TABLE public.departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.doctors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.doctor_availability ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can view departments" ON public.departments;
CREATE POLICY "Authenticated users can view departments"
  ON public.departments FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "Authenticated users can insert departments" ON public.departments;
CREATE POLICY "Authenticated users can insert departments"
  ON public.departments FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "Authenticated users can update departments" ON public.departments;
CREATE POLICY "Authenticated users can update departments"
  ON public.departments FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Authenticated users can delete departments" ON public.departments;
CREATE POLICY "Authenticated users can delete departments"
  ON public.departments FOR DELETE TO authenticated USING (true);

DROP POLICY IF EXISTS "Authenticated users can view doctors" ON public.doctors;
CREATE POLICY "Authenticated users can view doctors"
  ON public.doctors FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "Authenticated users can insert doctors" ON public.doctors;
CREATE POLICY "Authenticated users can insert doctors"
  ON public.doctors FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "Authenticated users can update doctors" ON public.doctors;
CREATE POLICY "Authenticated users can update doctors"
  ON public.doctors FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Authenticated users can delete doctors" ON public.doctors;
CREATE POLICY "Authenticated users can delete doctors"
  ON public.doctors FOR DELETE TO authenticated USING (true);

DROP POLICY IF EXISTS "Authenticated users can view availability" ON public.doctor_availability;
CREATE POLICY "Authenticated users can view availability"
  ON public.doctor_availability FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "Authenticated users can insert availability" ON public.doctor_availability;
CREATE POLICY "Authenticated users can insert availability"
  ON public.doctor_availability FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "Authenticated users can update availability" ON public.doctor_availability;
CREATE POLICY "Authenticated users can update availability"
  ON public.doctor_availability FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Authenticated users can delete availability" ON public.doctor_availability;
CREATE POLICY "Authenticated users can delete availability"
  ON public.doctor_availability FOR DELETE TO authenticated USING (true);

-- ---------------------------------------------------------------------------
-- Storage: doctor profile photos
-- ---------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public)
VALUES ('doctor-photos', 'doctor-photos', true)
ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS "Authenticated users can upload doctor photos" ON storage.objects;
CREATE POLICY "Authenticated users can upload doctor photos"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'doctor-photos');

DROP POLICY IF EXISTS "Authenticated users can update doctor photos" ON storage.objects;
CREATE POLICY "Authenticated users can update doctor photos"
  ON storage.objects FOR UPDATE TO authenticated
  USING (bucket_id = 'doctor-photos')
  WITH CHECK (bucket_id = 'doctor-photos');

DROP POLICY IF EXISTS "Authenticated users can delete doctor photos" ON storage.objects;
CREATE POLICY "Authenticated users can delete doctor photos"
  ON storage.objects FOR DELETE TO authenticated
  USING (bucket_id = 'doctor-photos');

DROP POLICY IF EXISTS "Public can view doctor photos" ON storage.objects;
CREATE POLICY "Public can view doctor photos"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'doctor-photos');

COMMENT ON TABLE public.doctors IS 'Hospital doctors registry';
COMMENT ON COLUMN public.doctors.ai_summary IS 'Reserved for future AI summary';
COMMENT ON COLUMN public.doctors.performance_metrics IS 'Reserved for future AI metrics';
COMMENT ON COLUMN public.doctors.predicted_workload IS 'Reserved for future workload predictions';
COMMENT ON COLUMN public.doctors.recommended_schedule IS 'Reserved for future schedule recommendations';
COMMENT ON TABLE public.doctor_availability IS 'Weekly slots for future Scheduling Agent';
