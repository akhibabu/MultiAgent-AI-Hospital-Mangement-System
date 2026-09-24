import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { getApiErrorMessage } from '@/services/apiClient';
import {
  resourceAllocationService,
  type ResourceAllocationRequest,
} from '@/services/resourceAllocationService';

export const resourceAllocationKeys = {
  all: ['resource-allocation'] as const,
  result: (patientId: string) => ['resource-allocation', 'result', patientId] as const,
};

export function useResourceAllocationResult(patientId: string | undefined) {
  return useQuery({
    queryKey: resourceAllocationKeys.result(patientId || ''),
    queryFn: () => resourceAllocationService.result(patientId!),
    enabled: Boolean(patientId),
    retry: false,
  });
}

export function useStartResourceAllocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ResourceAllocationRequest) =>
      resourceAllocationService.start(payload),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: resourceAllocationKeys.all });
      toast.success(
        data.conflicts.length
          ? 'Resource Allocation Agent completed with conflicts to review.'
          : 'Resource Allocation Agent completed.',
      );
    },
    onError: (error) =>
      toast.error(getApiErrorMessage(error, 'Resource Allocation Agent failed')),
  });
}
