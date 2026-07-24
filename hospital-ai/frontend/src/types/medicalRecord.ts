/** Medical records types + AI / RAG extension placeholders. */

export type MedicalRecordType =
  | 'Consultation'
  | 'Prescription'
  | 'Lab Report'
  | 'X-Ray'
  | 'MRI'
  | 'CT Scan'
  | 'Ultrasound'
  | 'Discharge Summary'
  | 'Vaccination'
  | 'Other';

/** Reserved for future AI / RAG agents — currently unused. */
export interface MedicalRecordAIExtensions {
  ai_summary: string | null;
  detected_conditions: unknown | null;
  risk_score: number | string | null;
  recommended_tests: unknown | null;
  embedding_id: string | null;
  vector_status: string | null;
  ocr_status: string | null;
}

export interface PatientBrief {
  id: string;
  patient_number: string;
  first_name: string;
  last_name: string;
}

export interface DoctorBrief {
  id: string;
  doctor_number: string;
  first_name: string;
  last_name: string;
}

export interface AppointmentBrief {
  id: string;
  appointment_number: string;
  appointment_date?: string | null;
}

export interface MedicalDocument {
  id: string;
  medical_record_id: string;
  file_name: string;
  file_url: string;
  storage_path: string;
  file_type: string;
  file_size: number;
  uploaded_by: string | null;
  created_at: string;
  signed_url?: string | null;
}

export interface MedicalRecord extends MedicalRecordAIExtensions {
  id: string;
  patient_id: string;
  appointment_id: string | null;
  doctor_id: string | null;
  record_type: MedicalRecordType;
  title: string;
  description: string | null;
  diagnosis: string | null;
  treatment: string | null;
  notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  patient: PatientBrief | null;
  doctor: DoctorBrief | null;
  appointment: AppointmentBrief | null;
  documents: MedicalDocument[];
}

export interface MedicalRecordFormValues {
  patient_id: string;
  appointment_id: string;
  doctor_id: string;
  record_type: MedicalRecordType;
  title: string;
  description: string;
  diagnosis: string;
  treatment: string;
  notes: string;
}

export interface MedicalRecordListParams {
  page?: number;
  page_size?: number;
  search?: string;
  patient_id?: string;
  doctor_id?: string;
  appointment_id?: string;
  record_type?: MedicalRecordType | '';
  date_from?: string;
  date_to?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface MedicalRecordListResponse {
  items: MedicalRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface MedicalRecordAudit {
  id: string;
  record_id: string | null;
  document_id: string | null;
  action: string;
  performed_by: string | null;
  details: unknown | null;
  timestamp: string;
}

export const MEDICAL_RECORD_TYPES: MedicalRecordType[] = [
  'Consultation',
  'Prescription',
  'Lab Report',
  'X-Ray',
  'MRI',
  'CT Scan',
  'Ultrasound',
  'Discharge Summary',
  'Vaccination',
  'Other',
];

export const EMPTY_MEDICAL_RECORD_FORM: MedicalRecordFormValues = {
  patient_id: '',
  appointment_id: '',
  doctor_id: '',
  record_type: 'Consultation',
  title: '',
  description: '',
  diagnosis: '',
  treatment: '',
  notes: '',
};

export const RECORD_TYPE_COLORS: Record<MedicalRecordType, string> = {
  Consultation: 'bg-sky-500/15 text-sky-700 dark:text-sky-300',
  Prescription: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
  'Lab Report': 'bg-amber-500/15 text-amber-800 dark:text-amber-300',
  'X-Ray': 'bg-violet-500/15 text-violet-700 dark:text-violet-300',
  MRI: 'bg-fuchsia-500/15 text-fuchsia-700 dark:text-fuchsia-300',
  'CT Scan': 'bg-indigo-500/15 text-indigo-700 dark:text-indigo-300',
  Ultrasound: 'bg-cyan-500/15 text-cyan-700 dark:text-cyan-300',
  'Discharge Summary': 'bg-rose-500/15 text-rose-700 dark:text-rose-300',
  Vaccination: 'bg-lime-500/15 text-lime-800 dark:text-lime-300',
  Other: 'bg-slate-500/15 text-slate-700 dark:text-slate-300',
};

export const IMAGING_TYPES: MedicalRecordType[] = [
  'X-Ray',
  'MRI',
  'CT Scan',
  'Ultrasound',
];
