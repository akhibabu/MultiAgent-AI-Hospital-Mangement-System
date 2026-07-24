-- =============================================================================
-- Hospital AI — Appointments
-- Run in Supabase SQL Editor after 003_create_doctors.sql
-- =============================================================================

CREATE SEQUENCE IF NOT EXISTS public.appointments_number_seq START WITH 1001 INCREMENT BY 1;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appointment_status') THEN
    CREATE TYPE public.appointment_status AS ENUM (
      'Scheduled',
      'Completed',
      'Cancelled',
      'No Show',
      'Rescheduled'
    );
  END IF;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'visit_type') THEN
    CREATE TYPE public.visit_type AS ENUM (
      'Consultation',
      'Follow Up',
      'Emergency',
      'Telemedicine'
    );
  END IF;
END
$$;

-- Optional doctor AI extension used by future scheduling agents
ALTER TABLE public.doctors
  ADD COLUMN IF NOT EXISTS schedule_score JSONB;

COMMENT ON COLUMN public.doctors.schedule_score IS
  'Reserved for future Scheduling Agent — unused.';

CREATE TABLE IF NOT EXISTS public.appointments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  appointment_number TEXT NOT NULL DEFAULT '' UNIQUE,
  patient_id UUID NOT NULL REFERENCES public.patients (id) ON DELETE RESTRICT,
  doctor_id UUID NOT NULL REFERENCES public.doctors (id) ON DELETE RESTRICT,
  department_id UUID REFERENCES public.departments (id) ON DELETE SET NULL,
  appointment_date DATE NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  status public.appointment_status NOT NULL DEFAULT 'Scheduled',
  visit_type public.visit_type NOT NULL DEFAULT 'Consultation',
  reason_for_visit TEXT,
  notes TEXT,
  -- Future AI agent extension points
  predicted_wait_time INTEGER,
  priority_score NUMERIC(8, 2),
  recommended_slot JSONB,
  ai_notes TEXT,
  created_by UUID REFERENCES public.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT appointments_end_after_start CHECK (end_time > start_time),
  CONSTRAINT appointments_min_duration CHECK (
    (EXTRACT(EPOCH FROM (end_time - start_time)) / 60) >= 5
  ),
  CONSTRAINT appointments_max_duration CHECK (
    (EXTRACT(EPOCH FROM (end_time - start_time)) / 60) <= 480
  )
);

CREATE INDEX IF NOT EXISTS idx_appointments_number ON public.appointments (appointment_number);
CREATE INDEX IF NOT EXISTS idx_appointments_patient ON public.appointments (patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_doctor ON public.appointments (doctor_id);
CREATE INDEX IF NOT EXISTS idx_appointments_department ON public.appointments (department_id);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON public.appointments (status);
CREATE INDEX IF NOT EXISTS idx_appointments_visit_type ON public.appointments (visit_type);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON public.appointments (appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointments_doctor_date ON public.appointments (doctor_id, appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointments_patient_date ON public.appointments (patient_id, appointment_date DESC);

CREATE OR REPLACE FUNCTION public.set_appointment_number()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.appointment_number IS NULL OR NEW.appointment_number = '' THEN
    NEW.appointment_number :=
      'APT-' || LPAD(nextval('public.appointments_number_seq')::TEXT, 6, '0');
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_appointments_number ON public.appointments;
CREATE TRIGGER trg_appointments_number
  BEFORE INSERT ON public.appointments
  FOR EACH ROW
  EXECUTE FUNCTION public.set_appointment_number();

DROP TRIGGER IF EXISTS trg_appointments_updated_at ON public.appointments;
CREATE TRIGGER trg_appointments_updated_at
  BEFORE UPDATE ON public.appointments
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.appointments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "appointments_select_authenticated" ON public.appointments;
CREATE POLICY "appointments_select_authenticated"
  ON public.appointments FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "appointments_insert_authenticated" ON public.appointments;
CREATE POLICY "appointments_insert_authenticated"
  ON public.appointments FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "appointments_update_authenticated" ON public.appointments;
CREATE POLICY "appointments_update_authenticated"
  ON public.appointments FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "appointments_delete_authenticated" ON public.appointments;
CREATE POLICY "appointments_delete_authenticated"
  ON public.appointments FOR DELETE TO authenticated USING (true);

COMMENT ON TABLE public.appointments IS
  'Hospital appointments — scheduling, calendar, and future AI agent inputs.';
COMMENT ON COLUMN public.appointments.predicted_wait_time IS
  'Reserved for Scheduling Agent — minutes; unused.';
COMMENT ON COLUMN public.appointments.priority_score IS
  'Reserved for Emergency / triage agents — unused.';
COMMENT ON COLUMN public.appointments.recommended_slot IS
  'Reserved for Scheduling Agent — unused.';
COMMENT ON COLUMN public.appointments.ai_notes IS
  'Reserved for AI notes / digital twin — unused.';
