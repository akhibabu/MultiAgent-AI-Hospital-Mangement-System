import apiClient from '@/services/apiClient';
import type {
  KnowledgeGraph,
  KnowledgeGraphStartResult,
} from '@/types/knowledgeGraph';

export const knowledgeGraphService = {
  async start(jobId: string): Promise<KnowledgeGraphStartResult> {
    const { data } = await apiClient.post<KnowledgeGraphStartResult>(
      '/ai/intake/kg/start',
      { job_id: jobId },
    );
    return data;
  },

  async result(jobId: string): Promise<KnowledgeGraph> {
    const { data } = await apiClient.get<KnowledgeGraph>(
      `/ai/intake/kg/result/${jobId}`,
    );
    return data;
  },

  async forPatient(patientId: string): Promise<KnowledgeGraph> {
    const { data } = await apiClient.get<KnowledgeGraph>(
      `/ai/intake/patients/${patientId}/knowledge-graph`,
    );
    return data;
  },
};
