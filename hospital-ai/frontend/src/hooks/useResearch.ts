import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { isAxiosError } from 'axios';
import { researchService } from '@/services/researchService';

export const researchKeys = {
  all: ['research'] as const,
  result: (patientId: string) => [...researchKeys.all, 'result', patientId] as const,
  history: (patientId: string) => [...researchKeys.all, 'history', patientId] as const,
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

export function useResearchResult(patientId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: researchKeys.result(patientId || ''),
    queryFn: () => researchService.result(patientId!),
    enabled: Boolean(patientId) && enabled,
    retry: false,
  });
}

export function useResearchHistory(patientId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: researchKeys.history(patientId || ''),
    queryFn: () => researchService.history(patientId!),
    enabled: Boolean(patientId) && enabled,
    retry: false,
  });
}

export function useStartResearch(patientId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (diagnosisResultId?: string) =>
      researchService.start(patientId!, diagnosisResultId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: researchKeys.all });
      toast.success('Research Agent completed — evidence ready for review.');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Research Agent failed'));
    },
  });
}
