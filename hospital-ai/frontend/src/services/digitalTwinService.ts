import apiClient from '@/services/apiClient';
import type {
  DigitalTwinHistoryItem,
  DigitalTwinRun,
  DigitalTwinScenario,
  DigitalTwinStateResponse,
} from '@/types/digitalTwin';

export const digitalTwinService = {
  async state(): Promise<DigitalTwinStateResponse> {
    const { data } = await apiClient.get<DigitalTwinStateResponse>('/ai/digital-twin/state');
    return data;
  },

  async simulate(payload: DigitalTwinScenario): Promise<DigitalTwinRun> {
    const { data } = await apiClient.post<DigitalTwinRun>('/ai/digital-twin/simulate', payload, {
      timeout: 10 * 60 * 1000,
    });
    return data;
  },

  async latest(): Promise<DigitalTwinRun> {
    const { data } = await apiClient.get<DigitalTwinRun>('/ai/digital-twin/latest');
    return data;
  },

  async history(limit = 20): Promise<DigitalTwinHistoryItem[]> {
    const { data } = await apiClient.get<DigitalTwinHistoryItem[]>('/ai/digital-twin/history', {
      params: { limit },
    });
    return data;
  },
};
