import apiClient from '@/services/apiClient';
import type {
  ResourceAllocationResult,
  ResourceAllocationStartResult,
} from '@/types/resourceAllocation';

export interface ResourceAllocationRequest {
  patient_id: string;
}

export const resourceAllocationService = {
  async start(payload: ResourceAllocationRequest): Promise<ResourceAllocationStartResult> {
    const { data } = await apiClient.post<ResourceAllocationStartResult>(
      '/ai/resource-allocation/start',
      payload,
    );
    return data;
  },

  async result(patientId: string): Promise<ResourceAllocationResult> {
    const { data } = await apiClient.get<ResourceAllocationResult>(
      '/ai/resource-allocation/' + patientId,
    );
    return data;
  },
};
