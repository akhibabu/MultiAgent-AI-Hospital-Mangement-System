import apiClient, { AI_AGENT_TIMEOUT_MS } from '@/services/apiClient';
import type {
  MedicalEntity,
  NERResult,
  NERStartResult,
  NERStatus,
} from '@/types/ner';

export const nerService = {
  async start(jobId: string): Promise<NERStartResult> {
    const { data } = await apiClient.post<NERStartResult>(
      '/ai/intake/ner/start',
      { job_id: jobId },
      { timeout: AI_AGENT_TIMEOUT_MS },
    );
    return data;
  },

  async status(jobId: string): Promise<NERStatus> {
    const { data } = await apiClient.get<NERStatus>(
      `/ai/intake/ner/status/${jobId}`,
    );
    return data;
  },

  async result(jobId: string): Promise<NERResult> {
    const { data } = await apiClient.get<NERResult>(
      `/ai/intake/ner/result/${jobId}`,
    );
    return data;
  },

  async entities(jobId: string): Promise<MedicalEntity[]> {
    const { data } = await apiClient.get<MedicalEntity[]>(
      `/ai/intake/ner/entities/${jobId}`,
    );
    return data;
  },
};
