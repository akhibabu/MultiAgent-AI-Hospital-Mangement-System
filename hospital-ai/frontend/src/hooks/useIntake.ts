import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { isAxiosError } from 'axios';
import { intakeService } from '@/services/intakeService';

export const intakeKeys = {
  all: ['intake'] as const,
  dashboard: (patientId: string) =>
    [...intakeKeys.all, 'dashboard', patientId] as const,
  agentInput: (patientId: string) =>
    [...intakeKeys.all, 'agent-input', patientId] as const,
};

function getErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => item?.msg || JSON.stringify(item))
        .join(', ');
    }
  }
  if (error instanceof Error) return error.message;
  return fallback;
}

export function useIntakeDashboard(patientId: string | undefined) {
  return useQuery({
    queryKey: intakeKeys.dashboard(patientId || ''),
    queryFn: () => intakeService.getDashboard(patientId!),
    enabled: Boolean(patientId),
    refetchInterval: (query) => {
      const jobs = query.state.data?.jobs ?? [];
      const running = jobs.some(
        (j) =>
          j.status !== 'Completed' &&
          j.status !== 'Failed' &&
          j.status !== 'Queued',
      );
      return running ? 4000 : false;
    },
  });
}

export function useProcessIntakeDocument(patientId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) =>
      intakeService.processDocument(documentId),
    onSuccess: () => {
      if (patientId) {
        queryClient.invalidateQueries({
          queryKey: intakeKeys.dashboard(patientId),
        });
      }
      toast.success('Intake Agent finished processing');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Intake processing failed'));
    },
  });
}
