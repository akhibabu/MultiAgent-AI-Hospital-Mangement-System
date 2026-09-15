export interface ChartSeries {
  label: string;
  value: number;
}

export interface DashboardStatistics {
  total_patients: number;
  total_doctors: number;
  todays_appointments: number;
  available_beds: number;
  icu_occupancy_pct: number;
  total_departments: number;
  medical_records_uploaded: number;
  available_resources: number;
}

export interface DashboardCharts {
  appointments_per_day: ChartSeries[];
  patients_per_department: ChartSeries[];
  doctor_distribution: ChartSeries[];
  bed_utilization: ChartSeries[];
  monthly_patient_registration: ChartSeries[];
  appointment_status_distribution: ChartSeries[];
}

export interface ActivityItem {
  id: string;
  type: string;
  title: string;
  subtitle?: string | null;
  timestamp: string;
  link?: string | null;
}

export interface RecentActivities {
  new_patients: ActivityItem[];
  new_doctors: ActivityItem[];
  recent_medical_records: ActivityItem[];
  todays_appointments: ActivityItem[];
  recently_updated_records: ActivityItem[];
}

export interface UpcomingAppointmentItem {
  id: string;
  appointment_number: string;
  patient_name: string;
  doctor_name: string;
  appointment_date: string;
  start_time: string;
  status: string;
  visit_type: string;
}

export interface ResourceSummary {
  items: Array<{
    resource_type: string;
    total_quantity: number;
    available_quantity: number;
    in_use: number;
  }>;
  total_beds: number;
  available_beds: number;
  total_icu: number;
  available_icu: number;
  operation_theatres: number;
  ventilators_available: number;
  laboratories: number;
}

export interface GlobalSearchHit {
  id: string;
  category: string;
  title: string;
  subtitle?: string | null;
  link: string;
}

export interface GlobalSearchResponse {
  query: string;
  patients: GlobalSearchHit[];
  doctors: GlobalSearchHit[];
  departments: GlobalSearchHit[];
  appointments: GlobalSearchHit[];
  medical_records: GlobalSearchHit[];
  total: number;
}

export interface HospitalSettings {
  hospitalName: string;
  hospitalLogo: string;
  theme: 'system' | 'light' | 'dark';
  language: string;
  timezone: string;
  emailNotifications: boolean;
  smsNotifications: boolean;
  appointmentReminders: boolean;
  aiConfigPlaceholder: string;
}

export const DEFAULT_HOSPITAL_SETTINGS: HospitalSettings = {
  hospitalName: 'Hospital',
  hospitalLogo: '',
  theme: 'system',
  language: 'en',
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
  emailNotifications: true,
  smsNotifications: false,
  appointmentReminders: true,
  aiConfigPlaceholder: 'AI agents configuration will be available in Week 2.',
};
