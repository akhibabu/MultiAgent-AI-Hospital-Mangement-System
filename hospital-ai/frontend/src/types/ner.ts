/** Intake Stage 4 — Medical Entity Recognition types. */

export interface MedicalEntity {
  id?: string | null;
  type: string;
  value: string;
  confidence: number;
  source_document?: string | null;
  page?: number;
  sentence?: string | null;
  char_start?: number | null;
  char_end?: number | null;
  extraction_time?: string | null;
  metadata?: Record<string, unknown>;
}

export interface EntityStatistics {
  disease_count: number;
  medication_count: number;
  symptom_count: number;
  allergy_count: number;
  vital_count: number;
  lab_value_count: number;
  lab_test_count: number;
  procedure_count: number;
  dosage_count: number;
  date_count: number;
  doctor_count: number;
  hospital_count: number;
  body_part_count: number;
  total_entities: number;
}

export interface PatientEntitySummary {
  conditions: string[];
  current_medications: Array<{
    name?: string;
    dosage?: string | null;
    frequency?: string | null;
  }>;
  symptoms: string[];
  allergies: string[];
  recent_tests: string[];
  recent_procedures: string[];
  vitals: Array<{ name?: string; value?: string; unit?: string | null }>;
  follow_up: string[];
  doctors: string[];
  hospitals: string[];
}

export interface NERResult {
  id: string;
  processing_job_id: string;
  patient_id: string;
  ocr_result_id?: string | null;
  entity_count: number;
  statistics_json: Partial<EntityStatistics> & Record<string, unknown>;
  summary_json: Partial<PatientEntitySummary> & Record<string, unknown>;
  entities_json: MedicalEntity[];
  source_text_preview?: string | null;
  confidence?: number | null;
  processing_time_ms?: number | null;
  status: string;
  error_message?: string | null;
  created_at: string;
}

export interface NERStartResult {
  job_id: string;
  patient_id: string;
  status: string;
  current_stage: string;
  next_stage: string;
  entity_count: number;
  confidence: number;
  processing_time_ms: number;
  statistics: EntityStatistics;
  summary: PatientEntitySummary;
  entities: MedicalEntity[];
  source_text: string;
  warnings: string[];
  ner_result: NERResult;
  processing_job: { id: string; current_stage: string; status: string };
  patient_context_version: number;
}

export interface NERStatus {
  job_id: string;
  status: string;
  current_stage: string;
  next_stage: string;
  progress_pct: number;
  ner_completed: boolean;
  entity_count?: number | null;
  confidence?: number | null;
  error_message?: string | null;
}

/** Highlight colors for interactive report */
export const ENTITY_HIGHLIGHT: Record<
  string,
  { bg: string; text: string; label: string }
> = {
  Disease: { bg: 'bg-red-500/20', text: 'text-red-800 dark:text-red-200', label: 'Disease' },
  Medication: {
    bg: 'bg-blue-500/20',
    text: 'text-blue-800 dark:text-blue-200',
    label: 'Medication',
  },
  Symptom: {
    bg: 'bg-orange-500/20',
    text: 'text-orange-800 dark:text-orange-200',
    label: 'Symptom',
  },
  'Lab Value': {
    bg: 'bg-purple-500/20',
    text: 'text-purple-800 dark:text-purple-200',
    label: 'Lab Value',
  },
  'Lab Test': {
    bg: 'bg-purple-500/15',
    text: 'text-purple-700 dark:text-purple-300',
    label: 'Lab Test',
  },
  Allergy: {
    bg: 'bg-yellow-400/30',
    text: 'text-yellow-900 dark:text-yellow-100',
    label: 'Allergy',
  },
  Date: {
    bg: 'bg-emerald-500/20',
    text: 'text-emerald-800 dark:text-emerald-200',
    label: 'Date',
  },
  'Follow-up Date': {
    bg: 'bg-emerald-500/25',
    text: 'text-emerald-900 dark:text-emerald-100',
    label: 'Follow-up',
  },
  Vital: {
    bg: 'bg-fuchsia-500/15',
    text: 'text-fuchsia-800 dark:text-fuchsia-200',
    label: 'Vital',
  },
  Dosage: {
    bg: 'bg-sky-500/15',
    text: 'text-sky-800 dark:text-sky-200',
    label: 'Dosage',
  },
  Frequency: {
    bg: 'bg-sky-500/10',
    text: 'text-sky-700 dark:text-sky-300',
    label: 'Frequency',
  },
  Procedure: {
    bg: 'bg-indigo-500/15',
    text: 'text-indigo-800 dark:text-indigo-200',
    label: 'Procedure',
  },
  Doctor: {
    bg: 'bg-teal-500/15',
    text: 'text-teal-800 dark:text-teal-200',
    label: 'Doctor',
  },
  Hospital: {
    bg: 'bg-cyan-500/15',
    text: 'text-cyan-800 dark:text-cyan-200',
    label: 'Hospital',
  },
  'Body Part': {
    bg: 'bg-rose-500/10',
    text: 'text-rose-800 dark:text-rose-200',
    label: 'Body Part',
  },
};
