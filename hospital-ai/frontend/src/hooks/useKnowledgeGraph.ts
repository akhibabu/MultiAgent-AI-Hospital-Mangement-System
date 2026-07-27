import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { isAxiosError } from 'axios';
import { knowledgeGraphService } from '@/services/knowledgeGraphService';
import { riskKeys } from '@/hooks/useRisk';
import { nerKeys } from '@/hooks/useNer';
import { ocrKeys } from '@/hooks/useOcr';
import { registrationKeys } from '@/hooks/useRegistration';

export const kgKeys = {
  all: ['intake-kg'] as const,
  result: (jobId: string) => [...kgKeys.all, 'result', jobId] as const,
  patient: (patientId: string) => [...kgKeys.all, 'patient', patientId] as const,
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

export function useKnowledgeGraphResult(jobId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: kgKeys.result(jobId || ''),
    queryFn: () => knowledgeGraphService.result(jobId!),
    enabled: Boolean(jobId) && enabled,
    retry: false,
  });
}

export function useStartKnowledgeGraph(patientId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => knowledgeGraphService.start(jobId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: kgKeys.all });
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
        `Knowledge graph ready — ${result.node_count} nodes, ${result.relationship_count} links. Intake complete.`,
      );
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Knowledge graph creation failed'));
    },
  });
}
