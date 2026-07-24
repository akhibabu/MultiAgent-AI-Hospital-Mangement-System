import { type FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import Modal from '@/components/ui/Modal';
import Loading from '@/components/ui/Loading';
import ErrorState from '@/components/ui/ErrorState';
import { TextInput, TextSelect, TextTextarea } from '@/components/ui/FormFields';
import {
  useCreateDepartment,
  useDeleteDepartment,
  useDepartments,
  useDoctors,
  useUpdateDepartment,
} from '@/hooks/useDoctors';
import {
  EMPTY_DEPARTMENT_FORM,
  type Department,
  type DepartmentFormValues,
} from '@/types/doctor';

export default function DepartmentsPage() {
  const [search, setSearch] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Department | null>(null);
  const [deleting, setDeleting] = useState<Department | null>(null);
  const [values, setValues] = useState<DepartmentFormValues>(EMPTY_DEPARTMENT_FORM);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading, isError, error, refetch } = useDepartments(search);
  const { data: doctorsData } = useDoctors({ page: 1, page_size: 100 });
  const createMutation = useCreateDepartment();
  const updateMutation = useUpdateDepartment(editing?.id || '');
  const deleteMutation = useDeleteDepartment();

  const selected = data?.items.find((d) => d.id === selectedId) ?? null;

  function openCreate() {
    setEditing(null);
    setValues(EMPTY_DEPARTMENT_FORM);
    setFormOpen(true);
  }

  function openEdit(dept: Department) {
    setEditing(dept);
    setValues({
      name: dept.name,
      description: dept.description || '',
      floor_number: dept.floor_number != null ? String(dept.floor_number) : '',
      head_doctor_id: dept.head_doctor_id || '',
    });
    setFormOpen(true);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!values.name.trim()) return;
    if (editing) await updateMutation.mutateAsync(values);
    else await createMutation.mutateAsync(values);
    setFormOpen(false);
    setEditing(null);
  }

  return (
    <ErrorBoundary title="Departments module error">
      <section className="space-y-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-[var(--text-primary)]">
              Departments
            </h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Organize hospital units, floors, and department heads.
            </p>
          </div>
          <button
            type="button"
            onClick={openCreate}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white"
          >
            Add Department
          </button>
        </header>

        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search departments"
          className="w-full max-w-md rounded-lg border border-[var(--border-color)] bg-[var(--bg-navbar)] px-3 py-2 text-sm"
        />

        {isLoading ? (
          <Loading message="Loading departments…" />
        ) : isError ? (
          <ErrorState
            title="Unable to load departments"
            message={error instanceof Error ? error.message : 'Try again'}
            onRetry={() => refetch()}
          />
        ) : (
          <div className="grid gap-4 lg:grid-cols-5">
            <div className="space-y-2 lg:col-span-2">
              {(data?.items ?? []).length === 0 ? (
                <div className="rounded-xl border border-dashed border-[var(--border-color)] p-8 text-center text-sm text-[var(--text-secondary)]">
                  No departments yet.
                </div>
              ) : (
                (data?.items ?? []).map((dept) => (
                  <button
                    key={dept.id}
                    type="button"
                    onClick={() => setSelectedId(dept.id)}
                    className={`w-full rounded-xl border px-4 py-3 text-left transition ${
                      selectedId === dept.id
                        ? 'border-primary-500 bg-primary-50/50 dark:bg-primary-950/20'
                        : 'border-[var(--border-color)] bg-[var(--bg-navbar)] hover:border-primary-300'
                    }`}
                  >
                    <p className="font-medium text-[var(--text-primary)]">
                      {dept.name}
                    </p>
                    <p className="text-xs text-[var(--text-secondary)]">
                      {dept.doctors_count} doctors
                      {dept.floor_number != null
                        ? ` · Floor ${dept.floor_number}`
                        : ''}
                    </p>
                  </button>
                ))
              )}
            </div>

            <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5 lg:col-span-3">
              {!selected ? (
                <p className="text-sm text-[var(--text-secondary)]">
                  Select a department to view details and statistics.
                </p>
              ) : (
                <div className="space-y-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-xl font-semibold text-[var(--text-primary)]">
                        {selected.name}
                      </h3>
                      <p className="mt-1 text-sm text-[var(--text-secondary)]">
                        {selected.description || 'No description'}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => openEdit(selected)}
                        className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-xs"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleting(selected)}
                        className="rounded-lg px-3 py-1.5 text-xs text-red-600"
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-lg border border-[var(--border-color)] p-4">
                      <p className="text-xs text-[var(--text-secondary)]">
                        Doctors count
                      </p>
                      <p className="mt-1 text-2xl font-semibold text-[var(--text-primary)]">
                        {selected.doctors_count}
                      </p>
                    </div>
                    <div className="rounded-lg border border-dashed border-[var(--border-color)] p-4">
                      <p className="text-xs text-[var(--text-secondary)]">
                        Patient count
                      </p>
                      <p className="mt-1 text-2xl font-semibold text-[var(--text-primary)]">
                        {selected.patients_count}
                      </p>
                      <p className="mt-1 text-[10px] uppercase tracking-wide text-[var(--text-secondary)]">
                        Placeholder · future module
                      </p>
                    </div>
                    <div className="rounded-lg border border-[var(--border-color)] p-4">
                      <p className="text-xs text-[var(--text-secondary)]">Floor</p>
                      <p className="mt-1 text-2xl font-semibold text-[var(--text-primary)]">
                        {selected.floor_number ?? '—'}
                      </p>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs text-[var(--text-secondary)]">
                      Head doctor
                    </p>
                    <p className="mt-1 text-sm font-medium text-[var(--text-primary)]">
                      {selected.head_doctor_name
                        ? `Dr. ${selected.head_doctor_name}`
                        : 'Not assigned'}
                    </p>
                  </div>

                  <Link
                    to={`/doctors?department=${selected.id}`}
                    className="inline-block text-sm font-medium text-primary-600 hover:underline"
                  >
                    View doctors in this department →
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      <Modal
        open={formOpen}
        title={editing ? 'Edit department' : 'Add department'}
        onClose={() => {
          if (createMutation.isPending || updateMutation.isPending) return;
          setFormOpen(false);
        }}
      >
        <form className="space-y-4" onSubmit={handleSubmit}>
          <TextInput
            label="Name"
            required
            value={values.name}
            onChange={(e) => setValues((p) => ({ ...p, name: e.target.value }))}
          />
          <TextTextarea
            label="Description"
            value={values.description}
            onChange={(e) =>
              setValues((p) => ({ ...p, description: e.target.value }))
            }
          />
          <TextInput
            label="Floor number"
            type="number"
            value={values.floor_number}
            onChange={(e) =>
              setValues((p) => ({ ...p, floor_number: e.target.value }))
            }
          />
          <TextSelect
            label="Head doctor"
            value={values.head_doctor_id}
            onChange={(e) =>
              setValues((p) => ({ ...p, head_doctor_id: e.target.value }))
            }
            placeholder="Select head doctor"
            options={(doctorsData?.items ?? []).map((d) => ({
              value: d.id,
              label: `Dr. ${d.first_name} ${d.last_name}`,
            }))}
          />
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setFormOpen(false)}
              className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white"
            >
              Save
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        open={Boolean(deleting)}
        title="Delete department"
        onClose={() => !deleteMutation.isPending && setDeleting(null)}
      >
        <p className="text-sm text-[var(--text-secondary)]">
          Delete <strong>{deleting?.name}</strong>? Doctors will be unassigned
          from this department.
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
              if (selectedId === deleting.id) setSelectedId(null);
              setDeleting(null);
            }}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white"
          >
            Delete
          </button>
        </div>
      </Modal>
    </ErrorBoundary>
  );
}
