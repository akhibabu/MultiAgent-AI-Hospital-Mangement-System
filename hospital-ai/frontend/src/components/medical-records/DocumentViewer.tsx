import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  formatFileSize,
  isImageType,
  isPdfType,
} from '@/services/medicalStorageService';
import type { MedicalDocument, MedicalRecord } from '@/types/medicalRecord';

interface DocumentViewerProps {
  document: MedicalDocument;
  record?: MedicalRecord | null;
  onClose?: () => void;
  onDelete?: () => void;
}

export default function DocumentViewer({
  document,
  record,
  onClose,
  onDelete,
}: DocumentViewerProps) {
  const [zoom, setZoom] = useState(1);
  const url = document.signed_url || document.file_url;
  const image = isImageType(document.file_type);
  const pdf = isPdfType(document.file_type);

  function toggleFullscreen() {
    const el = window.document.getElementById('med-doc-viewer');
    if (!el) return;
    if (!window.document.fullscreenElement) {
      void el.requestFullscreen();
    } else {
      void window.document.exitFullscreen();
    }
  }

  return (
    <div className="space-y-4" id="med-doc-viewer">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-[var(--text-primary)]">
            {document.file_name}
          </h3>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">
            {document.file_type} · {formatFileSize(document.file_size)} ·{' '}
            {new Date(document.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href={url}
            download={document.file_name}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-sm"
          >
            Download
          </a>
          <button
            type="button"
            onClick={toggleFullscreen}
            className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-sm"
          >
            Full screen
          </button>
          {onDelete ? (
            <button
              type="button"
              onClick={onDelete}
              className="rounded-lg border border-rose-600/40 px-3 py-1.5 text-sm text-rose-600"
            >
              Delete
            </button>
          ) : null}
          {onClose ? (
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-sm"
            >
              Close
            </button>
          ) : null}
        </div>
      </div>

      <div className="grid gap-3 rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4 sm:grid-cols-2 lg:grid-cols-4">
        <Meta
          label="Patient"
          value={
            record?.patient
              ? `${record.patient.first_name} ${record.patient.last_name}`
              : '—'
          }
          link={
            record?.patient_id
              ? `/patients/${record.patient_id}`
              : undefined
          }
        />
        <Meta
          label="Doctor"
          value={
            record?.doctor
              ? `Dr. ${record.doctor.first_name} ${record.doctor.last_name}`
              : '—'
          }
        />
        <Meta label="Upload date" value={new Date(document.created_at).toLocaleString()} />
        <Meta label="File size" value={formatFileSize(document.file_size)} />
      </div>

      {image ? (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}
              className="rounded border border-[var(--border-color)] px-2 py-1 text-sm"
            >
              −
            </button>
            <span className="text-xs text-[var(--text-secondary)]">
              {Math.round(zoom * 100)}%
            </span>
            <button
              type="button"
              onClick={() => setZoom((z) => Math.min(3, z + 0.25))}
              className="rounded border border-[var(--border-color)] px-2 py-1 text-sm"
            >
              +
            </button>
          </div>
          <div className="overflow-auto rounded-xl border border-[var(--border-color)] bg-black/5 p-4 dark:bg-white/5">
            <img
              src={url}
              alt={document.file_name}
              style={{ transform: `scale(${zoom})`, transformOrigin: 'top left' }}
              className="max-w-full rounded"
            />
          </div>
        </div>
      ) : null}

      {pdf ? (
        <iframe
          title={document.file_name}
          src={url}
          className="h-[70vh] w-full rounded-xl border border-[var(--border-color)]"
        />
      ) : null}

      {!image && !pdf ? (
        <div className="rounded-xl border border-dashed border-[var(--border-color)] px-4 py-10 text-center text-sm text-[var(--text-secondary)]">
          Preview not available for this file type.{' '}
          <a href={url} className="text-primary-600 hover:underline" target="_blank" rel="noreferrer">
            Open / download
          </a>
        </div>
      ) : null}
    </div>
  );
}

function Meta({
  label,
  value,
  link,
}: {
  label: string;
  value: string;
  link?: string;
}) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide text-[var(--text-secondary)]">
        {label}
      </p>
      {link ? (
        <Link to={link} className="text-sm font-medium text-primary-600 hover:underline">
          {value}
        </Link>
      ) : (
        <p className="text-sm font-medium text-[var(--text-primary)]">{value}</p>
      )}
    </div>
  );
}
