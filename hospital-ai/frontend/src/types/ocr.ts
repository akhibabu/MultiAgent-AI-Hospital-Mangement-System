/** Intake Stage 3 — Document Processing / OCR types. */

import type { ProcessingJob } from '@/types/registration';
import type { UnifiedMedicalHistory, TimelineEvent } from '@/types/medicalHistory';

export interface OCRResult {
  id: string;
  processing_job_id: string;
  patient_id: string;
  document_id?: string | null;
  provider: string;
  raw_text: string;
  clean_text?: string | null;
  tables_json: unknown[];
  images_json: unknown[];
  detected_language?: string | null;
  page_count: number;
  processing_time_ms?: number | null;
  confidence?: number | null;
  provenance_json?: Record<string, unknown>;
  extraction_method?: string | null;
  processing_method?: string | null;
  document_type?: string | null;
  ocr_provider?: string | null;
  library_used?: string | null;
  fallback_used?: boolean | null;
  document_status?: string | null;
  status?: string | null;
  character_count?: number | null;
  word_count?: number | null;
  processing_logs?: unknown[] | null;
  error_message?: string | null;
  created_at: string;
}

export interface OCRStartResult {
  job_id: string;
  patient_id: string;
  status: string;
  current_stage: string;
  next_stage: string;
  provider: string;
  confidence: number;
  page_count: number;
  processing_time_ms: number;
  detected_language: string;
  extraction_method?: string;
  processing_method?: string;
  document_type?: string;
  ocr_provider?: string | null;
  library_used?: string;
  fallback_used?: boolean;
  document_status?: string;
  character_count?: number;
  word_count?: number;
  warnings: string[];
  ocr_result: OCRResult;
  processing_job: ProcessingJob;
  patient_context_version: number;
}

export interface OCRStatus {
  job_id: string;
  status: string;
  current_stage: string;
  next_stage: string;
  progress_pct: number;
  provider?: string | null;
  confidence?: number | null;
  processing_time_ms?: number | null;
  error_message?: string | null;
  ocr_completed: boolean;
  processing_job: ProcessingJob;
}

export interface PatientContextView {
  patient_id: string;
  status: string;
  current_summary?: string | null;
  ocr_completed: boolean;
  ocr_provider?: string | null;
  ocr_confidence?: number | null;
  ocr_timestamp?: string | null;
  context_version: number;
  patient_context_json: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export type IntakeStageId =
  | 'registration'
  | 'history'
  | 'context'
  | 'ocr'
  | 'ner'
  | 'risk'
  | 'knowledge';

export interface IntakeStageDef {
  id: IntakeStageId;
  label: string;
  description?: string;
  stageKey?: string;
}

export const INTAKE_STAGES: IntakeStageDef[] = [
  {
    id: 'registration',
    label: 'Patient Registration',
    stageKey: 'Patient Registration',
    description: 'Link patient, appointment, doctor, and upload the report.',
  },
  {
    id: 'history',
    label: 'Medical History Extraction',
    stageKey: 'Medical History Extraction',
    description: 'Gather prior visits, diagnoses, and medications from hospital records.',
  },
  {
    id: 'context',
    label: 'Patient Context Builder',
    description: 'Build a readable clinical summary for downstream AI stages.',
  },
  {
    id: 'ocr',
    label: 'Document Processing',
    stageKey: 'OCR',
    description: 'Convert uploaded documents into readable text.',
  },
  {
    id: 'ner',
    label: 'Medical Entity Recognition',
    stageKey: 'Medical Entity Recognition',
    description: 'Identify clinical entities from the extracted text.',
  },
  {
    id: 'risk',
    label: 'Patient Risk Profiling',
    description: 'Estimate clinical risk from structured findings.',
  },
  {
    id: 'knowledge',
    label: 'Patient Knowledge Graph',
    description: 'Connect symptoms, conditions, and treatments for AI agents.',
  },
];

export type { UnifiedMedicalHistory, TimelineEvent };
