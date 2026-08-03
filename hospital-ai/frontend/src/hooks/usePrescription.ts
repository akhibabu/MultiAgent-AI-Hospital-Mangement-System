import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { isAxiosError } from 'axios';
import { prescriptionService } from '@/services/prescriptionService';

export const prescriptionKeys = {
  all: ['prescription'] as const,
  result: (patientId: string) => [...prescriptionKeys.all, 'result', patientId] as const,
  status: (patientId: string) => [...prescriptionKeys.all, 'status', patientId] as const,
  history: (patientId: string) => [...prescriptionKeys.all, 'history', patientId] as const,
};

function getErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item?.msg || JSON.stringify(item)).join(', ');
    }
  }
  if (error instanceof Error) return error.message;
  return fallback;
}

export function usePrescriptionResult(patientId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: prescriptionKeys.result(patientId || ''),
    queryFn: () => prescriptionService.result(patientId!),
    enabled: Boolean(patientId) && enabled,
    retry: false,
  });
}

export function usePrescriptionStatus(patientId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: prescriptionKeys.status(patientId || ''),
    queryFn: () => prescriptionService.status(patientId!),
    enabled: Boolean(patientId) && enabled,
    retry: false,
  });
}

export function usePrescriptionHistory(patientId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: prescriptionKeys.history(patientId || ''),
    queryFn: () => prescriptionService.history(patientId!),
    enabled: Boolean(patientId) && enabled,
    retry: false,
  });
}

export function useStartPrescription(patientId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (options?: { diagnosis_result_id?: string; research_result_id?: string }) =>
      prescriptionService.start(patientId!, options),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: prescriptionKeys.all });
      toast.success('Prescription Agent completed — physician review required before use.');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Prescription Agent failed'));
    },
  });
}
