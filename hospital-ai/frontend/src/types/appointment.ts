/** Appointment domain types + AI extension placeholders. */

export type AppointmentStatus =
  | 'Scheduled'
  | 'Completed'
  | 'Cancelled'
  | 'No Show'
  | 'Rescheduled';

export type VisitType =
  | 'Consultation'
  | 'Follow Up'
  | 'Emergency'
  | 'Telemedicine';

/** Reserved for future AI agents — currently unused. */
export interface AppointmentAIExtensions {
  predicted_wait_time: number | null;
  priority_score: number | string | null;
  recommended_slot: unknown | null;
  ai_notes: string | null;
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
  specialization?: string | null;
}

export interface DepartmentBrief {
  id: string;
  name: string;
}

export interface Appointment extends AppointmentAIExtensions {
  id: string;
  appointment_number: string;
  patient_id: string;
  doctor_id: string;
  department_id: string | null;
  appointment_date: string;
  start_time: string;
  end_time: string;
  status: AppointmentStatus;
  visit_type: VisitType;
  reason_for_visit: string | null;
  notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  patient: PatientBrief | null;
  doctor: DoctorBrief | null;
  department: DepartmentBrief | null;
}

export interface AppointmentFormValues {
  patient_id: string;
  doctor_id: string;
  department_id: string;
  appointment_date: string;
  start_time: string;
  end_time: string;
  visit_type: VisitType;
  reason_for_visit: string;
  notes: string;
  status?: AppointmentStatus;
}

export interface AppointmentListParams {
  page?: number;
  page_size?: number;
  search?: string;
  doctor_id?: string;
  patient_id?: string;
  department_id?: string;
  status?: AppointmentStatus | '';
  visit_type?: VisitType | '';
  date_from?: string;
  date_to?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface AppointmentListResponse {
  items: Appointment[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AvailableSlot {
  start_time: string;
  end_time: string;
}

export interface AvailableSlotsResponse {
  doctor_id: string;
  appointment_date: string;
  day_of_week: number;
  available_days: number[];
  slots: AvailableSlot[];
  message: string | null;
}

export const APPOINTMENT_STATUSES: AppointmentStatus[] = [
  'Scheduled',
  'Completed',
  'Cancelled',
  'No Show',
  'Rescheduled',
];

export const VISIT_TYPES: VisitType[] = [
  'Consultation',
  'Follow Up',
  'Emergency',
  'Telemedicine',
];

export const EMPTY_APPOINTMENT_FORM: AppointmentFormValues = {
  patient_id: '',
  doctor_id: '',
  department_id: '',
  appointment_date: '',
  start_time: '',
  end_time: '',
  visit_type: 'Consultation',
  reason_for_visit: '',
  notes: '',
};

export const STATUS_CHIP_COLORS: Record<AppointmentStatus, string> = {
  Scheduled: 'bg-sky-500/15 text-sky-700 dark:text-sky-300',
  Completed: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
  Cancelled: 'bg-rose-500/15 text-rose-700 dark:text-rose-300',
  'No Show': 'bg-amber-500/15 text-amber-800 dark:text-amber-300',
  Rescheduled: 'bg-violet-500/15 text-violet-700 dark:text-violet-300',
};

export const CALENDAR_EVENT_COLORS: Record<
  AppointmentStatus | 'Emergency',
  string
> = {
  Scheduled: 'bg-sky-600 border-sky-700',
  Completed: 'bg-emerald-600 border-emerald-700',
  Cancelled: 'bg-rose-600/70 border-rose-700 line-through opacity-80',
  'No Show': 'bg-amber-600 border-amber-700',
  Rescheduled: 'bg-violet-600 border-violet-700',
  Emergency: 'bg-orange-600 border-orange-700',
};

export const DAY_LABELS = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
];
