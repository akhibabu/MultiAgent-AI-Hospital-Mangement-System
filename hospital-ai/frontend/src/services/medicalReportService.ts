import apiClient from '@/services/apiClient';
import type {
  GeneratedMedicalReport,
  MedicalReportHistoryItem,
  MedicalReportStartResult,
  MedicalReportStatus,
} from '@/types/medicalReport';

export const medicalReportService = {
  async start(
    patientId: string,
    options?: {
      diagnosis_result_id?: string;
      research_result_id?: string;
      prescription_result_id?: string;
      receiving_specialist?: string;
    },
  ): Promise<MedicalReportStartResult> {
    const { data } = await apiClient.post<MedicalReportStartResult>(
      '/ai/report/start',
      {
        patient_id: patientId,
        diagnosis_result_id: options?.diagnosis_result_id,
        research_result_id: options?.research_result_id,
        prescription_result_id: options?.prescription_result_id,
        receiving_specialist: options?.receiving_specialist,
      },
    );
    return data;
  },

  async result(patientId: string): Promise<GeneratedMedicalReport> {
    const { data } = await apiClient.get<GeneratedMedicalReport>(
      `/ai/report/${patientId}`,
    );
    return data;
  },

  async status(patientId: string): Promise<MedicalReportStatus> {
    const { data } = await apiClient.get<MedicalReportStatus>(
      `/ai/report/status/${patientId}`,
    );
    return data;
  },

  async history(patientId: string, limit = 20): Promise<MedicalReportHistoryItem[]> {
    const { data } = await apiClient.get<MedicalReportHistoryItem[]>(
      `/ai/report/${patientId}/history`,
      { params: { limit } },
    );
    return data;
  },
};
