import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { knowledgeGraphService } from '@/services/knowledgeGraphService';
import { getApiErrorMessage } from '@/services/apiClient';
import { riskKeys } from '@/hooks/useRisk';
import { nerKeys } from '@/hooks/useNer';
import { ocrKeys } from '@/hooks/useOcr';
import { registrationKeys } from '@/hooks/useRegistration';

export const kgKeys = {
  all: ['intake-kg'] as const,
  result: (jobId: string) => [...kgKeys.all, 'result', jobId] as const,
  patient: (patientId: string) => [...kgKeys.all, 'patient', patientId] as const,
};

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
      // A client timeout does not mean the backend failed — KG builds often
      // finish after axios aborts. Invalidate so the next result poll can
      // pick up a graph that landed in the background.
      queryClient.invalidateQueries({ queryKey: kgKeys.all });
      toast.error(getApiErrorMessage(error, 'Knowledge graph creation failed'));
    },
  });
}
