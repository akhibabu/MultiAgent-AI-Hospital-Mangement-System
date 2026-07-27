import apiClient from '@/services/apiClient';
import type {
  DocumentProcessingJob,
  IntakeDashboard,
  IntakeProcessResult,
  KnowledgeGraphPreview,
  PatientAIContext,
} from '@/types/intake';

export const intakeService = {
  async processDocument(documentId: string): Promise<IntakeProcessResult> {
    const { data } = await apiClient.post<IntakeProcessResult>(
      '/ai/intake/process',
      { document_id: documentId },
    );
    return data;
  },

  async getDashboard(patientId: string): Promise<IntakeDashboard> {
    const { data } = await apiClient.get<IntakeDashboard>(
      `/ai/intake/patients/${patientId}/dashboard`,
    );
    return data;
  },

  async getContext(patientId: string): Promise<PatientAIContext> {
    const { data } = await apiClient.get<PatientAIContext>(
      `/ai/intake/patients/${patientId}/context`,
    );
    return data;
  },

  async getAgentInput(patientId: string): Promise<Record<string, unknown>> {
    const { data } = await apiClient.get<Record<string, unknown>>(
      `/ai/intake/patients/${patientId}/agent-input`,
    );
    return data;
  },

  async getKnowledgeGraph(patientId: string): Promise<KnowledgeGraphPreview> {
    const { data } = await apiClient.get<KnowledgeGraphPreview>(
      `/ai/intake/patients/${patientId}/knowledge-graph`,
    );
    return data;
  },

  async listJobs(patientId?: string): Promise<{
    items: DocumentProcessingJob[];
    total: number;
  }> {
    const { data } = await apiClient.get<{
      items: DocumentProcessingJob[];
      total: number;
    }>('/ai/intake/jobs', {
      params: patientId ? { patient_id: patientId } : undefined,
    });
    return data;
  },

  async getJob(jobId: string): Promise<DocumentProcessingJob> {
    const { data } = await apiClient.get<DocumentProcessingJob>(
      `/ai/intake/jobs/${jobId}`,
    );
    return data;
  },
};
