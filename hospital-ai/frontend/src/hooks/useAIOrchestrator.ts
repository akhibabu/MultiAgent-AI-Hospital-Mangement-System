import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { aiOrchestratorService } from '@/services/aiOrchestratorService';

export const aiOrchestratorKeys = {
  all: ['ai-orchestrator'] as const,
  status: () => [...aiOrchestratorKeys.all, 'status'] as const,
  health: () => [...aiOrchestratorKeys.all, 'health'] as const,
  providers: () => [...aiOrchestratorKeys.all, 'providers'] as const,
  queue: () => [...aiOrchestratorKeys.all, 'queue'] as const,
  cache: () => [...aiOrchestratorKeys.all, 'cache'] as const,
  stats: () => [...aiOrchestratorKeys.all, 'stats'] as const,
  logs: () => [...aiOrchestratorKeys.all, 'logs'] as const,
};

/** Live provider/model health — polled so an admin sees failover as it happens. */
export function useOrchestratorStatus() {
  return useQuery({
    queryKey: aiOrchestratorKeys.status(),
    queryFn: () => aiOrchestratorService.status(),
    refetchInterval: 30_000,
  });
}

/** `GET /ai/health` — fleet-wide AI infrastructure health check. */
export function useAIHealth() {
  return useQuery({
    queryKey: aiOrchestratorKeys.health(),
    queryFn: () => aiOrchestratorService.health(),
    refetchInterval: 30_000,
  });
}

/** Provider fleet + failover history. */
export function useProviderFleet() {
  return useQuery({
    queryKey: aiOrchestratorKeys.providers(),
    queryFn: () => aiOrchestratorService.providers(),
    refetchInterval: 15_000,
  });
}

/**
 * Live request queue. Polled fast because this is the one panel an operator
 * watches in real time to see whether work is moving.
 */
export function useAIRequestQueue() {
  return useQuery({
    queryKey: aiOrchestratorKeys.queue(),
    queryFn: () => aiOrchestratorService.queue(),
    refetchInterval: 5_000,
  });
}

export function useAICacheStats() {
  return useQuery({
    queryKey: aiOrchestratorKeys.cache(),
    queryFn: () => aiOrchestratorService.cacheStats(),
    refetchInterval: 30_000,
  });
}

export function useOrchestratorStats() {
  return useQuery({
    queryKey: aiOrchestratorKeys.stats(),
    queryFn: () => aiOrchestratorService.stats(),
    refetchInterval: 30_000,
  });
}

export function useOrchestratorLogs(limit = 50) {
  return useQuery({
    queryKey: aiOrchestratorKeys.logs(),
    queryFn: () => aiOrchestratorService.logs(limit),
    refetchInterval: 30_000,
  });
}

/** Clear a provider's cooldown after fixing the underlying cause. */
export function useResetProvider() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => aiOrchestratorService.resetProvider(name),
    onSuccess: (data) => {
      queryClient.setQueryData(aiOrchestratorKeys.providers(), data);
      queryClient.invalidateQueries({ queryKey: aiOrchestratorKeys.health() });
      queryClient.invalidateQueries({ queryKey: aiOrchestratorKeys.status() });
    },
  });
}

/** Re-read providers.yaml without a backend restart. */
export function useReloadProviders() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => aiOrchestratorService.reloadProviders(),
    onSuccess: (data) => {
      queryClient.setQueryData(aiOrchestratorKeys.providers(), data);
      queryClient.invalidateQueries({ queryKey: aiOrchestratorKeys.all });
    },
  });
}

export function useInvalidateAICache() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params?: { agent?: string; patientId?: string }) =>
      aiOrchestratorService.invalidateCache(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiOrchestratorKeys.cache() });
    },
  });
}

export function useCancelAIRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (requestId: string) => aiOrchestratorService.cancelRequest(requestId),
    onSuccess: (data) => {
      queryClient.setQueryData(aiOrchestratorKeys.queue(), data);
    },
  });
}
