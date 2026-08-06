import apiClient, { AI_AGENT_TIMEOUT_MS } from '@/services/apiClient';
import type {
  KnowledgeGraph,
  KnowledgeGraphStartResult,
} from '@/types/knowledgeGraph';

export const knowledgeGraphService = {
  async start(jobId: string): Promise<KnowledgeGraphStartResult> {
    // KG build is synchronous on the server and can take well over the
    // default 15s CRUD timeout when Supabase is slow or the graph is large —
    // Diagnosis/Research already use this longer budget for the same reason.
    const { data } = await apiClient.post<KnowledgeGraphStartResult>(
      '/ai/intake/kg/start',
      { job_id: jobId },
      { timeout: AI_AGENT_TIMEOUT_MS },
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
