import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { isAxiosError } from 'axios';
import { medicalHistoryService } from '@/services/medicalHistoryService';

export const medicalHistoryKeys = {
  all: ['medical-history'] as const,
  patient: (patientId: string) =>
    [...medicalHistoryKeys.all, patientId] as const,
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

export function useMedicalHistory(patientId: string | undefined) {
  return useQuery({
    queryKey: medicalHistoryKeys.patient(patientId || ''),
    queryFn: () => medicalHistoryService.get(patientId!),
    enabled: Boolean(patientId),
  });
}

export function useExtractMedicalHistory(patientId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => medicalHistoryService.extract(jobId),
    onSuccess: (result) => {
      if (patientId) {
        queryClient.setQueryData(
          medicalHistoryKeys.patient(patientId),
          result,
        );
      }
      toast.success(
        `History extracted — stage advanced to ${result.current_stage}`,
      );
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Medical history extraction failed'));
    },
  });
}
