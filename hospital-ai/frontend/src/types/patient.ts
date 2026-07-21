export type PatientGender = 'Male' | 'Female' | 'Other';

export type BloodGroup =
  | 'A+'
  | 'A-'
  | 'B+'
  | 'B-'
  | 'AB+'
  | 'AB-'
  | 'O+'
  | 'O-';

/** Reserved fields for future AI agents — currently unused. */
export interface PatientAIExtensions {
  ai_context: unknown | null;
  latest_diagnosis: string | null;
  latest_report: unknown | null;
  prediction_history: unknown | null;
}

export interface Patient extends PatientAIExtensions {
  id: string;
  patient_number: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: PatientGender;
  blood_group: BloodGroup | null;
  phone: string;
  email: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  allergies: string | null;
  medical_history: string | null;
  current_medications: string | null;
  insurance_provider: string | null;
  insurance_number: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatientFormValues {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: PatientGender | '';
  blood_group: BloodGroup | '';
  phone: string;
  email: string;
  address: string;
  city: string;
  state: string;
  country: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  allergies: string;
  medical_history: string;
  current_medications: string;
  insurance_provider: string;
  insurance_number: string;
}

export interface PatientListParams {
  page?: number;
  page_size?: number;
  search?: string;
  gender?: PatientGender | '';
  blood_group?: BloodGroup | '';
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface PatientListResponse {
  items: Patient[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const GENDER_OPTIONS: PatientGender[] = ['Male', 'Female', 'Other'];

export const BLOOD_GROUP_OPTIONS: BloodGroup[] = [
  'A+',
  'A-',
  'B+',
  'B-',
  'AB+',
  'AB-',
  'O+',
  'O-',
];

export const EMPTY_PATIENT_FORM: PatientFormValues = {
  first_name: '',
  last_name: '',
  date_of_birth: '',
  gender: '',
  blood_group: '',
  phone: '',
  email: '',
  address: '',
  city: '',
  state: '',
  country: 'India',
  emergency_contact_name: '',
  emergency_contact_phone: '',
  allergies: '',
  medical_history: '',
  current_medications: '',
  insurance_provider: '',
  insurance_number: '',
};
