/** Patient Registration (Intake stage 1) — TypeScript contracts. */

export type DocumentJobStatus =
  | 'Pending'
  | 'Processing'
  | 'Completed'
  | 'Failed';

export type PatientAIContextStatus =
  | 'Initialized'
  | 'Pending'
  | 'Ready'
  | 'Failed';

export interface ProcessingJob {
  id: string;
  patient_id: string;
  appointment_id: string;
  doctor_id: string;
  document_name: string;
  document_type: string;
  file_url: string;
  storage_path?: string | null;
  file_size?: number | null;
  status: DocumentJobStatus | string;
  current_stage: string;
  processing_started_at?: string | null;
  processing_completed_at?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatientAIContext {
  id: string;
  patient_id: string;
  processing_job_id?: string | null;
  status: PatientAIContextStatus | string;
  current_summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatientRegistrationResult {
  job_id: string;
  status: string;
  current_stage: string;
  next_stage: string;
  ready_for_medical_history_extraction: boolean;
  processing_job: ProcessingJob;
  patient_ai_context: PatientAIContext;
}

export interface PatientRegistrationFormValues {
  patient_id: string;
  appointment_id: string;
  doctor_id: string;
  file: File | null;
}
