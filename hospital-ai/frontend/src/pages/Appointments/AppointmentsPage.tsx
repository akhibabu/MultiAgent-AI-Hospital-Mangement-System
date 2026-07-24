import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import AppointmentCalendar from '@/components/appointments/AppointmentCalendar';
import AppointmentForm from '@/components/appointments/AppointmentForm';
import AppointmentsTable from '@/components/appointments/AppointmentsTable';
import AppointmentTimeline from '@/components/appointments/AppointmentTimeline';
import Modal from '@/components/ui/Modal';
import Loading from '@/components/ui/Loading';
import ErrorState from '@/components/ui/ErrorState';
import {
  useAppointments,
  useCreateAppointment,
  useRescheduleAppointment,
  useUpdateAppointmentStatus,
} from '@/hooks/useAppointments';
import { useDepartments, useDoctors } from '@/hooks/useDoctors';
import {
  APPOINTMENT_STATUSES,
  VISIT_TYPES,
  type Appointment,
  type AppointmentFormValues,
  type AppointmentListParams,
  type AppointmentStatus,
  type VisitType,
} from '@/types/appointment';
import { toDateInputValue } from '@/utils/appointmentValidation';

type Tab = 'dashboard' | 'list' | 'calendar' | 'timeline';

export default function AppointmentsPage() {
  const [searchParams] = useSearchParams();
  const today = toDateInputValue(new Date());

  const [tab, setTab] = useState<Tab>('dashboard');
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [doctorId, setDoctorId] = useState(searchParams.get('doctorId') || '');
  const [patientId] = useState(searchParams.get('patientId') || '');
  const [departmentId, setDepartmentId] = useState('');
  const [status, setStatus] = useState<AppointmentStatus | ''>('');
  const [visitType, setVisitType] = useState<VisitType | ''>('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState('appointment_date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [formOpen, setFormOpen] = useState(false);
  const [rescheduling, setRescheduling] = useState<Appointment | null>(null);

  const { data: doctorsData } = useDoctors({ page: 1, page_size: 100 });
  const { data: deptData } = useDepartments();

  useEffect(() => {
    const t = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 350);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  const listParams: AppointmentListParams = useMemo(
    () => ({
      page,
      page_size: 10,
      search,
      doctor_id: doctorId,
      patient_id: patientId,
      department_id: departmentId,
      status,
      visit_type: visitType,
      date_from: dateFrom,
      date_to: dateTo,
      sort_by: sortBy,
      sort_order: sortOrder,
    }),
    [
      page,
      search,
      doctorId,
      patientId,
      departmentId,
      status,
      visitType,
      dateFrom,
      dateTo,
      sortBy,
      sortOrder,
    ],
  );

  const calendarParams: AppointmentListParams = useMemo(
    () => ({
      page: 1,
      page_size: 100,
      doctor_id: doctorId,
      patient_id: patientId,
      department_id: departmentId,
      status,
      visit_type: visitType,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      sort_by: 'appointment_date',
      sort_order: 'asc',
    }),
    [doctorId, patientId, departmentId, status, visitType, dateFrom, dateTo],
  );

  const todayParams: AppointmentListParams = useMemo(
    () => ({
      page: 1,
      page_size: 50,
      date_from: today,
      date_to: today,
      sort_by: 'start_time',
      sort_order: 'asc',
      doctor_id: doctorId || undefined,
    }),
    [today, doctorId],
  );

  const upcomingParams: AppointmentListParams = useMemo(
    () => ({
      page: 1,
      page_size: 20,
      date_from: today,
      status: 'Scheduled',
      sort_by: 'appointment_date',
      sort_order: 'asc',
      doctor_id: doctorId || undefined,
    }),
    [today, doctorId],
  );

  const { data, isLoading, isError, error, refetch, isFetching } =
    useAppointments(listParams);
  const calendarQuery = useAppointments(calendarParams);
  const todayQuery = useAppointments(todayParams);
  const upcomingQuery = useAppointments(upcomingParams);

  const createMutation = useCreateAppointment();
  const rescheduleMutation = useRescheduleAppointment();
  const statusMutation = useUpdateAppointmentStatus();

  function handleSort(column: string) {
    if (sortBy === column) {
      setSortOrder((p) => (p === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
    setPage(1);
  }

  async function handleCreate(values: AppointmentFormValues) {
    await createMutation.mutateAsync(values);
    setFormOpen(false);
  }

  async function handleReschedule(values: AppointmentFormValues) {
    if (!rescheduling) return;
    await rescheduleMutation.mutateAsync({
      id: rescheduling.id,
      appointment_date: values.appointment_date,
      start_time: values.start_time,
      end_time: values.end_time,
      notes: values.notes,
    });
    setRescheduling(null);
  }

  const totalPages = data?.total_pages ?? 0;
  const tabs: { id: Tab; label: string }[] = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'list', label: 'All appointments' },
    { id: 'calendar', label: 'Calendar' },
    { id: 'timeline', label: 'Timeline' },
  ];

  return (
    <ErrorBoundary title="Appointments module error">
      <section className="space-y-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
              Appointments
            </h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Book, reschedule, and track visits across doctors and patients.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              to="/appointments/schedule"
              className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] hover:bg-surface-100 dark:hover:bg-surface-800"
            >
              Doctor schedule
            </Link>
            <button
              type="button"
              onClick={() => setFormOpen(true)}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
            >
              Book appointment
            </button>
          </div>
        </header>

        <div className="flex flex-wrap gap-1 rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                tab === t.id
                  ? 'bg-primary-600 text-white'
                  : 'text-[var(--text-secondary)] hover:bg-surface-100 dark:hover:bg-surface-800'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="grid gap-3 rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4 lg:grid-cols-4 xl:grid-cols-6">
          <div className="lg:col-span-2">
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Search
            </label>
            <input
              type="search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Number, reason, or notes"
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
              Department
            </label>
            <select
              value={departmentId}
              onChange={(e) => {
                setDepartmentId(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-500"
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
              Status
            </label>
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value as AppointmentStatus | '');
                setPage(1);
              }}
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-500"
            >
              <option value="">All statuses</option>
              {APPOINTMENT_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
              Visit type
            </label>
            <select
              value={visitType}
              onChange={(e) => {
                setVisitType(e.target.value as VisitType | '');
                setPage(1);
              }}
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-500"
            >
              <option value="">All types</option>
              {VISIT_TYPES.map((v) => (
                <option key={v} value={v}>
                  {v}
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

        {tab === 'dashboard' ? (
          <div className="grid gap-4 lg:grid-cols-2">
            <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                  Today&apos;s schedule
                </h3>
                <span className="text-xs text-[var(--text-secondary)]">
                  {todayQuery.data?.total ?? 0} total
                </span>
              </div>
              {todayQuery.isLoading ? (
                <Loading message="Loading today…" />
              ) : (
                <AppointmentTimeline
                  items={todayQuery.data?.items ?? []}
                  emptyLabel="No appointments scheduled for today"
                  showPatient
                />
              )}
            </section>
            <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                  Upcoming
                </h3>
                <button
                  type="button"
                  onClick={() => setTab('calendar')}
                  className="text-xs font-medium text-primary-600 hover:underline"
                >
                  Open calendar
                </button>
              </div>
              {upcomingQuery.isLoading ? (
                <Loading message="Loading upcoming…" />
              ) : (
                <AppointmentTimeline
                  items={upcomingQuery.data?.items ?? []}
                  emptyLabel="No upcoming scheduled visits"
                  showPatient
                />
              )}
            </section>
          </div>
        ) : null}

        {tab === 'list' ? (
          <>
            {isLoading ? (
              <Loading message="Loading appointments…" />
            ) : isError ? (
              <ErrorState
                title="Unable to load appointments"
                message={
                  error instanceof Error ? error.message : 'Request failed'
                }
                onRetry={() => refetch()}
              />
            ) : (
              <>
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>
                    {data?.total ?? 0} appointments
                    {isFetching ? ' · refreshing…' : ''}
                  </span>
                </div>
                <AppointmentsTable
                  items={data?.items ?? []}
                  sortBy={sortBy}
                  sortOrder={sortOrder}
                  onSort={handleSort}
                  onEdit={(a) => setRescheduling(a)}
                  onComplete={(a) =>
                    statusMutation.mutate({ id: a.id, status: 'Completed' })
                  }
                  onCancel={(a) =>
                    statusMutation.mutate({ id: a.id, status: 'Cancelled' })
                  }
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
          </>
        ) : null}

        {tab === 'calendar' ? (
          calendarQuery.isLoading ? (
            <Loading message="Loading calendar…" />
          ) : calendarQuery.isError ? (
            <ErrorState
              title="Unable to load calendar"
              message="Could not fetch appointments for the calendar view"
              onRetry={() => calendarQuery.refetch()}
            />
          ) : (
            <AppointmentCalendar items={calendarQuery.data?.items ?? []} />
          )
        ) : null}

        {tab === 'timeline' ? (
          calendarQuery.isLoading ? (
            <Loading message="Loading timeline…" />
          ) : (
            <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5">
              <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                Appointment history
              </h3>
              <AppointmentTimeline
                items={calendarQuery.data?.items ?? []}
                emptyLabel="No appointments in range"
                showPatient
              />
            </section>
          )
        ) : null}
      </section>

      <Modal
        open={formOpen}
        title="Book appointment"
        onClose={() => setFormOpen(false)}
        wide
      >
        <AppointmentForm
          defaultPatientId={patientId || undefined}
          defaultDoctorId={doctorId || undefined}
          submitting={createMutation.isPending}
          onSubmit={handleCreate}
          onCancel={() => setFormOpen(false)}
        />
      </Modal>

      <Modal
        open={Boolean(rescheduling)}
        title="Reschedule appointment"
        onClose={() => setRescheduling(null)}
        wide
      >
        {rescheduling ? (
          <AppointmentForm
            initial={rescheduling}
            submitting={rescheduleMutation.isPending}
            submitLabel="Reschedule"
            onSubmit={handleReschedule}
            onCancel={() => setRescheduling(null)}
          />
        ) : null}
      </Modal>
    </ErrorBoundary>
  );
}
