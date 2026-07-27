import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { isAxiosError } from 'axios';
import { intakeRegistrationService } from '@/services/intakeRegistrationService';

export const registrationKeys = {
  all: ['intake-registration'] as const,
  jobs: (patientId?: string) =>
    [...registrationKeys.all, 'jobs', patientId || 'all'] as const,
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

export function useRegisterForProcessing() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: intakeRegistrationService.register,
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: registrationKeys.all });
      toast.success(
        `Registered — Job ${result.job_id.slice(0, 8)}… ready for ${result.next_stage}`,
      );
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Patient Registration failed'));
    },
  });
}

export function useProcessingJobs(patientId?: string) {
  return useQuery({
    queryKey: registrationKeys.jobs(patientId),
    queryFn: () => intakeRegistrationService.listJobs(patientId),
  });
}
