import apiClient from '@/services/apiClient';
import type {
  InsuranceHistoryItem,
  InsuranceResult,
  InsuranceStartRequest,
  InsuranceStartResponse,
} from '@/types/insurance';

export const insuranceService = {
  async start(payload: InsuranceStartRequest): Promise<InsuranceStartResponse> {
    const { data } = await apiClient.post<InsuranceStartResponse>(
      '/ai/insurance/start',
      payload,
    );
    return data;
  },

  async result(patientId: string): Promise<InsuranceResult> {
    const { data } = await apiClient.get<InsuranceResult>(
      '/ai/insurance/' + patientId,
    );
    return data;
  },

  async history(patientId: string): Promise<InsuranceHistoryItem[]> {
    const { data } = await apiClient.get<InsuranceHistoryItem[]>(
      '/ai/insurance/' + patientId + '/history',
    );
    return data;
  },
};
