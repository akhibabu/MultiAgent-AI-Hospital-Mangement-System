import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { emergencyService } from '@/services/emergencyService';
import { getApiErrorMessage } from '@/services/apiClient';

export const emergencyKeys = {
  all: ['emergency'] as const,
  result: (patientId: string) => [...emergencyKeys.all, 'result', patientId] as const,
};

export function useEmergencyResult(patientId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: emergencyKeys.result(patientId || ''),
    queryFn: () => emergencyService.result(patientId!),
    enabled: Boolean(patientId) && enabled,
    retry: false,
  });
}

export function useStartEmergency(patientId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => emergencyService.start(patientId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: emergencyKeys.all });
      toast.success('Emergency Agent completed — review the acuity signals with clinical staff.');
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Emergency Agent failed'));
    },
  });
}
