import apiClient from '@/services/apiClient';
import type {
  PatientRegistrationResult,
  ProcessingJob,
} from '@/types/registration';

export const intakeRegistrationService = {
  async register(params: {
    patient_id: string;
    appointment_id: string;
    doctor_id: string;
    file: File;
  }): Promise<PatientRegistrationResult> {
    const form = new FormData();
    form.append('patient_id', params.patient_id);
    form.append('appointment_id', params.appointment_id);
    form.append('doctor_id', params.doctor_id);
    form.append('uploaded_document', params.file);

    const { data } = await apiClient.post<PatientRegistrationResult>(
      '/ai/intake/register',
      form,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      },
    );
    return data;
  },

  async getJob(jobId: string): Promise<ProcessingJob> {
    const { data } = await apiClient.get<ProcessingJob>(
      `/ai/intake/jobs/${jobId}`,
    );
    return data;
  },

  async listJobs(patientId?: string): Promise<ProcessingJob[]> {
    const { data } = await apiClient.get<ProcessingJob[]>('/ai/intake/jobs', {
      params: patientId ? { patient_id: patientId } : undefined,
    });
    return data;
  },
};
