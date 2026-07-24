/**
 * Client-side helpers for medical-records uploads (validation + path conventions).
 * Actual upload goes through the FastAPI /medical-records/upload endpoint.
 */

export const MEDICAL_RECORDS_BUCKET = 'medical-records';
export const MAX_MEDICAL_FILE_BYTES = 20 * 1024 * 1024;

export const ALLOWED_MEDICAL_MIME = new Set([
  'application/pdf',
  'image/png',
  'image/jpeg',
  'image/jpg',
  'image/webp',
]);

export const ALLOWED_MEDICAL_EXT = new Set([
  'pdf',
  'png',
  'jpeg',
  'jpg',
  'webp',
]);

export function validateMedicalFile(file: File): string | null {
  const ext = file.name.split('.').pop()?.toLowerCase() || '';
  if (!ALLOWED_MEDICAL_EXT.has(ext)) {
    return 'Allowed types: PDF, PNG, JPEG, JPG, WEBP';
  }
  if (file.size > MAX_MEDICAL_FILE_BYTES) {
    return 'File must be 20MB or smaller';
  }
  if (file.type && !ALLOWED_MEDICAL_MIME.has(file.type) && file.type !== 'application/octet-stream') {
    return `Unsupported type: ${file.type}`;
  }
  return null;
}

/** Path convention used by backend storage: patient_id/appointment_id|general/file */
export function buildMedicalStoragePathPreview(
  patientId: string,
  appointmentId: string | null | undefined,
  fileName: string,
): string {
  const folder = appointmentId || 'general';
  return `${MEDICAL_RECORDS_BUCKET}/${patientId}/${folder}/${fileName}`;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function isImageType(mime: string): boolean {
  return mime.startsWith('image/');
}

export function isPdfType(mime: string): boolean {
  return mime === 'application/pdf' || mime.endsWith('/pdf');
}
