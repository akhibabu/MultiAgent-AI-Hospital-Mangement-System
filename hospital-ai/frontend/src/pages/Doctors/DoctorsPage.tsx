import { useEffect, useMemo, useState } from 'react';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import DoctorForm from '@/components/doctors/DoctorForm';
import DoctorsTable from '@/components/doctors/DoctorsTable';
import Modal from '@/components/ui/Modal';
import Loading from '@/components/ui/Loading';
import ErrorState from '@/components/ui/ErrorState';
import {
  useCreateDoctor,
  useDeleteDoctor,
  useDepartments,
  useDoctors,
  useUpdateDoctor,
} from '@/hooks/useDoctors';
import {
  AVAILABILITY_STATUSES,
  type AvailabilityStatus,
  type Doctor,
  type DoctorFormValues,
  type DoctorListParams,
} from '@/types/doctor';

export default function DoctorsPage() {
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [status, setStatus] = useState<AvailabilityStatus | ''>('');
  const [minExperience, setMinExperience] = useState<number | ''>('');
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Doctor | null>(null);
  const [deleting, setDeleting] = useState<Doctor | null>(null);

  const { data: deptData } = useDepartments();

  useEffect(() => {
    const t = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 350);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  const params: DoctorListParams = useMemo(
    () => ({
      page,
      page_size: 10,
      search,
      department_id: departmentId,
      availability_status: status,
      min_experience: minExperience,
      sort_by: sortBy,
      sort_order: sortOrder,
    }),
    [page, search, departmentId, status, minExperience, sortBy, sortOrder],
  );

  const { data, isLoading, isError, error, refetch, isFetching } =
    useDoctors(params);
  const createMutation = useCreateDoctor();
  const updateMutation = useUpdateDoctor(editing?.id || '');
  const deleteMutation = useDeleteDoctor();

  function handleSort(column: string) {
    if (sortBy === column) {
      setSortOrder((p) => (p === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
    setPage(1);
  }

  async function handleSubmit(values: DoctorFormValues) {
    if (editing) await updateMutation.mutateAsync(values);
    else await createMutation.mutateAsync(values);
    setFormOpen(false);
    setEditing(null);
  }

  const totalPages = data?.total_pages ?? 0;

  return (
    <ErrorBoundary title="Doctors module error">
      <section className="space-y-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
              Doctors
            </h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Manage physicians, specialties, departments, and availability.
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
            Add Doctor
          </button>
        </header>

        <div className="grid gap-3 rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4 lg:grid-cols-4">
          <div className="lg:col-span-2">
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Search
            </label>
            <input
              type="search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Name, doctor number, or specialization"
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-500"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Department
            </label>
            <select
              value={departmentId}
              onChange={(e) => {
                setDepartmentId(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm"
            >
              <option value="">All departments</option>
              {(deptData?.items ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Availability
            </label>
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value as AvailabilityStatus | '');
                setPage(1);
              }}
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm"
            >
              <option value="">All statuses</option>
              {AVAILABILITY_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Min. experience (years)
            </label>
            <input
              type="number"
              min={0}
              value={minExperience}
              onChange={(e) => {
                setMinExperience(
                  e.target.value === '' ? '' : Number(e.target.value),
                );
                setPage(1);
              }}
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm"
            />
          </div>
        </div>

        {isLoading ? (
          <Loading message="Loading doctors…" />
        ) : isError ? (
          <ErrorState
            title="Unable to load doctors"
            message={error instanceof Error ? error.message : 'Try again'}
            onRetry={() => refetch()}
          />
        ) : (
          <>
            <div className="flex justify-between text-xs text-[var(--text-secondary)]">
              <span>
                {data?.total ?? 0} doctor{(data?.total ?? 0) === 1 ? '' : 's'}
                {isFetching ? ' · refreshing…' : ''}
              </span>
              <span>
                Page {data?.page ?? 1} of {Math.max(totalPages, 1)}
              </span>
            </div>
            <DoctorsTable
              doctors={data?.items ?? []}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={handleSort}
              onEdit={(d) => {
                setEditing(d);
                setFormOpen(true);
              }}
              onDelete={setDeleting}
            />
            <div className="flex justify-end gap-2">
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
        title={editing ? 'Edit doctor' : 'Add doctor'}
        onClose={() => {
          if (createMutation.isPending || updateMutation.isPending) return;
          setFormOpen(false);
          setEditing(null);
        }}
      >
        <DoctorForm
          initialDoctor={editing}
          submitting={createMutation.isPending || updateMutation.isPending}
          submitLabel={editing ? 'Update doctor' : 'Register doctor'}
          onCancel={() => {
            setFormOpen(false);
            setEditing(null);
          }}
          onSubmit={handleSubmit}
        />
      </Modal>

      <Modal
        open={Boolean(deleting)}
        title="Delete doctor"
        onClose={() => !deleteMutation.isPending && setDeleting(null)}
      >
        <p className="text-sm text-[var(--text-secondary)]">
          Delete{' '}
          <strong className="text-[var(--text-primary)]">
            Dr. {deleting?.first_name} {deleting?.last_name}
          </strong>{' '}
          ({deleting?.doctor_number})?
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={() => setDeleting(null)}
            className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={deleteMutation.isPending}
            onClick={async () => {
              if (!deleting) return;
              await deleteMutation.mutateAsync(deleting.id);
              setDeleting(null);
            }}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white"
          >
            {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </Modal>
    </ErrorBoundary>
  );
}
