import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { isAxiosError } from 'axios';
import { nerService } from '@/services/nerService';
import { ocrKeys } from '@/hooks/useOcr';
import { registrationKeys } from '@/hooks/useRegistration';

export const nerKeys = {
  all: ['intake-ner'] as const,
  status: (jobId: string) => [...nerKeys.all, 'status', jobId] as const,
  result: (jobId: string) => [...nerKeys.all, 'result', jobId] as const,
  entities: (jobId: string) => [...nerKeys.all, 'entities', jobId] as const,
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

export function useNerResult(jobId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: nerKeys.result(jobId || ''),
    queryFn: () => nerService.result(jobId!),
    enabled: Boolean(jobId) && enabled,
    retry: false,
  });
}

export function useNerEntities(jobId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: nerKeys.entities(jobId || ''),
    queryFn: () => nerService.entities(jobId!),
    enabled: Boolean(jobId) && enabled,
    retry: false,
  });
}

export function useStartNer(patientId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => nerService.start(jobId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: nerKeys.all });
      queryClient.invalidateQueries({ queryKey: registrationKeys.all });
      queryClient.invalidateQueries({ queryKey: ocrKeys.all });
      if (patientId) {
        queryClient.invalidateQueries({
          queryKey: ocrKeys.context(patientId),
        });
      }
      toast.success(
        `Recognized ${result.entity_count} entities — next: ${result.next_stage}`,
      );
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Entity recognition failed'));
    },
  });
}
