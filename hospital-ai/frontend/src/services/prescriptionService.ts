import apiClient from '@/services/apiClient';
import type {
  PrescriptionHistoryItem,
  PrescriptionResult,
  PrescriptionStartResult,
  PrescriptionStatus,
} from '@/types/prescription';

export const prescriptionService = {
  async start(
    patientId: string,
    options?: { diagnosis_result_id?: string; research_result_id?: string },
  ): Promise<PrescriptionStartResult> {
    const { data } = await apiClient.post<PrescriptionStartResult>(
      '/ai/prescription/start',
      {
        patient_id: patientId,
        diagnosis_result_id: options?.diagnosis_result_id,
        research_result_id: options?.research_result_id,
      },
    );
    return data;
  },

  async result(patientId: string): Promise<PrescriptionResult> {
    const { data } = await apiClient.get<PrescriptionResult>(
      `/ai/prescription/${patientId}`,
    );
    return data;
  },

  async status(patientId: string): Promise<PrescriptionStatus> {
    const { data } = await apiClient.get<PrescriptionStatus>(
      `/ai/prescription/status/${patientId}`,
    );
    return data;
  },

  async history(patientId: string, limit = 20): Promise<PrescriptionHistoryItem[]> {
    const { data } = await apiClient.get<PrescriptionHistoryItem[]>(
      `/ai/prescription/${patientId}/history`,
      { params: { limit } },
    );
    return data;
  },
};
