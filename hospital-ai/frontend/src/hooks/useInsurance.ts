import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { isAxiosError } from 'axios';
import { insuranceService } from '@/services/insuranceService';
import type { InsuranceStartRequest } from '@/types/insurance';

export const insuranceKeys = {
  all: ['insurance'] as const,
  result: (patientId: string) => [...insuranceKeys.all, 'result', patientId] as const,
  history: (patientId: string) => [...insuranceKeys.all, 'history', patientId] as const,
};

function getErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
  }
  return error instanceof Error ? error.message : 'Insurance Agent failed';
}

export function useInsuranceResult(patientId: string | undefined) {
  return useQuery({
    queryKey: insuranceKeys.result(patientId || ''),
    queryFn: () => insuranceService.result(patientId!),
    enabled: Boolean(patientId),
    retry: false,
  });
}

export function useInsuranceHistory(patientId: string | undefined) {
  return useQuery({
    queryKey: insuranceKeys.history(patientId || ''),
    queryFn: () => insuranceService.history(patientId!),
    enabled: Boolean(patientId),
    retry: false,
  });
}

export function useStartInsurance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: InsuranceStartRequest) => insuranceService.start(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(insuranceKeys.result(data.patient_id), data.insurance_result);
      queryClient.invalidateQueries({ queryKey: insuranceKeys.history(data.patient_id) });
      toast.success('Insurance Agent completed a draft review');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });
}
