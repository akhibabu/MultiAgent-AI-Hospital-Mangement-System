-- =============================================================================
-- Hospital AI — Prescription Agent + Medical Report Agent
-- Run in Supabase SQL Editor after 015_create_diagnosis_research_agents.sql
--
-- Prescription Agent consumes Diagnosis Agent + Research Agent + Intake
-- Agent output. Medical Report Agent consumes ALL previous agents' output.
-- Neither agent replaces a physician. The Prescription Agent NEVER produces
-- a final prescription — only physician-review recommendations.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- PRESCRIPTION RESULTS
-- Append-only run history. One row per Prescription Agent execution.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.prescription_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  diagnosis_result_id UUID REFERENCES public.diagnosis_results (id) ON DELETE SET NULL,
  research_result_id UUID REFERENCES public.research_results (id) ON DELETE SET NULL,
  target_conditions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  medication_recommendations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  drug_interactions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  allergy_checks_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  dosage_recommendations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  treatment_plan_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  validation_summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  summary TEXT,
  engine TEXT NOT NULL DEFAULT 'rule_based',
  status TEXT NOT NULL DEFAULT 'Completed',
  error_message TEXT,
  processing_time_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prescription_results_patient
  ON public.prescription_results (patient_id);
CREATE INDEX IF NOT EXISTS idx_prescription_results_created
  ON public.prescription_results (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_prescription_results_diagnosis
  ON public.prescription_results (diagnosis_result_id);

DROP TRIGGER IF EXISTS trg_prescription_results_updated_at ON public.prescription_results;
CREATE TRIGGER trg_prescription_results_updated_at
  BEFORE UPDATE ON public.prescription_results
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.prescription_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "prescription_results_select_authenticated" ON public.prescription_results;
CREATE POLICY "prescription_results_select_authenticated"
  ON public.prescription_results FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "prescription_results_insert_authenticated" ON public.prescription_results;
CREATE POLICY "prescription_results_insert_authenticated"
  ON public.prescription_results FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "prescription_results_update_authenticated" ON public.prescription_results;
CREATE POLICY "prescription_results_update_authenticated"
  ON public.prescription_results FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "prescription_results_delete_authenticated" ON public.prescription_results;
CREATE POLICY "prescription_results_delete_authenticated"
  ON public.prescription_results FOR DELETE TO authenticated USING (true);

-- ---------------------------------------------------------------------------
-- MEDICATION RECOMMENDATIONS
-- One row per medication recommended within a Prescription Agent run.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.medication_recommendations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prescription_result_id UUID NOT NULL REFERENCES public.prescription_results (id) ON DELETE CASCADE,
  condition TEXT NOT NULL,
  medication_name TEXT NOT NULL,
  drug_class TEXT,
  purpose TEXT,
  evidence_source TEXT,
  clinical_guideline TEXT,
  confidence NUMERIC(5, 4) NOT NULL DEFAULT 0,
  alternative_drugs_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  expected_outcome TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_medication_recommendations_prescription
  ON public.medication_recommendations (prescription_result_id);
CREATE INDEX IF NOT EXISTS idx_medication_recommendations_condition
  ON public.medication_recommendations (condition);

ALTER TABLE public.medication_recommendations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "medication_recommendations_select_authenticated" ON public.medication_recommendations;
CREATE POLICY "medication_recommendations_select_authenticated"
  ON public.medication_recommendations FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "medication_recommendations_insert_authenticated" ON public.medication_recommendations;
CREATE POLICY "medication_recommendations_insert_authenticated"
  ON public.medication_recommendations FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "medication_recommendations_update_authenticated" ON public.medication_recommendations;
CREATE POLICY "medication_recommendations_update_authenticated"
  ON public.medication_recommendations FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "medication_recommendations_delete_authenticated" ON public.medication_recommendations;
CREATE POLICY "medication_recommendations_delete_authenticated"
  ON public.medication_recommendations FOR DELETE TO authenticated USING (true);

-- ---------------------------------------------------------------------------
-- INTERACTION REPORTS
-- One row per detected drug interaction within a Prescription Agent run.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.interaction_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prescription_result_id UUID NOT NULL REFERENCES public.prescription_results (id) ON DELETE CASCADE,
  drug_a TEXT NOT NULL,
  drug_b TEXT NOT NULL,
  interaction_level TEXT NOT NULL DEFAULT 'Minor' CHECK (
    interaction_level IN ('Minor', 'Moderate', 'Major', 'Critical')
  ),
  explanation TEXT,
  recommendation TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interaction_reports_prescription
  ON public.interaction_reports (prescription_result_id);
CREATE INDEX IF NOT EXISTS idx_interaction_reports_level
  ON public.interaction_reports (interaction_level);

ALTER TABLE public.interaction_reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "interaction_reports_select_authenticated" ON public.interaction_reports;
CREATE POLICY "interaction_reports_select_authenticated"
  ON public.interaction_reports FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "interaction_reports_insert_authenticated" ON public.interaction_reports;
CREATE POLICY "interaction_reports_insert_authenticated"
  ON public.interaction_reports FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "interaction_reports_update_authenticated" ON public.interaction_reports;
CREATE POLICY "interaction_reports_update_authenticated"
  ON public.interaction_reports FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "interaction_reports_delete_authenticated" ON public.interaction_reports;
CREATE POLICY "interaction_reports_delete_authenticated"
  ON public.interaction_reports FOR DELETE TO authenticated USING (true);

-- ---------------------------------------------------------------------------
-- VALIDATION REPORTS
-- One row per Prescription Agent run — final safety validation (1:1 with
-- prescription_results, kept as its own audit-friendly table).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.validation_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prescription_result_id UUID NOT NULL UNIQUE
    REFERENCES public.prescription_results (id) ON DELETE CASCADE,
  confidence_score NUMERIC(5, 4) NOT NULL DEFAULT 0,
  approval_status TEXT NOT NULL DEFAULT 'Requires Physician Review' CHECK (
    approval_status IN ('Approved', 'Requires Physician Review', 'Rejected')
  ),
  duplicate_drugs_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  contraindications_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  max_dose_exceeded_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  allergy_conflicts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  drug_warnings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  notes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_validation_reports_prescription
  ON public.validation_reports (prescription_result_id);
CREATE INDEX IF NOT EXISTS idx_validation_reports_status
  ON public.validation_reports (approval_status);

ALTER TABLE public.validation_reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "validation_reports_select_authenticated" ON public.validation_reports;
CREATE POLICY "validation_reports_select_authenticated"
  ON public.validation_reports FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "validation_reports_insert_authenticated" ON public.validation_reports;
CREATE POLICY "validation_reports_insert_authenticated"
  ON public.validation_reports FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "validation_reports_update_authenticated" ON public.validation_reports;
CREATE POLICY "validation_reports_update_authenticated"
  ON public.validation_reports FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "validation_reports_delete_authenticated" ON public.validation_reports;
CREATE POLICY "validation_reports_delete_authenticated"
  ON public.validation_reports FOR DELETE TO authenticated USING (true);

-- ---------------------------------------------------------------------------
-- GENERATED MEDICAL REPORTS
-- Append-only, versioned run history. One row per Medical Report Agent
-- execution (version increments per patient).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.generated_medical_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  diagnosis_result_id UUID REFERENCES public.diagnosis_results (id) ON DELETE SET NULL,
  research_result_id UUID REFERENCES public.research_results (id) ON DELETE SET NULL,
  prescription_result_id UUID REFERENCES public.prescription_results (id) ON DELETE SET NULL,
  clinical_summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  doctor_notes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  discharge_summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  referral_letter_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  insurance_documentation_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  patient_report_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  summary TEXT,
  engine TEXT NOT NULL DEFAULT 'template_based',
  version INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'Completed',
  error_message TEXT,
  processing_time_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_generated_medical_reports_patient
  ON public.generated_medical_reports (patient_id);
CREATE INDEX IF NOT EXISTS idx_generated_medical_reports_created
  ON public.generated_medical_reports (created_at DESC);

DROP TRIGGER IF EXISTS trg_generated_medical_reports_updated_at ON public.generated_medical_reports;
CREATE TRIGGER trg_generated_medical_reports_updated_at
  BEFORE UPDATE ON public.generated_medical_reports
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.generated_medical_reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "generated_medical_reports_select_authenticated" ON public.generated_medical_reports;
CREATE POLICY "generated_medical_reports_select_authenticated"
  ON public.generated_medical_reports FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "generated_medical_reports_insert_authenticated" ON public.generated_medical_reports;
CREATE POLICY "generated_medical_reports_insert_authenticated"
  ON public.generated_medical_reports FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "generated_medical_reports_update_authenticated" ON public.generated_medical_reports;
CREATE POLICY "generated_medical_reports_update_authenticated"
  ON public.generated_medical_reports FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "generated_medical_reports_delete_authenticated" ON public.generated_medical_reports;
CREATE POLICY "generated_medical_reports_delete_authenticated"
  ON public.generated_medical_reports FOR DELETE TO authenticated USING (true);

-- ---------------------------------------------------------------------------
-- REFERRAL LETTERS
-- One row per referral letter generated within a Medical Report Agent run.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.referral_letters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  generated_report_id UUID NOT NULL REFERENCES public.generated_medical_reports (id) ON DELETE CASCADE,
  patient_id UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  receiving_specialist TEXT,
  reason TEXT,
  history_summary TEXT,
  important_findings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  investigations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  requested_evaluation TEXT,
  letter_body TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_referral_letters_report
  ON public.referral_letters (generated_report_id);
CREATE INDEX IF NOT EXISTS idx_referral_letters_patient
  ON public.referral_letters (patient_id);

ALTER TABLE public.referral_letters ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "referral_letters_select_authenticated" ON public.referral_letters;
CREATE POLICY "referral_letters_select_authenticated"
  ON public.referral_letters FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "referral_letters_insert_authenticated" ON public.referral_letters;
CREATE POLICY "referral_letters_insert_authenticated"
  ON public.referral_letters FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "referral_letters_update_authenticated" ON public.referral_letters;
CREATE POLICY "referral_letters_update_authenticated"
  ON public.referral_letters FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "referral_letters_delete_authenticated" ON public.referral_letters;
CREATE POLICY "referral_letters_delete_authenticated"
  ON public.referral_letters FOR DELETE TO authenticated USING (true);

-- ---------------------------------------------------------------------------
-- INSURANCE DOCUMENTS
-- One row per insurance documentation package generated within a Medical
-- Report Agent run.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.insurance_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  generated_report_id UUID NOT NULL REFERENCES public.generated_medical_reports (id) ON DELETE CASCADE,
  patient_id UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  diagnosis_codes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  procedure_codes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  supporting_documents_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  medical_necessity TEXT,
  claim_summary TEXT,
  supporting_evidence_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_insurance_documents_report
  ON public.insurance_documents (generated_report_id);
CREATE INDEX IF NOT EXISTS idx_insurance_documents_patient
  ON public.insurance_documents (patient_id);

ALTER TABLE public.insurance_documents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "insurance_documents_select_authenticated" ON public.insurance_documents;
CREATE POLICY "insurance_documents_select_authenticated"
  ON public.insurance_documents FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "insurance_documents_insert_authenticated" ON public.insurance_documents;
CREATE POLICY "insurance_documents_insert_authenticated"
  ON public.insurance_documents FOR INSERT TO authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "insurance_documents_update_authenticated" ON public.insurance_documents;
CREATE POLICY "insurance_documents_update_authenticated"
  ON public.insurance_documents FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "insurance_documents_delete_authenticated" ON public.insurance_documents;
CREATE POLICY "insurance_documents_delete_authenticated"
  ON public.insurance_documents FOR DELETE TO authenticated USING (true);

COMMENT ON TABLE public.prescription_results IS
  'Prescription Agent — physician-review treatment recommendations. Never a final prescription; never replaces a physician.';
COMMENT ON TABLE public.medication_recommendations IS
  'Individual medication suggestions produced by a Prescription Agent run.';
COMMENT ON TABLE public.interaction_reports IS
  'Detected drug interactions (current + suggested medications) produced by a Prescription Agent run.';
COMMENT ON TABLE public.validation_reports IS
  'Final safety validation (duplicates, contraindications, allergy conflicts, confidence, approval status) for a Prescription Agent run.';
COMMENT ON TABLE public.generated_medical_reports IS
  'Medical Report Agent — versioned professional hospital documentation bundle synthesized from all prior AI Agent output.';
COMMENT ON TABLE public.referral_letters IS
  'Generated specialist referral letters produced by a Medical Report Agent run.';
COMMENT ON TABLE public.insurance_documents IS
  'Generated insurance/claim documentation (illustrative codes only — must be verified by a certified coder) produced by a Medical Report Agent run.';
