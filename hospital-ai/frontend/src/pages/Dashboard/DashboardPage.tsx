import ErrorBoundary from '@/components/common/ErrorBoundary';
import ActivityList from '@/components/dashboard/ActivityList';
import KpiCard from '@/components/dashboard/KpiCard';
import QuickActions from '@/components/dashboard/QuickActions';
import SimpleChart from '@/components/dashboard/SimpleChart';
import Loading from '@/components/ui/Loading';
import ErrorState from '@/components/ui/ErrorState';
import {
  useDashboardCharts,
  useDashboardResourceSummary,
  useDashboardStatistics,
  useRecentActivities,
  useUpcomingDashboardAppointments,
} from '@/hooks/useHospital';
import { Link } from 'react-router-dom';

export default function DashboardPage() {
  const stats = useDashboardStatistics();
  const charts = useDashboardCharts();
  const activities = useRecentActivities();
  const upcoming = useUpcomingDashboardAppointments();
  const resources = useDashboardResourceSummary();

  const loading =
    stats.isLoading || charts.isLoading || activities.isLoading;

  if (loading) {
    return <Loading message="Loading hospital dashboard…" />;
  }

  if (stats.isError) {
    return (
      <ErrorState
        title="Unable to load dashboard"
        message="Statistics could not be fetched"
        onRetry={() => stats.refetch()}
      />
    );
  }

  const s = stats.data!;
  const c = charts.data;

  return (
    <ErrorBoundary title="Dashboard error">
      <section className="space-y-6">
        <header>
          <h2 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            Hospital Administration
          </h2>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Operational visibility across patients, clinicians, appointments,
            records, and resources.
          </p>
        </header>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard
            label="Total Patients"
            value={s.total_patients}
            to="/patients"
          />
          <KpiCard
            label="Total Doctors"
            value={s.total_doctors}
            to="/doctors"
          />
          <KpiCard
            label="Today's Appointments"
            value={s.todays_appointments}
            to="/appointments"
          />
          <KpiCard
            label="Available Beds"
            value={s.available_beds}
            to="/resources"
          />
          <KpiCard
            label="ICU Occupancy"
            value={`${s.icu_occupancy_pct}%`}
            to="/resources"
          />
          <KpiCard
            label="Departments"
            value={s.total_departments}
            to="/departments"
          />
          <KpiCard
            label="Medical Records"
            value={s.medical_records_uploaded}
            to="/medical-records"
          />
          <KpiCard
            label="Available Resources"
            value={s.available_resources}
            to="/resources"
          />
        </div>

        <div>
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            Quick actions
          </h3>
          <QuickActions />
        </div>

        {c ? (
          <div className="grid gap-4 lg:grid-cols-2">
            <SimpleChart
              title="Appointments per day"
              data={c.appointments_per_day}
              type="line"
            />
            <SimpleChart
              title="Appointment status distribution"
              data={c.appointment_status_distribution}
              type="pie"
            />
            <SimpleChart
              title="Patients / visits per department"
              data={c.patients_per_department}
            />
            <SimpleChart
              title="Doctor distribution"
              data={c.doctor_distribution}
            />
            <SimpleChart
              title="Bed utilization"
              data={c.bed_utilization}
            />
            <SimpleChart
              title="Monthly patient registration"
              data={c.monthly_patient_registration}
              type="line"
            />
          </div>
        ) : null}

        <div className="grid gap-4 lg:grid-cols-3">
          <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4 lg:col-span-1">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                Resource snapshot
              </h3>
              <Link
                to="/resources"
                className="text-xs text-primary-600 hover:underline"
              >
                Manage
              </Link>
            </div>
            {resources.data ? (
              <dl className="space-y-2 text-sm">
                <Row
                  label="Beds"
                  value={`${resources.data.available_beds}/${resources.data.total_beds}`}
                />
                <Row
                  label="ICU"
                  value={`${resources.data.available_icu}/${resources.data.total_icu}`}
                />
                <Row
                  label="Operation theatres"
                  value={resources.data.operation_theatres}
                />
                <Row
                  label="Ventilators available"
                  value={resources.data.ventilators_available}
                />
                <Row
                  label="Laboratories"
                  value={resources.data.laboratories}
                />
              </dl>
            ) : (
              <p className="text-sm text-[var(--text-secondary)]">
                No resource data
              </p>
            )}
          </section>

          <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4 lg:col-span-2">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                Upcoming appointments
              </h3>
              <Link
                to="/appointments"
                className="text-xs text-primary-600 hover:underline"
              >
                View all
              </Link>
            </div>
            {!upcoming.data?.items.length ? (
              <p className="text-sm text-[var(--text-secondary)]">
                No upcoming appointments
              </p>
            ) : (
              <ul className="divide-y divide-[var(--border-color)]">
                {upcoming.data.items.map((a) => (
                  <li key={a.id} className="flex flex-wrap justify-between gap-2 py-2 text-sm">
                    <Link
                      to={`/appointments/${a.id}`}
                      className="font-medium text-primary-600 hover:underline"
                    >
                      {a.appointment_number}
                    </Link>
                    <span className="text-[var(--text-secondary)]">
                      {a.appointment_date} {a.start_time}
                    </span>
                    <span className="w-full text-[var(--text-primary)]">
                      {a.patient_name} · {a.doctor_name}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        {activities.data ? (
          <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
            <ActivityList
              title="New patients"
              items={activities.data.new_patients}
            />
            <ActivityList
              title="New doctors"
              items={activities.data.new_doctors}
            />
            <ActivityList
              title="Recent medical records"
              items={activities.data.recent_medical_records}
            />
            <ActivityList
              title="Today's appointments"
              items={activities.data.todays_appointments}
            />
            <ActivityList
              title="Recently updated records"
              items={activities.data.recently_updated_records}
            />
          </div>
        ) : null}
      </section>
    </ErrorBoundary>
  );
}

function Row({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="flex justify-between gap-2">
      <dt className="text-[var(--text-secondary)]">{label}</dt>
      <dd className="font-medium text-[var(--text-primary)]">{value}</dd>
    </div>
  );
}
