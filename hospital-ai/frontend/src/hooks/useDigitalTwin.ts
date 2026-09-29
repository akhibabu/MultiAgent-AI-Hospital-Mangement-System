import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { getApiErrorMessage } from '@/services/apiClient';
import { digitalTwinService } from '@/services/digitalTwinService';
import type { DigitalTwinScenario } from '@/types/digitalTwin';

export const digitalTwinKeys = {
  all: ['digital-twin'] as const,
  state: () => ['digital-twin', 'state'] as const,
  latest: () => ['digital-twin', 'latest'] as const,
  history: () => ['digital-twin', 'history'] as const,
};

export function useDigitalTwinState() {
  return useQuery({
    queryKey: digitalTwinKeys.state(),
    queryFn: digitalTwinService.state,
    refetchInterval: 30_000,
  });
}

export function useDigitalTwinLatest() {
  return useQuery({
    queryKey: digitalTwinKeys.latest(),
    queryFn: digitalTwinService.latest,
    retry: false,
  });
}

export function useDigitalTwinHistory() {
  return useQuery({
    queryKey: digitalTwinKeys.history(),
    queryFn: () => digitalTwinService.history(20),
  });
}

export function useSimulateDigitalTwin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DigitalTwinScenario) => digitalTwinService.simulate(payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: digitalTwinKeys.latest() });
      queryClient.invalidateQueries({ queryKey: digitalTwinKeys.history() });
      queryClient.invalidateQueries({ queryKey: digitalTwinKeys.state() });
      toast.success(
        data.simulation.bottlenecks.length
          ? 'Digital Twin simulation completed with bottlenecks to review.'
          : 'Digital Twin simulation completed.',
      );
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Digital Twin simulation failed')),
  });
}
