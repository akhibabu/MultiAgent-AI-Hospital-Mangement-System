/** Medical History Extraction (Intake stage 2) contracts. */

import type { ProcessingJob } from '@/types/registration';

export type TimelineEventType =
  | 'Appointment'
  | 'Diagnosis'
  | 'Prescription'
  | 'Lab Report'
  | 'Imaging'
  | 'Procedure'
  | 'Discharge'
  | 'Vaccination'
  | string;

export interface TimelineEvent {
  date?: string | null;
  event_type: TimelineEventType;
  doctor?: string | null;
  department?: string | null;
  summary: string;
  reference_id?: string | null;
}

export interface UnifiedMedicalHistory {
  patient: Record<string, unknown>;
  allergies: string[];
  conditions: string[];
  medications: string[];
  surgeries: string[];
  lab_reports: Array<Record<string, unknown>>;
  appointments: Array<Record<string, unknown>>;
  reports: Array<Record<string, unknown>>;
  doctors: Array<Record<string, unknown>>;
  departments: Array<Record<string, unknown>>;
  insurance: Record<string, unknown>;
  previous_treatments: string[];
  previous_diagnoses: string[];
  previous_ai_context?: Record<string, unknown> | null;
  timeline: TimelineEvent[];
  latest_summary: string;
  warnings: string[];
}

export interface PatientMedicalHistoryRecord {
  id: string;
  patient_id: string;
  processing_job_id?: string | null;
  medical_history_json: Record<string, unknown>;
  timeline_json: unknown[];
  last_updated: string;
  created_at?: string;
  updated_at?: string;
}

export interface MedicalHistoryResponse {
  patient_id: string;
  processing_job: ProcessingJob | null;
  medical_history: UnifiedMedicalHistory | null;
  timeline: TimelineEvent[];
  current_stage: string;
  next_stage: string;
  warnings: string[];
  history_record?: PatientMedicalHistoryRecord | null;
}
