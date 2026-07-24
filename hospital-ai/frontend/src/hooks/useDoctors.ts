import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { isAxiosError } from 'axios';
import { departmentService, doctorService } from '@/services/doctorService';
import type {
  AvailabilityFormValues,
  DepartmentFormValues,
  DoctorFormValues,
  DoctorListParams,
} from '@/types/doctor';

export const doctorKeys = {
  all: ['doctors'] as const,
  lists: () => [...doctorKeys.all, 'list'] as const,
  list: (params: DoctorListParams) => [...doctorKeys.lists(), params] as const,
  details: () => [...doctorKeys.all, 'detail'] as const,
  detail: (id: string) => [...doctorKeys.details(), id] as const,
  availability: (id: string) =>
    [...doctorKeys.all, 'availability', id] as const,
};

export const departmentKeys = {
  all: ['departments'] as const,
  lists: () => [...departmentKeys.all, 'list'] as const,
  list: (search?: string) => [...departmentKeys.lists(), search ?? ''] as const,
  detail: (id: string) => [...departmentKeys.all, 'detail', id] as const,
};

function errMsg(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
  }
  if (error instanceof Error) return error.message;
  return fallback;
}

export function useDoctors(params: DoctorListParams) {
  return useQuery({
    queryKey: doctorKeys.list(params),
    queryFn: () => doctorService.list(params),
    placeholderData: (prev) => prev,
  });
}

export function useDoctor(id: string | undefined) {
  return useQuery({
    queryKey: doctorKeys.detail(id || ''),
    queryFn: () => doctorService.getById(id!),
    enabled: Boolean(id),
  });
}

export function useDoctorAvailability(doctorId: string | undefined) {
  return useQuery({
    queryKey: doctorKeys.availability(doctorId || ''),
    queryFn: () => doctorService.listAvailability(doctorId!),
    enabled: Boolean(doctorId),
  });
}

export function useCreateDoctor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (values: DoctorFormValues) => doctorService.create(values),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: doctorKeys.lists() });
      toast.success('Doctor registered successfully');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to create doctor')),
  });
}

export function useUpdateDoctor(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (values: DoctorFormValues) => doctorService.update(id, values),
    onSuccess: (doctor) => {
      qc.invalidateQueries({ queryKey: doctorKeys.lists() });
      qc.setQueryData(doctorKeys.detail(id), doctor);
      toast.success('Doctor updated successfully');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to update doctor')),
  });
}

export function useDeleteDoctor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => doctorService.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: doctorKeys.lists() });
      toast.success('Doctor deleted');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to delete doctor')),
  });
}

export function useAddAvailability(doctorId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (values: AvailabilityFormValues) =>
      doctorService.addAvailability(doctorId, values),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: doctorKeys.availability(doctorId) });
      toast.success('Availability slot added');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to add slot')),
  });
}

export function useDeleteAvailability(doctorId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (slotId: string) => doctorService.removeAvailability(slotId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: doctorKeys.availability(doctorId) });
      toast.success('Slot removed');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to remove slot')),
  });
}

export function useDepartments(search?: string) {
  return useQuery({
    queryKey: departmentKeys.list(search),
    queryFn: () => departmentService.list(search),
  });
}

export function useDepartment(id: string | undefined) {
  return useQuery({
    queryKey: departmentKeys.detail(id || ''),
    queryFn: () => departmentService.getById(id!),
    enabled: Boolean(id),
  });
}

export function useCreateDepartment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (values: DepartmentFormValues) =>
      departmentService.create(values),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: departmentKeys.lists() });
      toast.success('Department created');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to create department')),
  });
}

export function useUpdateDepartment(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (values: DepartmentFormValues) =>
      departmentService.update(id, values),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: departmentKeys.lists() });
      qc.invalidateQueries({ queryKey: departmentKeys.detail(id) });
      toast.success('Department updated');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to update department')),
  });
}

export function useDeleteDepartment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => departmentService.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: departmentKeys.lists() });
      toast.success('Department deleted');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to delete department')),
  });
}
