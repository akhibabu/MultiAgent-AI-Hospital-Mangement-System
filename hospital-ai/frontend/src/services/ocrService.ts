import apiClient from '@/services/apiClient';
import type {
  OCRResult,
  OCRStartResult,
  OCRStatus,
  PatientContextView,
} from '@/types/ocr';

export const ocrService = {
  async start(jobId: string): Promise<OCRStartResult> {
    const { data } = await apiClient.post<OCRStartResult>('/ai/intake/ocr/start', {
      job_id: jobId,
    });
    return data;
  },

  async status(jobId: string): Promise<OCRStatus> {
    const { data } = await apiClient.get<OCRStatus>(
      `/ai/intake/ocr/status/${jobId}`,
    );
    return data;
  },

  async result(jobId: string): Promise<OCRResult> {
    const { data } = await apiClient.get<OCRResult>(
      `/ai/intake/ocr/result/${jobId}`,
    );
    return data;
  },

  async getContext(patientId: string): Promise<PatientContextView> {
    const { data } = await apiClient.get<PatientContextView>(
      `/ai/intake/context/${patientId}`,
    );
    return data;
  },
};
