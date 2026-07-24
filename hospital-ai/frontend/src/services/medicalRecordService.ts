import apiClient from '@/services/apiClient';
import type {
  MedicalDocument,
  MedicalRecord,
  MedicalRecordAudit,
  MedicalRecordFormValues,
  MedicalRecordListParams,
  MedicalRecordListResponse,
} from '@/types/medicalRecord';

function cleanPayload(values: MedicalRecordFormValues) {
  return {
    patient_id: values.patient_id,
    appointment_id: values.appointment_id || null,
    doctor_id: values.doctor_id || null,
    record_type: values.record_type,
    title: values.title.trim(),
    description: values.description.trim() || null,
    diagnosis: values.diagnosis.trim() || null,
    treatment: values.treatment.trim() || null,
    notes: values.notes.trim() || null,
  };
}

export const medicalRecordService = {
  async list(
    params: MedicalRecordListParams = {},
  ): Promise<MedicalRecordListResponse> {
    const { data } = await apiClient.get<MedicalRecordListResponse>(
      '/medical-records',
      {
        params: {
          page: params.page ?? 1,
          page_size: params.page_size ?? 10,
          search: params.search || undefined,
          patient_id: params.patient_id || undefined,
          doctor_id: params.doctor_id || undefined,
          appointment_id: params.appointment_id || undefined,
          record_type: params.record_type || undefined,
          date_from: params.date_from || undefined,
          date_to: params.date_to || undefined,
          sort_by: params.sort_by ?? 'created_at',
          sort_order: params.sort_order ?? 'desc',
        },
      },
    );
    return data;
  },

  async getById(id: string): Promise<MedicalRecord> {
    const { data } = await apiClient.get<MedicalRecord>(
      `/medical-records/${id}`,
    );
    return data;
  },

  async create(values: MedicalRecordFormValues): Promise<MedicalRecord> {
    const { data } = await apiClient.post<MedicalRecord>(
      '/medical-records',
      cleanPayload(values),
    );
    return data;
  },

  async update(
    id: string,
    values: MedicalRecordFormValues,
  ): Promise<MedicalRecord> {
    const { data } = await apiClient.put<MedicalRecord>(
      `/medical-records/${id}`,
      cleanPayload(values),
    );
    return data;
  },

  async remove(id: string): Promise<void> {
    await apiClient.delete(`/medical-records/${id}`);
  },

  async upload(
    medicalRecordId: string,
    file: File,
    onProgress?: (pct: number) => void,
  ): Promise<MedicalDocument> {
    const form = new FormData();
    form.append('medical_record_id', medicalRecordId);
    form.append('file', file);
    const { data } = await apiClient.post<MedicalDocument>(
      '/medical-records/upload',
      form,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (evt) => {
          if (!onProgress || !evt.total) return;
          onProgress(Math.round((evt.loaded / evt.total) * 100));
        },
      },
    );
    return data;
  },

  async uploadMany(
    medicalRecordId: string,
    files: File[],
  ): Promise<MedicalDocument[]> {
    const form = new FormData();
    form.append('medical_record_id', medicalRecordId);
    files.forEach((f) => form.append('files', f));
    const { data } = await apiClient.post<MedicalDocument[]>(
      '/medical-records/upload-many',
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );
    return data;
  },

  async getFile(documentId: string): Promise<MedicalDocument> {
    const { data } = await apiClient.get<MedicalDocument>(
      `/medical-records/files/${documentId}`,
    );
    return data;
  },

  async deleteFile(documentId: string): Promise<void> {
    await apiClient.delete(`/medical-records/files/${documentId}`);
  },

  async listAudit(
    recordId: string,
  ): Promise<{ items: MedicalRecordAudit[]; total: number }> {
    const { data } = await apiClient.get<{
      items: MedicalRecordAudit[];
      total: number;
    }>(`/medical-records/${recordId}/audit`);
    return data;
  },
};
