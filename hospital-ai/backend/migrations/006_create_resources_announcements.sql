-- =============================================================================
-- Hospital AI — Resources, Announcements, Notifications
-- Run in Supabase SQL Editor after 005_create_medical_records.sql
-- =============================================================================

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'hospital_resource_type') THEN
    CREATE TYPE public.hospital_resource_type AS ENUM (
      'Bed',
      'ICU Bed',
      'Operation Theatre',
      'Ventilator',
      'Ambulance',
      'Wheelchair',
      'Medical Equipment',
      'Laboratory',
      'Pharmacy'
    );
  END IF;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'resource_status') THEN
    CREATE TYPE public.resource_status AS ENUM (
      'Available',
      'In Use',
      'Maintenance',
      'Out of Service'
    );
  END IF;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'announcement_priority') THEN
    CREATE TYPE public.announcement_priority AS ENUM (
      'Low',
      'Normal',
      'High',
      'Emergency'
    );
  END IF;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notification_category') THEN
    CREATE TYPE public.notification_category AS ENUM (
      'Appointments',
      'Resources',
      'Announcements',
      'System'
    );
  END IF;
END
$$;

-- ---------------------------------------------------------------------------
-- HOSPITAL RESOURCES
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.hospital_resources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  resource_name TEXT NOT NULL,
  resource_type public.hospital_resource_type NOT NULL,
  quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 0),
  available_quantity INTEGER NOT NULL DEFAULT 0 CHECK (available_quantity >= 0),
  status public.resource_status NOT NULL DEFAULT 'Available',
  location TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT hospital_resources_name_not_empty CHECK (length(trim(resource_name)) > 0),
  CONSTRAINT hospital_resources_available_lte_quantity CHECK (available_quantity <= quantity)
);

CREATE INDEX IF NOT EXISTS idx_hospital_resources_type ON public.hospital_resources (resource_type);
CREATE INDEX IF NOT EXISTS idx_hospital_resources_status ON public.hospital_resources (status);
CREATE INDEX IF NOT EXISTS idx_hospital_resources_name ON public.hospital_resources (resource_name);

DROP TRIGGER IF EXISTS trg_hospital_resources_updated_at ON public.hospital_resources;
CREATE TRIGGER trg_hospital_resources_updated_at
  BEFORE UPDATE ON public.hospital_resources
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.hospital_resources ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "hospital_resources_select_authenticated" ON public.hospital_resources;
CREATE POLICY "hospital_resources_select_authenticated"
  ON public.hospital_resources FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "hospital_resources_insert_authenticated" ON public.hospital_resources;
CREATE POLICY "hospital_resources_insert_authenticated"
  ON public.hospital_resources FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "hospital_resources_update_authenticated" ON public.hospital_resources;
CREATE POLICY "hospital_resources_update_authenticated"
  ON public.hospital_resources FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "hospital_resources_delete_authenticated" ON public.hospital_resources;
CREATE POLICY "hospital_resources_delete_authenticated"
  ON public.hospital_resources FOR DELETE TO authenticated USING (true);

-- ---------------------------------------------------------------------------
-- HOSPITAL ANNOUNCEMENTS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.hospital_announcements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  priority public.announcement_priority NOT NULL DEFAULT 'Normal',
  category TEXT NOT NULL DEFAULT 'Hospital Notice',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_by UUID REFERENCES public.users (id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT hospital_announcements_title_not_empty CHECK (length(trim(title)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_hospital_announcements_priority ON public.hospital_announcements (priority);
CREATE INDEX IF NOT EXISTS idx_hospital_announcements_created ON public.hospital_announcements (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_hospital_announcements_active ON public.hospital_announcements (is_active);

DROP TRIGGER IF EXISTS trg_hospital_announcements_updated_at ON public.hospital_announcements;
CREATE TRIGGER trg_hospital_announcements_updated_at
  BEFORE UPDATE ON public.hospital_announcements
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.hospital_announcements ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "hospital_announcements_select_authenticated" ON public.hospital_announcements;
CREATE POLICY "hospital_announcements_select_authenticated"
  ON public.hospital_announcements FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "hospital_announcements_insert_authenticated" ON public.hospital_announcements;
CREATE POLICY "hospital_announcements_insert_authenticated"
  ON public.hospital_announcements FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "hospital_announcements_update_authenticated" ON public.hospital_announcements;
CREATE POLICY "hospital_announcements_update_authenticated"
  ON public.hospital_announcements FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "hospital_announcements_delete_authenticated" ON public.hospital_announcements;
CREATE POLICY "hospital_announcements_delete_authenticated"
  ON public.hospital_announcements FOR DELETE TO authenticated USING (true);

-- ---------------------------------------------------------------------------
-- NOTIFICATIONS (in-app notification center)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.hospital_notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.users (id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  category public.notification_category NOT NULL DEFAULT 'System',
  priority public.announcement_priority NOT NULL DEFAULT 'Normal',
  link TEXT,
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT hospital_notifications_title_not_empty CHECK (length(trim(title)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_hospital_notifications_user ON public.hospital_notifications (user_id, is_read, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_hospital_notifications_created ON public.hospital_notifications (created_at DESC);

ALTER TABLE public.hospital_notifications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "hospital_notifications_select_authenticated" ON public.hospital_notifications;
CREATE POLICY "hospital_notifications_select_authenticated"
  ON public.hospital_notifications FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "hospital_notifications_insert_authenticated" ON public.hospital_notifications;
CREATE POLICY "hospital_notifications_insert_authenticated"
  ON public.hospital_notifications FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "hospital_notifications_update_authenticated" ON public.hospital_notifications;
CREATE POLICY "hospital_notifications_update_authenticated"
  ON public.hospital_notifications FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "hospital_notifications_delete_authenticated" ON public.hospital_notifications;
CREATE POLICY "hospital_notifications_delete_authenticated"
  ON public.hospital_notifications FOR DELETE TO authenticated USING (true);

COMMENT ON TABLE public.hospital_resources IS 'Hospital beds, ICU, OT, equipment inventory.';
COMMENT ON TABLE public.hospital_announcements IS 'Hospital notices, maintenance, emergency announcements.';
COMMENT ON TABLE public.hospital_notifications IS 'In-app notification center items.';
