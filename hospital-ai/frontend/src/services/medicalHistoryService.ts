import apiClient, { AI_AGENT_TIMEOUT_MS } from '@/services/apiClient';
import type { MedicalHistoryResponse } from '@/types/medicalHistory';

export const medicalHistoryService = {
  async get(patientId: string): Promise<MedicalHistoryResponse> {
    const { data } = await apiClient.get<MedicalHistoryResponse>(
      `/ai/intake/history/${patientId}`,
    );
    return data;
  },

  async extract(jobId: string): Promise<MedicalHistoryResponse> {
    const { data } = await apiClient.post<MedicalHistoryResponse>(
      '/ai/intake/history/extract',
      { job_id: jobId },
      { timeout: AI_AGENT_TIMEOUT_MS },
    );
    return data;
  },

  async getAndExtract(
    patientId: string,
    jobId?: string,
  ): Promise<MedicalHistoryResponse> {
    const { data } = await apiClient.get<MedicalHistoryResponse>(
      `/ai/intake/history/${patientId}`,
      {
        params: {
          extract: true,
          ...(jobId ? { job_id: jobId } : {}),
        },
      },
    );
    return data;
  },
};
