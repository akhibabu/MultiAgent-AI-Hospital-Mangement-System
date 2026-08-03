import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { isAxiosError } from 'axios';
import { medicalReportService } from '@/services/medicalReportService';

export const medicalReportKeys = {
  all: ['medical-report'] as const,
  result: (patientId: string) => [...medicalReportKeys.all, 'result', patientId] as const,
  status: (patientId: string) => [...medicalReportKeys.all, 'status', patientId] as const,
  history: (patientId: string) => [...medicalReportKeys.all, 'history', patientId] as const,
};

function getErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item?.msg || JSON.stringify(item)).join(', ');
    }
  }
  if (error instanceof Error) return error.message;
  return fallback;
}

export function useMedicalReportResult(patientId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: medicalReportKeys.result(patientId || ''),
    queryFn: () => medicalReportService.result(patientId!),
    enabled: Boolean(patientId) && enabled,
    retry: false,
  });
}

export function useMedicalReportStatus(patientId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: medicalReportKeys.status(patientId || ''),
    queryFn: () => medicalReportService.status(patientId!),
    enabled: Boolean(patientId) && enabled,
    retry: false,
  });
}

export function useMedicalReportHistory(patientId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: medicalReportKeys.history(patientId || ''),
    queryFn: () => medicalReportService.history(patientId!),
    enabled: Boolean(patientId) && enabled,
    retry: false,
  });
}

export function useStartMedicalReport(patientId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (options?: {
      diagnosis_result_id?: string;
      research_result_id?: string;
      prescription_result_id?: string;
      receiving_specialist?: string;
    }) => medicalReportService.start(patientId!, options),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: medicalReportKeys.all });
      toast.success('Medical Report Agent completed — review before use in an official record.');
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Medical Report Agent failed'));
    },
  });
}
