import apiClient, { AI_AGENT_TIMEOUT_MS } from '@/services/apiClient';
import type {
  ResearchHistoryItem,
  ResearchResult,
  ResearchStartResult,
} from '@/types/research';

export const researchService = {
  async start(
    patientId: string,
    diagnosisResultId?: string,
  ): Promise<ResearchStartResult> {
    const { data } = await apiClient.post<ResearchStartResult>(
      '/ai/research/start',
      {
        patient_id: patientId,
        diagnosis_result_id: diagnosisResultId,
      },
      { timeout: AI_AGENT_TIMEOUT_MS },
    );
    return data;
  },

  async result(patientId: string): Promise<ResearchResult> {
    const { data } = await apiClient.get<ResearchResult>(
      `/ai/research/${patientId}`,
    );
    return data;
  },

  async history(patientId: string, limit = 20): Promise<ResearchHistoryItem[]> {
    const { data } = await apiClient.get<ResearchHistoryItem[]>(
      `/ai/research/${patientId}/history`,
      { params: { limit } },
    );
    return data;
  },
};
