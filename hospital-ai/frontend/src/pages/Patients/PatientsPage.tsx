import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import PatientForm from '@/components/patients/PatientForm';
import PatientsTable from '@/components/patients/PatientsTable';
import Modal from '@/components/ui/Modal';
import Loading from '@/components/ui/Loading';
import ErrorState from '@/components/ui/ErrorState';
import {
  useCreatePatient,
  useDeletePatient,
  usePatients,
  useUpdatePatient,
} from '@/hooks/usePatients';
import {
  BLOOD_GROUP_OPTIONS,
  GENDER_OPTIONS,
  type BloodGroup,
  type Patient,
  type PatientFormValues,
  type PatientGender,
  type PatientListParams,
} from '@/types/patient';
import { exportPatientsToCsv } from '@/utils/exportPatientsCsv';

export default function PatientsPage() {
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [gender, setGender] = useState<PatientGender | ''>('');
  const [bloodGroup, setBloodGroup] = useState<BloodGroup | ''>('');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Patient | null>(null);
  const [deleting, setDeleting] = useState<Patient | null>(null);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 350);
    return () => window.clearTimeout(handle);
  }, [searchInput]);

  const params: PatientListParams = useMemo(
    () => ({
      page,
      page_size: pageSize,
      search,
      gender,
      blood_group: bloodGroup,
      sort_by: sortBy,
      sort_order: sortOrder,
    }),
    [page, pageSize, search, gender, bloodGroup, sortBy, sortOrder],
  );

  const { data, isLoading, isError, error, refetch, isFetching } =
    usePatients(params);
  const createMutation = useCreatePatient();
  const updateMutation = useUpdatePatient(editing?.id || '');
  const deleteMutation = useDeletePatient();

  function handleSort(column: string) {
    if (sortBy === column) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
    setPage(1);
  }

  async function handleSubmit(values: PatientFormValues) {
    if (editing) {
      await updateMutation.mutateAsync(values);
    } else {
      await createMutation.mutateAsync(values);
    }
    setFormOpen(false);
    setEditing(null);
  }

  async function confirmDelete() {
    if (!deleting) return;
    await deleteMutation.mutateAsync(deleting.id);
    setDeleting(null);
  }

  function handleExport() {
    const items = data?.items ?? [];
    if (items.length === 0) {
      toast.message('Nothing to export on this page');
      return;
    }
    exportPatientsToCsv(items, `patients-page-${page}.csv`);
    toast.success('CSV exported');
  }

  const totalPages = data?.total_pages ?? 0;

  return (
    <ErrorBoundary title="Patients module error">
      <section className="space-y-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
              Patients
            </h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Register, search, and manage hospital patient records.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleExport}
              className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] hover:bg-surface-100 dark:hover:bg-surface-800"
            >
              Export CSV
            </button>
            <button
              type="button"
              onClick={() => {
                setEditing(null);
                setFormOpen(true);
              }}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
            >
              Add Patient
            </button>
          </div>
        </header>

        <div className="grid gap-3 rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="sm:col-span-2">
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Search
            </label>
            <input
              type="search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Name, patient number, or phone"
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-500"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Gender
            </label>
            <select
              value={gender}
              onChange={(e) => {
                setGender(e.target.value as PatientGender | '');
                setPage(1);
              }}
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-500"
            >
              <option value="">All genders</option>
              {GENDER_OPTIONS.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Blood group
            </label>
            <select
              value={bloodGroup}
              onChange={(e) => {
                setBloodGroup(e.target.value as BloodGroup | '');
                setPage(1);
              }}
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-500"
            >
              <option value="">All blood groups</option>
              {BLOOD_GROUP_OPTIONS.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </div>
        </div>

        {isLoading ? (
          <Loading message="Loading patients…" />
        ) : isError ? (
          <ErrorState
            title="Unable to load patients"
            message={
              error instanceof Error
                ? error.message
                : 'Please try again shortly.'
            }
            onRetry={() => refetch()}
          />
        ) : (
          <>
            <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
              <span>
                {data?.total ?? 0} patient{(data?.total ?? 0) === 1 ? '' : 's'}
                {isFetching ? ' · refreshing…' : ''}
              </span>
              <span>
                Page {data?.page ?? 1} of {Math.max(totalPages, 1)}
              </span>
            </div>

            <PatientsTable
              patients={data?.items ?? []}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={handleSort}
              onEdit={(patient) => {
                setEditing(patient);
                setFormOpen(true);
              }}
              onDelete={setDeleting}
            />

            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-sm disabled:opacity-40"
              >
                Previous
              </button>
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
        wide
        title={editing ? 'Edit patient' : 'Add patient'}
        onClose={() => {
          if (createMutation.isPending || updateMutation.isPending) return;
          setFormOpen(false);
          setEditing(null);
        }}
      >
        <PatientForm
          initialPatient={editing}
          submitting={createMutation.isPending || updateMutation.isPending}
          submitLabel={editing ? 'Update patient' : 'Register patient'}
          onCancel={() => {
            setFormOpen(false);
            setEditing(null);
          }}
          onSubmit={handleSubmit}
        />
      </Modal>

      <Modal
        open={Boolean(deleting)}
        title="Delete patient"
        onClose={() => {
          if (deleteMutation.isPending) return;
          setDeleting(null);
        }}
      >
        <p className="text-sm text-[var(--text-secondary)]">
          Delete{' '}
          <strong className="text-[var(--text-primary)]">
            {deleting?.first_name} {deleting?.last_name}
          </strong>{' '}
          ({deleting?.patient_number})? This cannot be undone.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            disabled={deleteMutation.isPending}
            onClick={() => setDeleting(null)}
            className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={deleteMutation.isPending}
            onClick={confirmDelete}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-70"
          >
            {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </Modal>
    </ErrorBoundary>
  );
}
