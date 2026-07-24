import { Link } from 'react-router-dom';
import AppointmentTimeline from '@/components/appointments/AppointmentTimeline';
import Loading from '@/components/ui/Loading';
import { useAppointments } from '@/hooks/useAppointments';
import { toDateInputValue } from '@/utils/appointmentValidation';

export default function PatientAppointmentHistory({
  patientId,
}: {
  patientId: string;
}) {
  const today = toDateInputValue(new Date());

  const allQuery = useAppointments({
    page: 1,
    page_size: 100,
    patient_id: patientId,
    sort_by: 'appointment_date',
    sort_order: 'desc',
  });

  const items = allQuery.data?.items ?? [];
  const upcoming = items.filter(
    (a) =>
      (a.status === 'Scheduled' || a.status === 'Rescheduled') &&
      a.appointment_date >= today,
  );
  const previous = items.filter(
    (a) => a.status === 'Completed' || a.appointment_date < today,
  );
  const cancelled = items.filter((a) => a.status === 'Cancelled');
  const noShows = items.filter((a) => a.status === 'No Show');

  if (allQuery.isLoading) {
    return <Loading message="Loading visits…" />;
  }

  return (
    <div className="space-y-6 lg:col-span-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Appointment history
        </h3>
        <Link
          to={`/appointments?patientId=${patientId}`}
          className="text-xs font-medium text-primary-600 hover:underline"
        >
          View in appointments
        </Link>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5">
          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            Upcoming visits
          </h4>
          <AppointmentTimeline
            items={upcoming}
            emptyLabel="No upcoming visits"
            showDoctor
            showPatient={false}
          />
        </section>
        <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5">
          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            Previous visits
          </h4>
          <AppointmentTimeline
            items={previous.filter((a) => a.status === 'Completed')}
            emptyLabel="No completed visits"
            showDoctor
            showPatient={false}
          />
        </section>
        <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5">
          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            Cancelled
          </h4>
          <AppointmentTimeline
            items={cancelled}
            emptyLabel="No cancellations"
            showDoctor
            showPatient={false}
          />
        </section>
        <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5">
          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            No shows
          </h4>
          <AppointmentTimeline
            items={noShows}
            emptyLabel="No no-shows recorded"
            showDoctor
            showPatient={false}
          />
        </section>
      </div>

      <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5">
        <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Timeline
        </h4>
        <AppointmentTimeline
          items={items}
          emptyLabel="No appointment history yet"
          showDoctor
          showPatient={false}
        />
      </section>
    </div>
  );
}
