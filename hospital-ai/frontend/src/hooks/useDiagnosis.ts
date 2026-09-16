import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { diagnosisService } from '@/services/diagnosisService';
import { getApiErrorMessage } from '@/services/apiClient';

export const diagnosisKeys = {
  all: ['diagnosis'] as const,
  result: (patientId: string) => [...diagnosisKeys.all, 'result', patientId] as const,
  history: (patientId: string) => [...diagnosisKeys.all, 'history', patientId] as const,
};

export function useDiagnosisResult(patientId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: diagnosisKeys.result(patientId || ''),
    queryFn: () => diagnosisService.result(patientId!),
    enabled: Boolean(patientId) && enabled,
    retry: false,
  });
}

export function useDiagnosisHistory(patientId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: diagnosisKeys.history(patientId || ''),
    queryFn: () => diagnosisService.history(patientId!),
    enabled: Boolean(patientId) && enabled,
    retry: false,
  });
}

export function useStartDiagnosis(patientId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (options?: { chief_complaint?: string; focus_symptoms?: string[] }) =>
      diagnosisService.start(patientId!, options),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: diagnosisKeys.all });
      toast.success('Diagnosis Agent completed — review results with the patient chart.');
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Diagnosis Agent failed'));
    },
  });
}
