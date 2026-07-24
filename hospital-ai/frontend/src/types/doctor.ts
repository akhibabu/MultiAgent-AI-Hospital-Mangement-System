export type DoctorGender = 'Male' | 'Female' | 'Other';

export type AvailabilityStatus = 'Available' | 'Busy' | 'On Leave';

/** Reserved for future AI agents — currently unused. */
export interface DoctorAIExtensions {
  ai_summary: string | null;
  performance_metrics: unknown | null;
  predicted_workload: unknown | null;
  recommended_schedule: unknown | null;
  /** Reserved for Scheduling Agent — unused. */
  schedule_score?: unknown | null;
}

export interface DepartmentBrief {
  id: string;
  name: string;
}

export interface Doctor extends DoctorAIExtensions {
  id: string;
  doctor_number: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  gender: DoctorGender;
  date_of_birth: string | null;
  department_id: string | null;
  specialization: string;
  qualification: string | null;
  experience_years: number;
  license_number: string | null;
  consultation_fee: number | string;
  availability_status: AvailabilityStatus;
  profile_photo_url: string | null;
  bio: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  department: DepartmentBrief | null;
}

export interface DoctorFormValues {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  gender: DoctorGender | '';
  date_of_birth: string;
  department_id: string;
  specialization: string;
  qualification: string;
  experience_years: string;
  license_number: string;
  consultation_fee: string;
  availability_status: AvailabilityStatus;
  profile_photo_url: string;
  bio: string;
}

export interface DoctorListParams {
  page?: number;
  page_size?: number;
  search?: string;
  department_id?: string;
  availability_status?: AvailabilityStatus | '';
  min_experience?: number | '';
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface DoctorListResponse {
  items: Doctor[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Department {
  id: string;
  name: string;
  description: string | null;
  floor_number: number | null;
  head_doctor_id: string | null;
  created_at: string;
  updated_at: string;
  doctors_count: number;
  patients_count: number;
  head_doctor_name: string | null;
}

export interface DepartmentFormValues {
  name: string;
  description: string;
  floor_number: string;
  head_doctor_id: string;
}

export interface DepartmentListResponse {
  items: Department[];
  total: number;
}

export interface DoctorAvailability {
  id: string;
  doctor_id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  slot_duration: number;
  is_available: boolean;
  created_at: string;
  updated_at: string;
}

export interface AvailabilityFormValues {
  day_of_week: number;
  start_time: string;
  end_time: string;
  slot_duration: string;
  is_available: boolean;
}

export const AVAILABILITY_STATUSES: AvailabilityStatus[] = [
  'Available',
  'Busy',
  'On Leave',
];

export const GENDER_OPTIONS: DoctorGender[] = ['Male', 'Female', 'Other'];

export const DAYS_OF_WEEK = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
] as const;

export const EMPTY_DOCTOR_FORM: DoctorFormValues = {
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  gender: '',
  date_of_birth: '',
  department_id: '',
  specialization: '',
  qualification: '',
  experience_years: '0',
  license_number: '',
  consultation_fee: '0',
  availability_status: 'Available',
  profile_photo_url: '',
  bio: '',
};

export const EMPTY_DEPARTMENT_FORM: DepartmentFormValues = {
  name: '',
  description: '',
  floor_number: '',
  head_doctor_id: '',
};
