import apiClient, { AI_AGENT_TIMEOUT_MS } from '@/services/apiClient';
import type { EmergencyResult, EmergencyStartResult } from '@/types/emergency';

export const emergencyService = {
  async start(patientId: string): Promise<EmergencyStartResult> {
    const { data } = await apiClient.post<EmergencyStartResult>(
      '/ai/emergency/start',
      { patient_id: patientId },
      { timeout: AI_AGENT_TIMEOUT_MS },
    );
    return data;
  },
  async result(patientId: string): Promise<EmergencyResult> {
    const { data } = await apiClient.get<EmergencyResult>(
      `/ai/emergency/${patientId}`,
    );
    return data;
  },
  async history(patientId: string, limit = 20) {
    const { data } = await apiClient.get(
      `/ai/emergency/${patientId}/history`,
      { params: { limit } },
    );
    return data;
  },
};
