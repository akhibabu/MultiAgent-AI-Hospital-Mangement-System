import apiClient from '@/services/apiClient';
import type {
  AIHealth,
  CacheInvalidation,
  CacheStats,
  OrchestratorLogs,
  OrchestratorStats,
  OrchestratorStatus,
  ProviderFleet,
  QueueStatus,
} from '@/types/aiOrchestrator';

export const aiOrchestratorService = {
  async status(): Promise<OrchestratorStatus> {
    const { data } = await apiClient.get<OrchestratorStatus>('/ai/orchestrator/status');
    return data;
  },

  async health(): Promise<AIHealth> {
    const { data } = await apiClient.get<AIHealth>('/ai/health');
    return data;
  },

  /** Provider fleet: config, priority, live health, and failover history. */
  async providers(): Promise<ProviderFleet> {
    const { data } = await apiClient.get<ProviderFleet>('/ai/orchestrator/providers');
    return data;
  },

  /** Clear a provider's cooldown and put it back in rotation. */
  async resetProvider(name: string): Promise<ProviderFleet> {
    const { data } = await apiClient.post<ProviderFleet>(
      `/ai/orchestrator/providers/${encodeURIComponent(name)}/reset`,
    );
    return data;
  },

  /** Re-read providers.yaml without restarting the backend. */
  async reloadProviders(): Promise<ProviderFleet> {
    const { data } = await apiClient.post<ProviderFleet>('/ai/orchestrator/providers/reload');
    return data;
  },

  async queue(): Promise<QueueStatus> {
    const { data } = await apiClient.get<QueueStatus>('/ai/orchestrator/queue');
    return data;
  },

  async cancelRequest(requestId: string): Promise<QueueStatus> {
    const { data } = await apiClient.post<QueueStatus>(
      `/ai/orchestrator/queue/${encodeURIComponent(requestId)}/cancel`,
    );
    return data;
  },

  async cacheStats(): Promise<CacheStats> {
    const { data } = await apiClient.get<CacheStats>('/ai/orchestrator/cache');
    return data;
  },

  /** Invalidate cached AI responses — all, one agent's, or one patient's. */
  async invalidateCache(params?: {
    agent?: string;
    patientId?: string;
  }): Promise<CacheInvalidation> {
    const { data } = await apiClient.delete<CacheInvalidation>('/ai/orchestrator/cache', {
      params: { agent: params?.agent, patient_id: params?.patientId },
    });
    return data;
  },

  async stats(window = 1000): Promise<OrchestratorStats> {
    const { data } = await apiClient.get<OrchestratorStats>('/ai/orchestrator/stats', {
      params: { window },
    });
    return data;
  },

  async logs(limit = 50): Promise<OrchestratorLogs> {
    const { data } = await apiClient.get<OrchestratorLogs>('/ai/orchestrator/logs', {
      params: { limit },
    });
    return data;
  },
};
