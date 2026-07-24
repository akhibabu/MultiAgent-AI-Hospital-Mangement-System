import { useEffect, useMemo, useState } from 'react';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import Modal from '@/components/ui/Modal';
import Loading from '@/components/ui/Loading';
import ErrorState from '@/components/ui/ErrorState';
import { TextInput, TextSelect, TextTextarea } from '@/components/ui/FormFields';
import {
  useAnnouncements,
  useCreateAnnouncement,
  useDeleteAnnouncement,
  useUpdateAnnouncement,
} from '@/hooks/useHospital';
import {
  ANNOUNCEMENT_CATEGORIES,
  ANNOUNCEMENT_PRIORITIES,
  EMPTY_ANNOUNCEMENT_FORM,
  PRIORITY_COLORS,
  type Announcement,
  type AnnouncementFormValues,
  type AnnouncementListParams,
  type AnnouncementPriority,
} from '@/types/dashboard';

export default function AnnouncementsPage() {
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [priority, setPriority] = useState<AnnouncementPriority | ''>('');
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Announcement | null>(null);
  const [deleting, setDeleting] = useState<Announcement | null>(null);
  const [values, setValues] = useState<AnnouncementFormValues>(
    EMPTY_ANNOUNCEMENT_FORM,
  );

  useEffect(() => {
    const t = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 300);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  const params: AnnouncementListParams = useMemo(
    () => ({ page, page_size: 10, search, priority }),
    [page, search, priority],
  );

  const { data, isLoading, isError, error, refetch } = useAnnouncements(params);
  const createMutation = useCreateAnnouncement();
  const updateMutation = useUpdateAnnouncement(editing?.id || '');
  const deleteMutation = useDeleteAnnouncement();

  function openCreate() {
    setEditing(null);
    setValues({ ...EMPTY_ANNOUNCEMENT_FORM });
    setFormOpen(true);
  }

  function openEdit(a: Announcement) {
    setEditing(a);
    setValues({
      title: a.title,
      description: a.description,
      priority: a.priority,
      category: a.category,
      is_active: a.is_active,
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
    <ErrorBoundary title="Announcements error">
      <section className="space-y-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-[var(--text-primary)]">
              Announcements
            </h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Hospital notices, maintenance windows, and emergency alerts.
            </p>
          </div>
          <button
            type="button"
            onClick={openCreate}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white"
          >
            New announcement
          </button>
        </header>

        <div className="grid gap-3 rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4 sm:grid-cols-3">
          <input
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search announcements"
            className="rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm sm:col-span-2"
          />
          <select
            value={priority}
            onChange={(e) => {
              setPriority(e.target.value as AnnouncementPriority | '');
              setPage(1);
            }}
            className="rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm"
          >
            <option value="">All priorities</option>
            {ANNOUNCEMENT_PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <Loading message="Loading announcements…" />
        ) : isError ? (
          <ErrorState
            title="Unable to load announcements"
            message={error instanceof Error ? error.message : 'Request failed'}
            onRetry={() => refetch()}
          />
        ) : (
          <div className="space-y-3">
            {(data?.items ?? []).map((a) => (
              <article
                key={a.id}
                className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-base font-semibold text-[var(--text-primary)]">
                        {a.title}
                      </h3>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${PRIORITY_COLORS[a.priority]}`}
                      >
                        {a.priority}
                      </span>
                      <span className="text-[10px] uppercase tracking-wide text-[var(--text-secondary)]">
                        {a.category}
                      </span>
                      {!a.is_active ? (
                        <span className="text-[10px] text-rose-600">Inactive</span>
                      ) : null}
                    </div>
                    <p className="mt-2 whitespace-pre-wrap text-sm text-[var(--text-secondary)]">
                      {a.description}
                    </p>
                    <p className="mt-2 text-xs text-[var(--text-secondary)]">
                      {new Date(a.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => openEdit(a)}
                      className="text-xs text-primary-600 hover:underline"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => setDeleting(a)}
                      className="text-xs text-rose-600 hover:underline"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </article>
            ))}
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
          </div>
        )}
      </section>

      <Modal
        open={formOpen}
        title={editing ? 'Edit announcement' : 'New announcement'}
        onClose={() => setFormOpen(false)}
        wide
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <TextInput
            label="Title"
            required
            value={values.title}
            onChange={(e) =>
              setValues((p) => ({ ...p, title: e.target.value }))
            }
          />
          <TextTextarea
            label="Description"
            required
            rows={4}
            value={values.description}
            onChange={(e) =>
              setValues((p) => ({ ...p, description: e.target.value }))
            }
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <TextSelect
              label="Priority"
              value={values.priority}
              options={ANNOUNCEMENT_PRIORITIES.map((p) => ({
                value: p,
                label: p,
              }))}
              onChange={(e) =>
                setValues((p) => ({
                  ...p,
                  priority: e.target.value as AnnouncementPriority,
                }))
              }
            />
            <TextSelect
              label="Category"
              value={values.category}
              options={ANNOUNCEMENT_CATEGORIES.map((c) => ({
                value: c,
                label: c,
              }))}
              onChange={(e) =>
                setValues((p) => ({ ...p, category: e.target.value }))
              }
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-[var(--text-primary)]">
            <input
              type="checkbox"
              checked={values.is_active}
              onChange={(e) =>
                setValues((p) => ({ ...p, is_active: e.target.checked }))
              }
            />
            Active
          </label>
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
              Publish
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        open={Boolean(deleting)}
        title="Delete announcement?"
        onClose={() => setDeleting(null)}
      >
        <p className="text-sm text-[var(--text-secondary)]">
          Remove “{deleting?.title}”?
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
