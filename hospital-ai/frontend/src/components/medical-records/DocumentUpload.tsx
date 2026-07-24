import { useRef, useState } from 'react';
import {
  formatFileSize,
  validateMedicalFile,
} from '@/services/medicalStorageService';

interface DocumentUploadProps {
  disabled?: boolean;
  multiple?: boolean;
  onFiles: (files: File[]) => Promise<void> | void;
}

export default function DocumentUpload({
  disabled,
  multiple = true,
  onFiles,
}: DocumentUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleChange(files: FileList | null) {
    if (!files?.length) return;
    setError(null);
    const list = Array.from(files);
    for (const file of list) {
      const msg = validateMedicalFile(file);
      if (msg) {
        setError(`${file.name}: ${msg}`);
        return;
      }
    }
    setBusy(true);
    setProgress(0);
    try {
      // Simulate staged progress while parent uploads sequentially
      const step = Math.max(1, Math.floor(100 / list.length));
      let pct = 0;
      for (let i = 0; i < list.length; i += 1) {
        await onFiles([list[i]]);
        pct = Math.min(100, pct + step);
        setProgress(pct);
      }
      setProgress(100);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = '';
      window.setTimeout(() => setProgress(null), 800);
    }
  }

  return (
    <div className="space-y-2">
      <div
        className={`rounded-xl border border-dashed border-[var(--border-color)] px-4 py-6 text-center ${
          disabled || busy ? 'opacity-60' : ''
        }`}
      >
        <p className="text-sm font-medium text-[var(--text-primary)]">
          Upload documents
        </p>
        <p className="mt-1 text-xs text-[var(--text-secondary)]">
          PDF, PNG, JPEG, JPG, WEBP · max 20 MB each
        </p>
        <button
          type="button"
          disabled={disabled || busy}
          onClick={() => inputRef.current?.click()}
          className="mt-3 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-60"
        >
          {busy ? 'Uploading…' : 'Choose files'}
        </button>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          multiple={multiple}
          accept=".pdf,.png,.jpeg,.jpg,.webp,application/pdf,image/png,image/jpeg,image/webp"
          onChange={(e) => handleChange(e.target.files)}
        />
      </div>
      {progress != null ? (
        <div className="h-2 overflow-hidden rounded-full bg-surface-200 dark:bg-surface-800">
          <div
            className="h-full bg-primary-600 transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      ) : null}
      {error ? <p className="text-xs text-rose-600">{error}</p> : null}
      <p className="text-[10px] text-[var(--text-secondary)]">
        Example path: medical-records/patient_id/appointment_id/file
        {` · `}
        Selected size guide: {formatFileSize(20 * 1024 * 1024)} max
      </p>
    </div>
  );
}
