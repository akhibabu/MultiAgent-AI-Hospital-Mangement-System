import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import MedicalRecordForm from '@/components/medical-records/MedicalRecordForm';
import MedicalRecordsTable from '@/components/medical-records/MedicalRecordsTable';
import Modal from '@/components/ui/Modal';
import Loading from '@/components/ui/Loading';
import ErrorState from '@/components/ui/ErrorState';
import {
  useCreateMedicalRecord,
  useDeleteMedicalRecord,
  useMedicalRecords,
  useUpdateMedicalRecord,
} from '@/hooks/useMedicalRecords';
import { useDoctors } from '@/hooks/useDoctors';
import {
  MEDICAL_RECORD_TYPES,
  type MedicalRecord,
  type MedicalRecordFormValues,
  type MedicalRecordListParams,
  type MedicalRecordType,
} from '@/types/medicalRecord';

export default function MedicalRecordsPage() {
  const [searchParams] = useSearchParams();
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [patientId] = useState(searchParams.get('patientId') || '');
  const [doctorId, setDoctorId] = useState('');
  const [recordType, setRecordType] = useState<MedicalRecordType | ''>('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<MedicalRecord | null>(null);
  const [deleting, setDeleting] = useState<MedicalRecord | null>(null);

  const { data: doctorsData } = useDoctors({ page: 1, page_size: 100 });

  useEffect(() => {
    const t = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 350);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  const params: MedicalRecordListParams = useMemo(
    () => ({
      page,
      page_size: 10,
      search,
      patient_id: patientId,
      doctor_id: doctorId,
      record_type: recordType,
      date_from: dateFrom,
      date_to: dateTo,
      sort_by: sortBy,
      sort_order: sortOrder,
    }),
    [
      page,
      search,
      patientId,
      doctorId,
      recordType,
      dateFrom,
      dateTo,
      sortBy,
      sortOrder,
    ],
  );

  const { data, isLoading, isError, error, refetch, isFetching } =
    useMedicalRecords(params);
  const createMutation = useCreateMedicalRecord();
  const updateMutation = useUpdateMedicalRecord(editing?.id || '');
  const deleteMutation = useDeleteMedicalRecord();

  function handleSort(column: string) {
    if (sortBy === column) {
      setSortOrder((p) => (p === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
    setPage(1);
  }

  async function handleSubmit(values: MedicalRecordFormValues) {
    if (editing) await updateMutation.mutateAsync(values);
    else await createMutation.mutateAsync(values);
    setFormOpen(false);
    setEditing(null);
  }

  const totalPages = data?.total_pages ?? 0;

  return (
    <ErrorBoundary title="Medical records module error">
      <section className="space-y-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
              Medical Records
            </h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              EMR for consultations, labs, imaging, prescriptions, and discharge
              summaries.
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              setEditing(null);
              setFormOpen(true);
            }}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            New record
          </button>
        </header>

        <div className="grid gap-3 rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4 lg:grid-cols-3 xl:grid-cols-6">
          <div className="lg:col-span-2">
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Search
            </label>
            <input
              type="search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Title, diagnosis, notes…"
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-500"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Doctor
            </label>
            <select
              value={doctorId}
              onChange={(e) => {
                setDoctorId(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-500"
            >
              <option value="">All doctors</option>
              {(doctorsData?.items ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  Dr. {d.first_name} {d.last_name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Record type
            </label>
            <select
              value={recordType}
              onChange={(e) => {
                setRecordType(e.target.value as MedicalRecordType | '');
                setPage(1);
              }}
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-500"
            >
              <option value="">All types</option>
              {MEDICAL_RECORD_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              From
            </label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-500"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              To
            </label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-500"
            />
          </div>
        </div>

        {isLoading ? (
          <Loading message="Loading medical records…" />
        ) : isError ? (
          <ErrorState
            title="Unable to load medical records"
            message={error instanceof Error ? error.message : 'Request failed'}
            onRetry={() => refetch()}
          />
        ) : (
          <>
            <div className="text-xs text-[var(--text-secondary)]">
              {data?.total ?? 0} records
              {isFetching ? ' · refreshing…' : ''}
              {patientId ? ' · filtered by patient' : ''}
            </div>
            <MedicalRecordsTable
              items={data?.items ?? []}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={handleSort}
              onEdit={(r) => {
                setEditing(r);
                setFormOpen(true);
              }}
              onDelete={setDeleting}
            />
            <div className="flex items-center justify-between">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-sm disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-sm text-[var(--text-secondary)]">
                Page {page} of {totalPages || 1}
              </span>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-sm disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </>
        )}
      </section>

      <Modal
        open={formOpen}
        title={editing ? 'Edit medical record' : 'New medical record'}
        onClose={() => {
          setFormOpen(false);
          setEditing(null);
        }}
        wide
      >
        <MedicalRecordForm
          initial={editing}
          defaultPatientId={patientId || undefined}
          submitting={createMutation.isPending || updateMutation.isPending}
          submitLabel={editing ? 'Update record' : 'Create record'}
          onSubmit={handleSubmit}
          onCancel={() => {
            setFormOpen(false);
            setEditing(null);
          }}
        />
      </Modal>

      <Modal
        open={Boolean(deleting)}
        title="Delete medical record?"
        onClose={() => setDeleting(null)}
      >
        <p className="text-sm text-[var(--text-secondary)]">
          This deletes {deleting?.title} and all attached documents.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={() => setDeleting(null)}
            className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm"
          >
            Keep
          </button>
          <button
            type="button"
            disabled={deleteMutation.isPending}
            onClick={async () => {
              if (!deleting) return;
              await deleteMutation.mutateAsync(deleting.id);
              setDeleting(null);
            }}
            className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white"
          >
            {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </Modal>
    </ErrorBoundary>
  );
}
