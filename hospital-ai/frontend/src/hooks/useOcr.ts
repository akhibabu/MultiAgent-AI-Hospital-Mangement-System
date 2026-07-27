import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { isAxiosError } from 'axios';
import { ocrService } from '@/services/ocrService';
import { medicalHistoryKeys } from '@/hooks/useMedicalHistory';
import { registrationKeys } from '@/hooks/useRegistration';

export const ocrKeys = {
  all: ['intake-ocr'] as const,
  status: (jobId: string) => [...ocrKeys.all, 'status', jobId] as const,
  result: (jobId: string) => [...ocrKeys.all, 'result', jobId] as const,
  context: (patientId: string) => [...ocrKeys.all, 'context', patientId] as const,
};

function getErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => item?.msg || JSON.stringify(item))
        .join(', ');
    }
  }
  if (error instanceof Error) return error.message;
  return fallback;
}

export function useOcrStatus(jobId: string | undefined) {
  return useQuery({
    queryKey: ocrKeys.status(jobId || ''),
    queryFn: () => ocrService.status(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (q) =>
      q.state.data?.current_stage === 'OCR' && q.state.data?.status === 'Processing'
        ? 3000
        : false,
  });
}

export function useOcrResult(jobId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ocrKeys.result(jobId || ''),
    queryFn: () => ocrService.result(jobId!),
    enabled: Boolean(jobId) && enabled,
    retry: false,
  });
}

export function usePatientContext(patientId: string | undefined) {
  return useQuery({
    queryKey: ocrKeys.context(patientId || ''),
    queryFn: () => ocrService.getContext(patientId!),
    enabled: Boolean(patientId),
    retry: false,
  });
}

export function useStartOcr(patientId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => ocrService.start(jobId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ocrKeys.all });
      queryClient.invalidateQueries({ queryKey: registrationKeys.all });
      if (patientId) {
        queryClient.invalidateQueries({
          queryKey: medicalHistoryKeys.patient(patientId),
        });
        queryClient.invalidateQueries({
          queryKey: ocrKeys.context(patientId),
        });
      }
      toast.success(
        `OCR complete (${result.provider}) — next: ${result.next_stage}`,
      );
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'OCR failed'));
    },
  });
}
