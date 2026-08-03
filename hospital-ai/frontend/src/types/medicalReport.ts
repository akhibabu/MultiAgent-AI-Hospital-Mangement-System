/** Medical Report Agent types — professional hospital documentation. Assists — never replaces — clinician review. */

export interface ClinicalSummary {
  patient_overview: string;
  chief_complaint: string;
  history: string;
  diagnosis_summary: string;
  current_status: string;
  key_findings: string[];
}

export interface DoctorNotes {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  clinical_reasoning: string;
}

export interface DischargeSummary {
  admission_reason: string;
  hospital_course: string;
  procedures: string[];
  medications: string[];
  condition_on_discharge: string;
  follow_up: string;
  emergency_instructions: string;
}

export interface ReferralLetter {
  id?: string | null;
  receiving_specialist: string;
  reason: string;
  history: string;
  important_findings: string[];
  investigations: string[];
  requested_evaluation: string;
  letter_body: string;
}

export interface InsuranceDocumentation {
  id?: string | null;
  diagnosis_codes: Array<{ condition?: string; code?: string }>;
  procedure_codes: Array<{ procedure?: string; code?: string }>;
  supporting_documents: string[];
  medical_necessity: string;
  claim_summary: string;
  supporting_evidence: string[];
}

export interface FAQItem {
  question: string;
  answer: string;
}

export interface PatientReport {
  diagnosis_summary: string;
  treatment_summary: string;
  current_medicines: string[];
  lifestyle_advice: string[];
  diet: string[];
  exercise: string[];
  follow_up: string;
  emergency_contact_instructions: string;
  faq: FAQItem[];
}

export interface GeneratedMedicalReport {
  id: string;
  patient_id: string;
  diagnosis_result_id?: string | null;
  research_result_id?: string | null;
  prescription_result_id?: string | null;
  clinical_summary_json: ClinicalSummary;
  doctor_notes_json: DoctorNotes;
  discharge_summary_json: DischargeSummary;
  referral_letter_json: ReferralLetter;
  insurance_documentation_json: InsuranceDocumentation;
  patient_report_json: PatientReport;
  summary?: string | null;
  engine: string;
  version: number;
  status: string;
  error_message?: string | null;
  processing_time_ms?: number | null;
  created_at: string;
  updated_at?: string | null;
}

export interface MedicalReportStartResult {
  patient_id: string;
  diagnosis_result_id?: string | null;
  research_result_id?: string | null;
  prescription_result_id?: string | null;
  status: string;
  processing_time_ms: number;
  summary: string;
  engine: string;
  version: number;
  warnings: string[];
  clinical_summary: ClinicalSummary;
  doctor_notes: DoctorNotes;
  discharge_summary: DischargeSummary;
  referral_letter: ReferralLetter;
  insurance_documentation: InsuranceDocumentation;
  patient_report: PatientReport;
  generated_report: GeneratedMedicalReport;
}

export interface MedicalReportHistoryItem {
  id: string;
  created_at: string;
  version: number;
  summary?: string | null;
  status: string;
}

export interface MedicalReportStatus {
  patient_id: string;
  has_result: boolean;
  status: string;
  version?: number | null;
  summary?: string | null;
  processing_time_ms?: number | null;
  created_at?: string | null;
}
