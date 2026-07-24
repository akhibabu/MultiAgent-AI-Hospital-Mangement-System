import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import DocumentUpload from '@/components/medical-records/DocumentUpload';
import DocumentViewer from '@/components/medical-records/DocumentViewer';
import MedicalRecordForm from '@/components/medical-records/MedicalRecordForm';
import RecordTypeChip from '@/components/medical-records/RecordTypeChip';
import Modal from '@/components/ui/Modal';
import Loading from '@/components/ui/Loading';
import ErrorState from '@/components/ui/ErrorState';
import {
  useDeleteMedicalDocument,
  useDeleteMedicalRecord,
  useMedicalRecord,
  useMedicalRecordAudit,
  useUpdateMedicalRecord,
  useUploadMedicalDocument,
} from '@/hooks/useMedicalRecords';
import { formatFileSize } from '@/services/medicalStorageService';
import type {
  MedicalDocument,
  MedicalRecordFormValues,
} from '@/types/medicalRecord';

export default function MedicalRecordDetailPage() {
  const { recordId } = useParams();
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useMedicalRecord(recordId);
  const auditQuery = useMedicalRecordAudit(recordId);
  const updateMutation = useUpdateMedicalRecord(recordId || '');
  const deleteMutation = useDeleteMedicalRecord();
  const uploadMutation = useUploadMedicalDocument(recordId || '');
  const deleteDocMutation = useDeleteMedicalDocument(recordId);
  const [editOpen, setEditOpen] = useState(false);
  const [viewerDoc, setViewerDoc] = useState<MedicalDocument | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);

  if (isLoading) return <Loading message="Loading medical record…" />;
  if (isError || !data) {
    return (
      <ErrorState
        title="Unable to load record"
        message={error instanceof Error ? error.message : 'Not found'}
        onRetry={() => refetch()}
      />
    );
  }

  async function handleUpdate(values: MedicalRecordFormValues) {
    await updateMutation.mutateAsync(values);
    setEditOpen(false);
  }

  async function handleUpload(files: File[]) {
    for (const file of files) {
      await uploadMutation.mutateAsync({ file });
    }
  }

  return (
    <ErrorBoundary title="Medical record detail error">
      <section className="mx-auto max-w-5xl space-y-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <RecordTypeChip type={data.record_type} />
              {data.ocr_status ? (
                <span className="rounded-full bg-surface-100 px-2 py-0.5 text-[10px] uppercase tracking-wide text-[var(--text-secondary)] dark:bg-surface-800">
                  OCR · {data.ocr_status}
                </span>
              ) : null}
            </div>
            <h2 className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">
              {data.title}
            </h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Created {new Date(data.created_at).toLocaleString()}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setEditOpen(true)}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white"
            >
              Edit
            </button>
            <button
              type="button"
              onClick={() => setDeleteOpen(true)}
              className="rounded-lg border border-rose-600/40 px-4 py-2 text-sm text-rose-600"
            >
              Delete
            </button>
            <Link
              to="/medical-records"
              className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm"
            >
              Back
            </Link>
          </div>
        </header>

        <div className="grid gap-4 sm:grid-cols-2">
          <Card title="Patient">
            {data.patient ? (
              <Link
                to={`/patients/${data.patient.id}`}
                className="text-sm font-medium text-primary-600 hover:underline"
              >
                {data.patient.first_name} {data.patient.last_name}
              </Link>
            ) : (
              <p className="text-sm">—</p>
            )}
          </Card>
          <Card title="Doctor">
            <p className="text-sm text-[var(--text-primary)]">
              {data.doctor
                ? `Dr. ${data.doctor.first_name} ${data.doctor.last_name}`
                : '—'}
            </p>
          </Card>
          <Card title="Appointment">
            <p className="text-sm text-[var(--text-primary)]">
              {data.appointment
                ? `${data.appointment.appointment_number}${
                    data.appointment.appointment_date
                      ? ` · ${data.appointment.appointment_date}`
                      : ''
                  }`
                : '—'}
            </p>
          </Card>
          <Card title="Diagnosis">
            <p className="text-sm text-[var(--text-primary)]">
              {data.diagnosis || '—'}
            </p>
          </Card>
        </div>

        <Card title="Treatment">
          <p className="whitespace-pre-wrap text-sm">{data.treatment || '—'}</p>
        </Card>
        <Card title="Notes">
          <p className="whitespace-pre-wrap text-sm">{data.notes || '—'}</p>
        </Card>

        <Card title="Documents">
          <DocumentUpload
            disabled={uploadMutation.isPending}
            onFiles={handleUpload}
          />
          <ul className="mt-4 space-y-2">
            {!data.documents.length ? (
              <li className="text-sm text-[var(--text-secondary)]">
                No documents uploaded yet
              </li>
            ) : (
              data.documents.map((doc) => (
                <li
                  key={doc.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--border-color)] px-3 py-2"
                >
                  <button
                    type="button"
                    onClick={() => setViewerDoc(doc)}
                    className="text-left text-sm font-medium text-primary-600 hover:underline"
                  >
                    {doc.file_name}
                  </button>
                  <span className="text-xs text-[var(--text-secondary)]">
                    {formatFileSize(doc.file_size)}
                  </span>
                </li>
              ))
            )}
          </ul>
        </Card>

        <Card title="Audit log">
          {auditQuery.isLoading ? (
            <Loading message="Loading audit…" />
          ) : !(auditQuery.data?.items.length) ? (
            <p className="text-sm text-[var(--text-secondary)]">No audit events</p>
          ) : (
            <ul className="space-y-2">
              {auditQuery.data.items.map((evt) => (
                <li key={evt.id} className="text-sm">
                  <span className="font-medium text-[var(--text-primary)]">
                    {evt.action}
                  </span>
                  <span className="text-[var(--text-secondary)]">
                    {' '}
                    · {new Date(evt.timestamp).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Future AI / RAG">
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              ['ai_summary', 'Clinical summary from MedicalSummaryService'],
              ['detected_conditions', 'Condition detection payload'],
              ['risk_score', 'Risk scoring extension'],
              ['recommended_tests', 'Suggested follow-up tests'],
              ['embedding_id', 'EmbeddingService document id'],
              ['vector_status', 'VectorIndexService status'],
              ['ocr_status', 'OCRService pipeline status'],
            ].map(([label, hint]) => (
              <div
                key={label}
                className="rounded-lg border border-dashed border-[var(--border-color)] px-3 py-2"
              >
                <p className="font-mono text-xs text-[var(--text-primary)]">
                  medical_record.{label}
                </p>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">{hint}</p>
              </div>
            ))}
          </div>
        </Card>
      </section>

      <Modal
        open={editOpen}
        title="Edit medical record"
        onClose={() => setEditOpen(false)}
        wide
      >
        <MedicalRecordForm
          initial={data}
          submitting={updateMutation.isPending}
          submitLabel="Save changes"
          onSubmit={handleUpdate}
          onCancel={() => setEditOpen(false)}
        />
      </Modal>

      <Modal
        open={Boolean(viewerDoc)}
        title="Document viewer"
        onClose={() => setViewerDoc(null)}
        wide
      >
        {viewerDoc ? (
          <DocumentViewer
            document={viewerDoc}
            record={data}
            onClose={() => setViewerDoc(null)}
            onDelete={async () => {
              await deleteDocMutation.mutateAsync(viewerDoc.id);
              setViewerDoc(null);
            }}
          />
        ) : null}
      </Modal>

      <Modal
        open={deleteOpen}
        title="Delete medical record?"
        onClose={() => setDeleteOpen(false)}
      >
        <p className="text-sm text-[var(--text-secondary)]">
          Permanently remove this record and its files.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={() => setDeleteOpen(false)}
            className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm"
          >
            Keep
          </button>
          <button
            type="button"
            disabled={deleteMutation.isPending}
            onClick={async () => {
              await deleteMutation.mutateAsync(data.id);
              navigate('/medical-records');
            }}
            className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white"
          >
            Delete
          </button>
        </div>
      </Modal>
    </ErrorBoundary>
  );
}

function Card({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
        {title}
      </h3>
      {children}
    </section>
  );
}
