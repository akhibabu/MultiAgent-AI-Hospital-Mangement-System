import { useEffect, useMemo, useState } from 'react';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import Modal from '@/components/ui/Modal';
import Loading from '@/components/ui/Loading';
import ErrorState from '@/components/ui/ErrorState';
import { TextInput, TextSelect, TextTextarea } from '@/components/ui/FormFields';
import {
  useCreateResource,
  useDeleteResource,
  useResources,
  useUpdateResource,
  useDashboardResourceSummary,
} from '@/hooks/useHospital';
import {
  EMPTY_RESOURCE_FORM,
  RESOURCE_STATUSES,
  RESOURCE_TYPES,
  type HospitalResource,
  type ResourceFormValues,
  type ResourceListParams,
  type ResourceStatus,
  type ResourceType,
} from '@/types/resource';

export default function ResourcesPage() {
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [type, setType] = useState<ResourceType | ''>('');
  const [status, setStatus] = useState<ResourceStatus | ''>('');
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<HospitalResource | null>(null);
  const [deleting, setDeleting] = useState<HospitalResource | null>(null);
  const [values, setValues] = useState<ResourceFormValues>(EMPTY_RESOURCE_FORM);

  const summary = useDashboardResourceSummary();

  useEffect(() => {
    const t = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 300);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  const params: ResourceListParams = useMemo(
    () => ({
      page,
      page_size: 10,
      search,
      resource_type: type,
      status,
    }),
    [page, search, type, status],
  );

  const { data, isLoading, isError, error, refetch } = useResources(params);
  const createMutation = useCreateResource();
  const updateMutation = useUpdateResource(editing?.id || '');
  const deleteMutation = useDeleteResource();

  function openCreate() {
    setEditing(null);
    setValues({ ...EMPTY_RESOURCE_FORM });
    setFormOpen(true);
  }

  function openEdit(r: HospitalResource) {
    setEditing(r);
    setValues({
      resource_name: r.resource_name,
      resource_type: r.resource_type,
      quantity: String(r.quantity),
      available_quantity: String(r.available_quantity),
      status: r.status,
      location: r.location || '',
      notes: r.notes || '',
    });
    setFormOpen(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (editing) await updateMutation.mutateAsync(values);
    else await createMutation.mutateAsync(values);
    setFormOpen(false);
    setEditing(null);
  }

  return (
    <ErrorBoundary title="Resources module error">
      <section className="space-y-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-[var(--text-primary)]">
              Hospital Resources
            </h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Beds, ICU, theatres, ventilators, labs, and equipment inventory.
            </p>
          </div>
          <button
            type="button"
            onClick={openCreate}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white"
          >
            Add resource
          </button>
        </header>

        {summary.data ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Stat label="Beds available" value={`${summary.data.available_beds}/${summary.data.total_beds}`} />
            <Stat label="ICU available" value={`${summary.data.available_icu}/${summary.data.total_icu}`} />
            <Stat label="Operation theatres" value={summary.data.operation_theatres} />
            <Stat label="Ventilators" value={summary.data.ventilators_available} />
            <Stat label="Laboratories" value={summary.data.laboratories} />
          </div>
        ) : null}

        <div className="grid gap-3 rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4 lg:grid-cols-4">
          <input
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search name or location"
            className="rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm lg:col-span-2"
          />
          <select
            value={type}
            onChange={(e) => {
              setType(e.target.value as ResourceType | '');
              setPage(1);
            }}
            className="rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm"
          >
            <option value="">All types</option>
            {RESOURCE_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as ResourceStatus | '');
              setPage(1);
            }}
            className="rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            {RESOURCE_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <Loading message="Loading resources…" />
        ) : isError ? (
          <ErrorState
            title="Unable to load resources"
            message={error instanceof Error ? error.message : 'Request failed'}
            onRetry={() => refetch()}
          />
        ) : (
          <>
            <div className="overflow-x-auto rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)]">
              <table className="min-w-full text-sm">
                <thead className="border-b border-[var(--border-color)] text-left text-xs uppercase text-[var(--text-secondary)]">
                  <tr>
                    <th className="px-3 py-2">Name</th>
                    <th className="px-3 py-2">Type</th>
                    <th className="px-3 py-2">Qty</th>
                    <th className="px-3 py-2">Available</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Location</th>
                    <th className="px-3 py-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.items ?? []).map((r) => (
                    <tr key={r.id} className="border-b border-[var(--border-color)] last:border-0">
                      <td className="px-3 py-3 font-medium text-[var(--text-primary)]">
                        {r.resource_name}
                      </td>
                      <td className="px-3 py-3 text-[var(--text-secondary)]">
                        {r.resource_type}
                      </td>
                      <td className="px-3 py-3">{r.quantity}</td>
                      <td className="px-3 py-3">{r.available_quantity}</td>
                      <td className="px-3 py-3">{r.status}</td>
                      <td className="px-3 py-3 text-[var(--text-secondary)]">
                        {r.location || '—'}
                      </td>
                      <td className="px-3 py-3 text-right">
                        <button
                          type="button"
                          onClick={() => openEdit(r)}
                          className="mr-2 text-xs text-primary-600 hover:underline"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => setDeleting(r)}
                          className="text-xs text-rose-600 hover:underline"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-sm disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-sm text-[var(--text-secondary)]">
                Page {page} of {data?.total_pages || 1}
              </span>
              <button
                type="button"
                disabled={page >= (data?.total_pages || 1)}
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
        title={editing ? 'Edit resource' : 'Add resource'}
        onClose={() => setFormOpen(false)}
        wide
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <TextInput
              label="Name"
              required
              value={values.resource_name}
              onChange={(e) =>
                setValues((p) => ({ ...p, resource_name: e.target.value }))
              }
            />
            <TextSelect
              label="Type"
              required
              value={values.resource_type}
              options={RESOURCE_TYPES.map((t) => ({ value: t, label: t }))}
              onChange={(e) =>
                setValues((p) => ({
                  ...p,
                  resource_type: e.target.value as ResourceType,
                }))
              }
            />
            <TextInput
              label="Quantity"
              type="number"
              min={0}
              required
              value={values.quantity}
              onChange={(e) =>
                setValues((p) => ({ ...p, quantity: e.target.value }))
              }
            />
            <TextInput
              label="Available"
              type="number"
              min={0}
              required
              value={values.available_quantity}
              onChange={(e) =>
                setValues((p) => ({
                  ...p,
                  available_quantity: e.target.value,
                }))
              }
            />
            <TextSelect
              label="Status"
              value={values.status}
              options={RESOURCE_STATUSES.map((s) => ({ value: s, label: s }))}
              onChange={(e) =>
                setValues((p) => ({
                  ...p,
                  status: e.target.value as ResourceStatus,
                }))
              }
            />
            <TextInput
              label="Location"
              value={values.location}
              onChange={(e) =>
                setValues((p) => ({ ...p, location: e.target.value }))
              }
            />
          </div>
          <TextTextarea
            label="Notes"
            rows={2}
            value={values.notes}
            onChange={(e) =>
              setValues((p) => ({ ...p, notes: e.target.value }))
            }
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setFormOpen(false)}
              className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white"
            >
              Save
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        open={Boolean(deleting)}
        title="Delete resource?"
        onClose={() => setDeleting(null)}
      >
        <p className="text-sm text-[var(--text-secondary)]">
          Remove {deleting?.resource_name}?
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
            onClick={async () => {
              if (!deleting) return;
              await deleteMutation.mutateAsync(deleting.id);
              setDeleting(null);
            }}
            className="rounded-lg bg-rose-600 px-4 py-2 text-sm text-white"
          >
            Delete
          </button>
        </div>
      </Modal>
    </ErrorBoundary>
  );
}

function Stat({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-3">
      <p className="text-[10px] uppercase tracking-wide text-[var(--text-secondary)]">
        {label}
      </p>
      <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">
        {value}
      </p>
    </div>
  );
}
