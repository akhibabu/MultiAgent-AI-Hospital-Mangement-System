import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { isAxiosError } from 'axios';
import { riskService } from '@/services/riskService';
import { nerKeys } from '@/hooks/useNer';
import { ocrKeys } from '@/hooks/useOcr';
import { registrationKeys } from '@/hooks/useRegistration';

export const riskKeys = {
  all: ['intake-risk'] as const,
  status: (jobId: string) => [...riskKeys.all, 'status', jobId] as const,
  result: (jobId: string) => [...riskKeys.all, 'result', jobId] as const,
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

export function useRiskResult(jobId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: riskKeys.result(jobId || ''),
    queryFn: () => riskService.result(jobId!),
    enabled: Boolean(jobId) && enabled,
    retry: false,
  });
}

export function useStartRisk(patientId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => riskService.start(jobId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: riskKeys.all });
      queryClient.invalidateQueries({ queryKey: nerKeys.all });
      queryClient.invalidateQueries({ queryKey: registrationKeys.all });
      queryClient.invalidateQueries({ queryKey: ocrKeys.all });
      if (patientId) {
        queryClient.invalidateQueries({
          queryKey: ocrKeys.context(patientId),
        });
      }
      toast.success(
        `Risk profile: ${result.overall_level} (${result.overall_score.toFixed(0)}) — next: ${result.next_stage}`,
      );
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Risk profiling failed'));
    },
  });
}
