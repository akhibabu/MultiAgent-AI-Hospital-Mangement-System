import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { isAxiosError } from 'axios';
import { medicalRecordService } from '@/services/medicalRecordService';
import type {
  MedicalRecordFormValues,
  MedicalRecordListParams,
} from '@/types/medicalRecord';

export const medicalRecordKeys = {
  all: ['medical-records'] as const,
  lists: () => [...medicalRecordKeys.all, 'list'] as const,
  list: (params: MedicalRecordListParams) =>
    [...medicalRecordKeys.lists(), params] as const,
  details: () => [...medicalRecordKeys.all, 'detail'] as const,
  detail: (id: string) => [...medicalRecordKeys.details(), id] as const,
  audit: (id: string) => [...medicalRecordKeys.all, 'audit', id] as const,
  file: (id: string) => [...medicalRecordKeys.all, 'file', id] as const,
};

function errMsg(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
  }
  if (error instanceof Error) return error.message;
  return fallback;
}

export function useMedicalRecords(params: MedicalRecordListParams) {
  return useQuery({
    queryKey: medicalRecordKeys.list(params),
    queryFn: () => medicalRecordService.list(params),
    placeholderData: (prev) => prev,
  });
}

export function useMedicalRecord(id: string | undefined) {
  return useQuery({
    queryKey: medicalRecordKeys.detail(id || ''),
    queryFn: () => medicalRecordService.getById(id!),
    enabled: Boolean(id),
  });
}

export function useMedicalRecordAudit(id: string | undefined) {
  return useQuery({
    queryKey: medicalRecordKeys.audit(id || ''),
    queryFn: () => medicalRecordService.listAudit(id!),
    enabled: Boolean(id),
  });
}

export function useMedicalDocument(id: string | undefined) {
  return useQuery({
    queryKey: medicalRecordKeys.file(id || ''),
    queryFn: () => medicalRecordService.getFile(id!),
    enabled: Boolean(id),
  });
}

export function useCreateMedicalRecord() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (values: MedicalRecordFormValues) =>
      medicalRecordService.create(values),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: medicalRecordKeys.lists() });
      toast.success('Medical record created');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to create record')),
  });
}

export function useUpdateMedicalRecord(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (values: MedicalRecordFormValues) =>
      medicalRecordService.update(id, values),
    onSuccess: (record) => {
      qc.invalidateQueries({ queryKey: medicalRecordKeys.lists() });
      qc.setQueryData(medicalRecordKeys.detail(id), record);
      toast.success('Medical record updated');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to update record')),
  });
}

export function useDeleteMedicalRecord() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => medicalRecordService.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: medicalRecordKeys.lists() });
      toast.success('Medical record deleted');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to delete record')),
  });
}

export function useUploadMedicalDocument(recordId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      file,
      onProgress,
    }: {
      file: File;
      onProgress?: (pct: number) => void;
    }) => medicalRecordService.upload(recordId, file, onProgress),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: medicalRecordKeys.detail(recordId) });
      qc.invalidateQueries({ queryKey: medicalRecordKeys.lists() });
      qc.invalidateQueries({ queryKey: medicalRecordKeys.audit(recordId) });
      toast.success('Document uploaded');
    },
    onError: (e) => toast.error(errMsg(e, 'Upload failed')),
  });
}

export function useDeleteMedicalDocument(recordId?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) =>
      medicalRecordService.deleteFile(documentId),
    onSuccess: () => {
      if (recordId) {
        qc.invalidateQueries({ queryKey: medicalRecordKeys.detail(recordId) });
        qc.invalidateQueries({ queryKey: medicalRecordKeys.audit(recordId) });
      }
      qc.invalidateQueries({ queryKey: medicalRecordKeys.lists() });
      toast.success('Document deleted');
    },
    onError: (e) => toast.error(errMsg(e, 'Failed to delete document')),
  });
}
