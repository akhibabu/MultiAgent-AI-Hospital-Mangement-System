import { Link } from 'react-router-dom';

const ACTIONS = [
  { label: 'Add Patient', to: '/patients', hint: 'Register a new patient' },
  { label: 'Add Doctor', to: '/doctors', hint: 'Onboard a physician' },
  {
    label: 'Book Appointment',
    to: '/appointments',
    hint: 'Schedule a visit',
  },
  {
    label: 'Upload Medical Record',
    to: '/medical-records',
    hint: 'Create EMR + files',
  },
  {
    label: 'Manage Departments',
    to: '/departments',
    hint: 'Org structure',
  },
  {
    label: 'Manage Resources',
    to: '/resources',
    hint: 'Beds, ICU, equipment',
  },
];

export default function QuickActions() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {ACTIONS.map((a) => (
        <Link
          key={a.to + a.label}
          to={a.to}
          className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4 transition hover:border-primary-500/50 hover:bg-primary-600/5"
        >
          <p className="text-sm font-semibold text-[var(--text-primary)]">
            {a.label}
          </p>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">{a.hint}</p>
        </Link>
      ))}
    </div>
  );
}
