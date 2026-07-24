import { Link, useSearchParams } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import AppointmentCalendar from '@/components/appointments/AppointmentCalendar';
import AppointmentTimeline from '@/components/appointments/AppointmentTimeline';
import Loading from '@/components/ui/Loading';
import ErrorState from '@/components/ui/ErrorState';
import { useAppointments } from '@/hooks/useAppointments';
import { useDoctor, useDoctorAvailability, useDoctors } from '@/hooks/useDoctors';
import { DAY_LABELS } from '@/types/appointment';
import {
  addDays,
  formatTimeLabel,
  startOfWeek,
  toDateInputValue,
} from '@/utils/appointmentValidation';

export default function DoctorSchedulePage() {
  const [params, setParams] = useSearchParams();
  const doctorId = params.get('doctorId') || '';
  const { data: doctorsData } = useDoctors({ page: 1, page_size: 100 });
  const { data: doctor } = useDoctor(doctorId || undefined);
  const { data: availability } = useDoctorAvailability(doctorId || undefined);
  const availItems = availability ?? [];

  const today = toDateInputValue(new Date());
  const weekStart = startOfWeek(new Date());
  const weekEnd = toDateInputValue(addDays(weekStart, 6));

  const todayQuery = useAppointments({
    page: 1,
    page_size: 50,
    doctor_id: doctorId || undefined,
    date_from: today,
    date_to: today,
    sort_by: 'start_time',
    sort_order: 'asc',
  });

  const weekQuery = useAppointments({
    page: 1,
    page_size: 100,
    doctor_id: doctorId || undefined,
    date_from: toDateInputValue(weekStart),
    date_to: weekEnd,
    sort_by: 'appointment_date',
    sort_order: 'asc',
  });

  const upcomingQuery = useAppointments({
    page: 1,
    page_size: 30,
    doctor_id: doctorId || undefined,
    date_from: today,
    status: 'Scheduled',
    sort_by: 'appointment_date',
    sort_order: 'asc',
  });

  const completedQuery = useAppointments({
    page: 1,
    page_size: 20,
    doctor_id: doctorId || undefined,
    status: 'Completed',
    sort_by: 'appointment_date',
    sort_order: 'desc',
  });

  const cancelledQuery = useAppointments({
    page: 1,
    page_size: 20,
    doctor_id: doctorId || undefined,
    status: 'Cancelled',
    sort_by: 'appointment_date',
    sort_order: 'desc',
  });

  return (
    <ErrorBoundary title="Doctor schedule error">
      <section className="space-y-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
              Doctor schedule
            </h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Today, weekly calendar, availability, and visit history for a physician.
            </p>
          </div>
          <Link
            to="/appointments"
            className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)]"
          >
            Back to appointments
          </Link>
        </header>

        <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4">
          <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
            Select doctor
          </label>
          <select
            value={doctorId}
            onChange={(e) => {
              const next = new URLSearchParams(params);
              if (e.target.value) next.set('doctorId', e.target.value);
              else next.delete('doctorId');
              setParams(next);
            }}
            className="w-full max-w-md rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-500"
          >
            <option value="">Choose a doctor</option>
            {(doctorsData?.items ?? []).map((d) => (
              <option key={d.id} value={d.id}>
                Dr. {d.first_name} {d.last_name} — {d.specialization}
              </option>
            ))}
          </select>
          {doctor ? (
            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              {doctor.doctor_number} · {doctor.availability_status}
              {doctor.department ? ` · ${doctor.department.name}` : ''}
            </p>
          ) : null}
        </div>

        {!doctorId ? (
          <p className="text-sm text-[var(--text-secondary)]">
            Select a doctor to view their schedule.
          </p>
        ) : (
          <>
            <div className="grid gap-4 lg:grid-cols-2">
              <Panel title="Today's appointments">
                {todayQuery.isLoading ? (
                  <Loading message="Loading…" />
                ) : todayQuery.isError ? (
                  <ErrorState
                    title="Failed to load"
                    message="Could not load today's appointments"
                    onRetry={() => todayQuery.refetch()}
                  />
                ) : (
                  <AppointmentTimeline
                    items={todayQuery.data?.items ?? []}
                    emptyLabel="No appointments today"
                    showPatient
                    showDoctor={false}
                  />
                )}
              </Panel>

              <Panel title="Availability">
                {!availItems.length ? (
                  <p className="text-sm text-[var(--text-secondary)]">
                    No availability windows.{' '}
                    <Link
                      to={`/availability?doctorId=${doctorId}`}
                      className="text-primary-600 hover:underline"
                    >
                      Configure availability
                    </Link>
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {availItems.map((slot) => (
                      <li
                        key={slot.id}
                        className="flex justify-between gap-2 text-sm text-[var(--text-primary)]"
                      >
                        <span>{DAY_LABELS[slot.day_of_week] ?? slot.day_of_week}</span>
                        <span className="text-[var(--text-secondary)]">
                          {formatTimeLabel(String(slot.start_time))} –{' '}
                          {formatTimeLabel(String(slot.end_time))}
                          <span className="ml-2 text-xs">
                            ({slot.slot_duration}m)
                          </span>
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
                <div className="mt-4 rounded-lg border border-dashed border-[var(--border-color)] px-3 py-2">
                  <p className="font-mono text-xs text-[var(--text-primary)]">
                    doctor.schedule_score
                  </p>
                  <p className="mt-1 text-xs text-[var(--text-secondary)]">
                    Reserved for Scheduling Agent — unused.
                  </p>
                </div>
              </Panel>
            </div>

            <Panel title="Weekly schedule">
              {weekQuery.isLoading ? (
                <Loading message="Loading week…" />
              ) : (
                <AppointmentCalendar items={weekQuery.data?.items ?? []} />
              )}
            </Panel>

            <div className="grid gap-4 lg:grid-cols-3">
              <Panel title="Upcoming">
                <AppointmentTimeline
                  items={upcomingQuery.data?.items ?? []}
                  emptyLabel="None upcoming"
                  showPatient
                  showDoctor={false}
                />
              </Panel>
              <Panel title="Completed">
                <AppointmentTimeline
                  items={completedQuery.data?.items ?? []}
                  emptyLabel="No completed visits"
                  showPatient
                  showDoctor={false}
                />
              </Panel>
              <Panel title="Cancelled">
                <AppointmentTimeline
                  items={cancelledQuery.data?.items ?? []}
                  emptyLabel="No cancellations"
                  showPatient
                  showDoctor={false}
                />
              </Panel>
            </div>
          </>
        )}
      </section>
    </ErrorBoundary>
  );
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
        {title}
      </h3>
      {children}
    </section>
  );
}
