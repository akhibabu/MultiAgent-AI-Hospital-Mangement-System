import apiClient from '@/services/apiClient';
import type { RiskProfile, RiskStartResult, RiskStatus } from '@/types/risk';

export const riskService = {
  async start(jobId: string): Promise<RiskStartResult> {
    const { data } = await apiClient.post<RiskStartResult>('/ai/intake/risk/start', {
      job_id: jobId,
    });
    return data;
  },

  async status(jobId: string): Promise<RiskStatus> {
    const { data } = await apiClient.get<RiskStatus>(
      `/ai/intake/risk/status/${jobId}`,
    );
    return data;
  },

  async result(jobId: string): Promise<RiskProfile> {
    const { data } = await apiClient.get<RiskProfile>(
      `/ai/intake/risk/result/${jobId}`,
    );
    return data;
  },
};
