import type { AppointmentFormValues } from '@/types/appointment';

export function validateAppointmentForm(
  values: AppointmentFormValues,
): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!values.patient_id) errors.patient_id = 'Patient is required';
  if (!values.doctor_id) errors.doctor_id = 'Doctor is required';
  if (!values.appointment_date) {
    errors.appointment_date = 'Date is required';
  }
  if (!values.start_time) errors.start_time = 'Start time is required';
  if (!values.end_time) errors.end_time = 'End time is required';
  if (!values.visit_type) errors.visit_type = 'Visit type is required';

  if (values.start_time && values.end_time) {
    const [sh, sm] = values.start_time.split(':').map(Number);
    const [eh, em] = values.end_time.split(':').map(Number);
    const start = sh * 60 + sm;
    const end = eh * 60 + em;
    if (end <= start) {
      errors.end_time = 'End time must be after start time';
    } else if (end - start < 5) {
      errors.end_time = 'Minimum duration is 5 minutes';
    } else if (end - start > 480) {
      errors.end_time = 'Maximum duration is 8 hours';
    }
  }

  return errors;
}

export function formatTimeLabel(value: string): string {
  if (!value) return '—';
  const parts = value.split(':');
  if (parts.length < 2) return value;
  const h = Number(parts[0]);
  const m = parts[1];
  const suffix = h >= 12 ? 'PM' : 'AM';
  const hour12 = h % 12 || 12;
  return `${hour12}:${m} ${suffix}`;
}

export function formatDateLabel(value: string): string {
  if (!value) return '—';
  const d = new Date(`${value}T00:00:00`);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function toDateInputValue(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function startOfWeek(d: Date): Date {
  const copy = new Date(d);
  const day = (copy.getDay() + 6) % 7; // Monday=0
  copy.setDate(copy.getDate() - day);
  copy.setHours(0, 0, 0, 0);
  return copy;
}

export function addDays(d: Date, n: number): Date {
  const copy = new Date(d);
  copy.setDate(copy.getDate() + n);
  return copy;
}
