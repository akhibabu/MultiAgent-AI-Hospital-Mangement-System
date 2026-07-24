import { Link, useNavigate, useParams } from 'react-router-dom';
import { useState } from 'react';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import AppointmentForm from '@/components/appointments/AppointmentForm';
import AppointmentStatusChip from '@/components/appointments/AppointmentStatusChip';
import Modal from '@/components/ui/Modal';
import Loading from '@/components/ui/Loading';
import ErrorState from '@/components/ui/ErrorState';
import {
  useAppointment,
  useDeleteAppointment,
  useRescheduleAppointment,
  useUpdateAppointmentStatus,
} from '@/hooks/useAppointments';
import type { AppointmentFormValues } from '@/types/appointment';
import {
  formatDateLabel,
  formatTimeLabel,
} from '@/utils/appointmentValidation';

export default function AppointmentDetailPage() {
  const { appointmentId } = useParams();
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } =
    useAppointment(appointmentId);
  const statusMutation = useUpdateAppointmentStatus();
  const rescheduleMutation = useRescheduleAppointment();
  const deleteMutation = useDeleteAppointment();
  const [rescheduleOpen, setRescheduleOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const active =
    data &&
    (data.status === 'Scheduled' || data.status === 'Rescheduled');

  async function handleReschedule(values: AppointmentFormValues) {
    if (!data) return;
    await rescheduleMutation.mutateAsync({
      id: data.id,
      appointment_date: values.appointment_date,
      start_time: values.start_time,
      end_time: values.end_time,
      notes: values.notes,
    });
    setRescheduleOpen(false);
  }

  async function handleDelete() {
    if (!data) return;
    await deleteMutation.mutateAsync(data.id);
    navigate('/appointments');
  }

  if (isLoading) return <Loading message="Loading appointment…" />;
  if (isError || !data) {
    return (
      <ErrorState
        title="Unable to load appointment"
        message={error instanceof Error ? error.message : 'Not found'}
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <ErrorBoundary title="Appointment detail error">
      <section className="mx-auto max-w-4xl space-y-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-medium text-primary-600">
              {data.appointment_number}
            </p>
            <h2 className="mt-1 text-2xl font-semibold text-[var(--text-primary)]">
              {formatDateLabel(data.appointment_date)}
            </h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              {formatTimeLabel(data.start_time)} –{' '}
              {formatTimeLabel(data.end_time)}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <AppointmentStatusChip status={data.status} />
              <span className="rounded-full bg-surface-100 px-2 py-0.5 text-xs font-medium text-[var(--text-secondary)] dark:bg-surface-800">
                {data.visit_type}
              </span>
            </div>
          </div>
          <Link
            to="/appointments"
            className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] hover:bg-surface-100 dark:hover:bg-surface-800"
          >
            Back to appointments
          </Link>
        </header>

        <div className="grid gap-4 sm:grid-cols-2">
          <InfoCard title="Patient">
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
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              {data.patient?.patient_number}
            </p>
          </InfoCard>
          <InfoCard title="Doctor">
            {data.doctor ? (
              <Link
                to={`/doctors/${data.doctor.id}`}
                className="text-sm font-medium text-primary-600 hover:underline"
              >
                Dr. {data.doctor.first_name} {data.doctor.last_name}
              </Link>
            ) : (
              <p className="text-sm">—</p>
            )}
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              {data.doctor?.specialization || data.doctor?.doctor_number}
            </p>
          </InfoCard>
          <InfoCard title="Department">
            <p className="text-sm text-[var(--text-primary)]">
              {data.department?.name || '—'}
            </p>
          </InfoCard>
          <InfoCard title="Reason">
            <p className="text-sm text-[var(--text-primary)]">
              {data.reason_for_visit || '—'}
            </p>
          </InfoCard>
        </div>

        <InfoCard title="Notes">
          <p className="whitespace-pre-wrap text-sm text-[var(--text-primary)]">
            {data.notes || '—'}
          </p>
        </InfoCard>

        <InfoCard title="Future AI activity">
          <div className="grid gap-3 sm:grid-cols-2">
            <AiPlaceholder
              label="predicted_wait_time"
              description="Estimated wait minutes from Scheduling Agent"
            />
            <AiPlaceholder
              label="priority_score"
              description="Triage priority from Emergency Agent"
            />
            <AiPlaceholder
              label="recommended_slot"
              description="Suggested alternative slots"
            />
            <AiPlaceholder
              label="ai_notes"
              description="Digital twin / agent annotations"
            />
          </div>
        </InfoCard>

        <div className="flex flex-wrap gap-2">
          {active ? (
            <>
              <button
                type="button"
                onClick={() => setRescheduleOpen(true)}
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
              >
                Reschedule
              </button>
              <button
                type="button"
                onClick={() =>
                  statusMutation.mutate({ id: data.id, status: 'Completed' })
                }
                className="rounded-lg border border-emerald-600/40 px-4 py-2 text-sm font-medium text-emerald-700 dark:text-emerald-300"
              >
                Mark completed
              </button>
              <button
                type="button"
                onClick={() =>
                  statusMutation.mutate({ id: data.id, status: 'No Show' })
                }
                className="rounded-lg border border-amber-600/40 px-4 py-2 text-sm font-medium text-amber-800 dark:text-amber-300"
              >
                Mark no show
              </button>
              <button
                type="button"
                onClick={() =>
                  statusMutation.mutate({ id: data.id, status: 'Cancelled' })
                }
                className="rounded-lg border border-rose-600/40 px-4 py-2 text-sm font-medium text-rose-700 dark:text-rose-300"
              >
                Cancel
              </button>
            </>
          ) : null}
          <button
            type="button"
            onClick={() => setDeleteOpen(true)}
            className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)]"
          >
            Delete
          </button>
        </div>
      </section>

      <Modal
        open={rescheduleOpen}
        title="Reschedule appointment"
        onClose={() => setRescheduleOpen(false)}
        wide
      >
        <AppointmentForm
          initial={data}
          submitting={rescheduleMutation.isPending}
          submitLabel="Save new time"
          onSubmit={handleReschedule}
          onCancel={() => setRescheduleOpen(false)}
        />
      </Modal>

      <Modal
        open={deleteOpen}
        title="Delete appointment?"
        onClose={() => setDeleteOpen(false)}
      >
        <p className="text-sm text-[var(--text-secondary)]">
          This permanently removes {data.appointment_number}. Prefer cancel
          when you need to keep history.
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
            onClick={handleDelete}
            className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white"
          >
            {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </Modal>
    </ErrorBoundary>
  );
}

function InfoCard({
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

function AiPlaceholder({
  label,
  description,
}: {
  label: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border border-dashed border-[var(--border-color)] bg-surface-50/60 px-4 py-3 dark:bg-surface-900/30">
      <p className="font-mono text-xs text-[var(--text-primary)]">{label}</p>
      <p className="mt-1 text-xs text-[var(--text-secondary)]">{description}</p>
      <p className="mt-2 font-mono text-[10px] uppercase tracking-wider text-[var(--text-secondary)]">
        Coming soon · AI agent extension
      </p>
    </div>
  );
}
