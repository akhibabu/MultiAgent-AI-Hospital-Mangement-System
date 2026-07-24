import { Link } from 'react-router-dom';
import AppointmentStatusChip from '@/components/appointments/AppointmentStatusChip';
import type { Appointment } from '@/types/appointment';
import {
  formatDateLabel,
  formatTimeLabel,
} from '@/utils/appointmentValidation';

interface AppointmentsTableProps {
  items: Appointment[];
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  onSort: (column: string) => void;
  onEdit?: (appt: Appointment) => void;
  onCancel?: (appt: Appointment) => void;
  onComplete?: (appt: Appointment) => void;
}

function SortHeader({
  label,
  column,
  sortBy,
  sortOrder,
  onSort,
}: {
  label: string;
  column: string;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  onSort: (column: string) => void;
}) {
  const active = sortBy === column;
  return (
    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
      <button
        type="button"
        onClick={() => onSort(column)}
        className="inline-flex items-center gap-1 hover:text-[var(--text-primary)]"
      >
        {label}
        {active ? (sortOrder === 'asc' ? ' ↑' : ' ↓') : ''}
      </button>
    </th>
  );
}

export default function AppointmentsTable({
  items,
  sortBy,
  sortOrder,
  onSort,
  onEdit,
  onCancel,
  onComplete,
}: AppointmentsTableProps) {
  if (!items.length) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--border-color)] px-4 py-10 text-center text-sm text-[var(--text-secondary)]">
        No appointments match these filters.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)]">
      <table className="min-w-full text-sm">
        <thead className="border-b border-[var(--border-color)] bg-surface-50/80 dark:bg-surface-900/40">
          <tr>
            <SortHeader
              label="Number"
              column="appointment_number"
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={onSort}
            />
            <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              Patient
            </th>
            <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              Doctor
            </th>
            <SortHeader
              label="Date"
              column="appointment_date"
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={onSort}
            />
            <SortHeader
              label="Time"
              column="start_time"
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={onSort}
            />
            <SortHeader
              label="Status"
              column="status"
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={onSort}
            />
            <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              Visit
            </th>
            <th className="px-3 py-2 text-right text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((appt) => (
            <tr
              key={appt.id}
              className="border-b border-[var(--border-color)] last:border-0"
            >
              <td className="px-3 py-3">
                <Link
                  to={`/appointments/${appt.id}`}
                  className="font-medium text-primary-600 hover:underline"
                >
                  {appt.appointment_number}
                </Link>
              </td>
              <td className="px-3 py-3 text-[var(--text-primary)]">
                {appt.patient
                  ? `${appt.patient.first_name} ${appt.patient.last_name}`
                  : '—'}
              </td>
              <td className="px-3 py-3 text-[var(--text-primary)]">
                {appt.doctor
                  ? `Dr. ${appt.doctor.first_name} ${appt.doctor.last_name}`
                  : '—'}
              </td>
              <td className="px-3 py-3 text-[var(--text-secondary)]">
                {formatDateLabel(appt.appointment_date)}
              </td>
              <td className="px-3 py-3 text-[var(--text-secondary)]">
                {formatTimeLabel(appt.start_time)} –{' '}
                {formatTimeLabel(appt.end_time)}
              </td>
              <td className="px-3 py-3">
                <AppointmentStatusChip status={appt.status} />
              </td>
              <td className="px-3 py-3 text-[var(--text-secondary)]">
                {appt.visit_type}
              </td>
              <td className="px-3 py-3 text-right">
                <div className="flex justify-end gap-2">
                  {onEdit &&
                  (appt.status === 'Scheduled' ||
                    appt.status === 'Rescheduled') ? (
                    <button
                      type="button"
                      onClick={() => onEdit(appt)}
                      className="text-xs font-medium text-primary-600 hover:underline"
                    >
                      Reschedule
                    </button>
                  ) : null}
                  {onComplete &&
                  (appt.status === 'Scheduled' ||
                    appt.status === 'Rescheduled') ? (
                    <button
                      type="button"
                      onClick={() => onComplete(appt)}
                      className="text-xs font-medium text-emerald-600 hover:underline"
                    >
                      Complete
                    </button>
                  ) : null}
                  {onCancel &&
                  (appt.status === 'Scheduled' ||
                    appt.status === 'Rescheduled') ? (
                    <button
                      type="button"
                      onClick={() => onCancel(appt)}
                      className="text-xs font-medium text-rose-600 hover:underline"
                    >
                      Cancel
                    </button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
