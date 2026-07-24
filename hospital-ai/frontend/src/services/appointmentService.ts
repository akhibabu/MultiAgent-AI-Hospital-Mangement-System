import apiClient from '@/services/apiClient';
import type {
  Appointment,
  AppointmentFormValues,
  AppointmentListParams,
  AppointmentListResponse,
  AppointmentStatus,
  AvailableSlotsResponse,
} from '@/types/appointment';

function normalizeTime(value: string): string {
  if (!value) return value;
  return value.length === 5 ? `${value}:00` : value;
}

function cleanPayload(values: AppointmentFormValues) {
  return {
    patient_id: values.patient_id,
    doctor_id: values.doctor_id,
    department_id: values.department_id || null,
    appointment_date: values.appointment_date,
    start_time: normalizeTime(values.start_time),
    end_time: normalizeTime(values.end_time),
    visit_type: values.visit_type,
    reason_for_visit: values.reason_for_visit.trim() || null,
    notes: values.notes.trim() || null,
    ...(values.status ? { status: values.status } : {}),
  };
}

export const appointmentService = {
  async list(
    params: AppointmentListParams = {},
  ): Promise<AppointmentListResponse> {
    const { data } = await apiClient.get<AppointmentListResponse>(
      '/appointments',
      {
        params: {
          page: params.page ?? 1,
          page_size: params.page_size ?? 10,
          search: params.search || undefined,
          doctor_id: params.doctor_id || undefined,
          patient_id: params.patient_id || undefined,
          department_id: params.department_id || undefined,
          status: params.status || undefined,
          visit_type: params.visit_type || undefined,
          date_from: params.date_from || undefined,
          date_to: params.date_to || undefined,
          sort_by: params.sort_by ?? 'appointment_date',
          sort_order: params.sort_order ?? 'desc',
        },
      },
    );
    return data;
  },

  async getById(id: string): Promise<Appointment> {
    const { data } = await apiClient.get<Appointment>(`/appointments/${id}`);
    return data;
  },

  async create(values: AppointmentFormValues): Promise<Appointment> {
    const { data } = await apiClient.post<Appointment>(
      '/appointments',
      cleanPayload(values),
    );
    return data;
  },

  async update(
    id: string,
    values: AppointmentFormValues,
  ): Promise<Appointment> {
    const { data } = await apiClient.put<Appointment>(
      `/appointments/${id}`,
      cleanPayload(values),
    );
    return data;
  },

  async reschedule(
    id: string,
    payload: {
      appointment_date: string;
      start_time: string;
      end_time: string;
      notes?: string;
    },
  ): Promise<Appointment> {
    const { data } = await apiClient.post<Appointment>(
      `/appointments/${id}/reschedule`,
      {
        appointment_date: payload.appointment_date,
        start_time: normalizeTime(payload.start_time),
        end_time: normalizeTime(payload.end_time),
        notes: payload.notes?.trim() || null,
      },
    );
    return data;
  },

  async updateStatus(
    id: string,
    status: AppointmentStatus,
    notes?: string,
  ): Promise<Appointment> {
    const { data } = await apiClient.post<Appointment>(
      `/appointments/${id}/status`,
      { status, notes: notes?.trim() || null },
    );
    return data;
  },

  async remove(id: string): Promise<void> {
    await apiClient.delete(`/appointments/${id}`);
  },

  async getSlots(
    doctorId: string,
    appointmentDate: string,
  ): Promise<AvailableSlotsResponse> {
    const { data } = await apiClient.get<AvailableSlotsResponse>(
      '/appointments/slots',
      {
        params: {
          doctor_id: doctorId,
          appointment_date: appointmentDate,
        },
      },
    );
    return data;
  },
};
