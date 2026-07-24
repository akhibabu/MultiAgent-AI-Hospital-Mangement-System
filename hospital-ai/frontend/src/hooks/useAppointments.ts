import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { isAxiosError } from 'axios';
import { appointmentService } from '@/services/appointmentService';
import type {
  AppointmentFormValues,
  AppointmentListParams,
  AppointmentStatus,
} from '@/types/appointment';

export const appointmentKeys = {
  all: ['appointments'] as const,
  lists: () => [...appointmentKeys.all, 'list'] as const,
  list: (params: AppointmentListParams) =>
    [...appointmentKeys.lists(), params] as const,
  details: () => [...appointmentKeys.all, 'detail'] as const,
  detail: (id: string) => [...appointmentKeys.details(), id] as const,
  slots: (doctorId: string, date: string) =>
    [...appointmentKeys.all, 'slots', doctorId, date] as const,
};

function errMsg(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
  }
  if (error instanceof Error) return error.message;
  return fallback;
}

export function useAppointments(params: AppointmentListParams) {
  return useQuery({
    queryKey: appointmentKeys.list(params),
    queryFn: () => appointmentService.list(params),
    placeholderData: (prev) => prev,
  });
}

export function useAppointment(id: string | undefined) {
  return useQuery({
    queryKey: appointmentKeys.detail(id || ''),
    queryFn: () => appointmentService.getById(id!),
    enabled: Boolean(id),
  });
}

export function useAvailableSlots(
  doctorId: string | undefined,
  appointmentDate: string | undefined,
) {
  return useQuery({
    queryKey: appointmentKeys.slots(doctorId || '', appointmentDate || ''),
    queryFn: () => appointmentService.getSlots(doctorId!, appointmentDate!),
    enabled: Boolean(doctorId && appointmentDate),
  });
}

export function useCreateAppointment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (values: AppointmentFormValues) =>
      appointmentService.create(values),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: appointmentKeys.lists() });
      toast.success('Appointment booked successfully');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to book appointment')),
  });
}

export function useUpdateAppointment(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (values: AppointmentFormValues) =>
      appointmentService.update(id, values),
    onSuccess: (appt) => {
      qc.invalidateQueries({ queryKey: appointmentKeys.lists() });
      qc.setQueryData(appointmentKeys.detail(id), appt);
      toast.success('Appointment updated');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to update appointment')),
  });
}

export function useRescheduleAppointment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...payload
    }: {
      id: string;
      appointment_date: string;
      start_time: string;
      end_time: string;
      notes?: string;
    }) => appointmentService.reschedule(id, payload),
    onSuccess: (appt) => {
      qc.invalidateQueries({ queryKey: appointmentKeys.lists() });
      qc.setQueryData(appointmentKeys.detail(appt.id), appt);
      toast.success('Appointment rescheduled');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to reschedule')),
  });
}

export function useUpdateAppointmentStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      status,
      notes,
    }: {
      id: string;
      status: AppointmentStatus;
      notes?: string;
    }) => appointmentService.updateStatus(id, status, notes),
    onSuccess: (appt) => {
      qc.invalidateQueries({ queryKey: appointmentKeys.lists() });
      qc.setQueryData(appointmentKeys.detail(appt.id), appt);
      toast.success(`Marked as ${appt.status}`);
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to update status')),
  });
}

export function useDeleteAppointment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => appointmentService.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: appointmentKeys.lists() });
      toast.success('Appointment deleted');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to delete appointment')),
  });
}
