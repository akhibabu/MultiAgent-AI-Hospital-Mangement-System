import { supabase } from '@/services/supabaseClient';

export {
  ALLOWED_MEDICAL_EXT,
  ALLOWED_MEDICAL_MIME,
  MEDICAL_RECORDS_BUCKET,
  MAX_MEDICAL_FILE_BYTES,
  buildMedicalStoragePathPreview,
  formatFileSize,
  isImageType,
  isPdfType,
  validateMedicalFile,
} from '@/services/medicalStorageService';

const BUCKET = 'doctor-photos';
const MAX_BYTES = 5 * 1024 * 1024;
const ALLOWED = new Set(['image/jpeg', 'image/png', 'image/webp', 'image/gif']);

/**
 * Reusable Supabase Storage upload helper for doctor profile photos.
 */
export async function uploadDoctorPhoto(file: File): Promise<string> {
  if (!ALLOWED.has(file.type)) {
    throw new Error('Only JPEG, PNG, WEBP, or GIF images are allowed');
  }
  if (file.size > MAX_BYTES) {
    throw new Error('Image must be 5MB or smaller');
  }

  const ext = file.name.split('.').pop()?.toLowerCase() || 'jpg';
  const path = `${crypto.randomUUID()}.${ext}`;

  const { error } = await supabase.storage.from(BUCKET).upload(path, file, {
    cacheControl: '3600',
    upsert: false,
    contentType: file.type,
  });

  if (error) {
    throw new Error(error.message || 'Failed to upload photo');
  }

  const { data } = supabase.storage.from(BUCKET).getPublicUrl(path);
  return data.publicUrl;
}

export default { uploadDoctorPhoto };
