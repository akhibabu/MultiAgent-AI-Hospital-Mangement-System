import apiClient from '@/services/apiClient';
import type {
  DiagnosisHistoryItem,
  DiagnosisResult,
  DiagnosisStartResult,
} from '@/types/diagnosis';

export const diagnosisService = {
  async start(
    patientId: string,
    options?: { chief_complaint?: string; focus_symptoms?: string[] },
  ): Promise<DiagnosisStartResult> {
    const { data } = await apiClient.post<DiagnosisStartResult>(
      '/ai/diagnosis/start',
      {
        patient_id: patientId,
        chief_complaint: options?.chief_complaint,
        focus_symptoms: options?.focus_symptoms ?? [],
      },
    );
    return data;
  },

  async result(patientId: string): Promise<DiagnosisResult> {
    const { data } = await apiClient.get<DiagnosisResult>(
      `/ai/diagnosis/${patientId}`,
    );
    return data;
  },

  async history(patientId: string, limit = 20): Promise<DiagnosisHistoryItem[]> {
    const { data } = await apiClient.get<DiagnosisHistoryItem[]>(
      `/ai/diagnosis/${patientId}/history`,
      { params: { limit } },
    );
    return data;
  },
};
