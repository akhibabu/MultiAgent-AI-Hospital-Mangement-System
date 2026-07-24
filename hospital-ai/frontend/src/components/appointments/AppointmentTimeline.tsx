import { Link } from 'react-router-dom';
import AppointmentStatusChip from '@/components/appointments/AppointmentStatusChip';
import type { Appointment } from '@/types/appointment';
import {
  formatDateLabel,
  formatTimeLabel,
} from '@/utils/appointmentValidation';

interface AppointmentTimelineProps {
  items: Appointment[];
  emptyLabel?: string;
  showPatient?: boolean;
  showDoctor?: boolean;
}

export default function AppointmentTimeline({
  items,
  emptyLabel = 'No visits yet',
  showPatient = false,
  showDoctor = true,
}: AppointmentTimelineProps) {
  if (!items.length) {
    return (
      <p className="text-sm text-[var(--text-secondary)]">{emptyLabel}</p>
    );
  }

  const sorted = [...items].sort((a, b) => {
    const da = `${a.appointment_date}T${a.start_time}`;
    const db = `${b.appointment_date}T${b.start_time}`;
    return db.localeCompare(da);
  });

  return (
    <ol className="relative space-y-0 border-l border-[var(--border-color)] pl-5">
      {sorted.map((appt) => (
        <li key={appt.id} className="relative pb-6 last:pb-0">
          <span className="absolute -left-[1.4rem] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-primary-500 bg-[var(--bg-navbar)]" />
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <Link
                to={`/appointments/${appt.id}`}
                className="text-sm font-medium text-primary-600 hover:underline"
              >
                {appt.appointment_number}
              </Link>
              <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                {formatDateLabel(appt.appointment_date)} ·{' '}
                {formatTimeLabel(appt.start_time)} –{' '}
                {formatTimeLabel(appt.end_time)}
              </p>
              {showPatient && appt.patient ? (
                <p className="mt-1 text-sm text-[var(--text-primary)]">
                  {appt.patient.first_name} {appt.patient.last_name}
                </p>
              ) : null}
              {showDoctor && appt.doctor ? (
                <p className="mt-1 text-sm text-[var(--text-primary)]">
                  Dr. {appt.doctor.first_name} {appt.doctor.last_name}
                  {appt.doctor.specialization
                    ? ` · ${appt.doctor.specialization}`
                    : ''}
                </p>
              ) : null}
              {appt.reason_for_visit ? (
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  {appt.reason_for_visit}
                </p>
              ) : null}
            </div>
            <div className="flex flex-col items-end gap-1">
              <AppointmentStatusChip status={appt.status} />
              <span className="text-[10px] uppercase tracking-wide text-[var(--text-secondary)]">
                {appt.visit_type}
              </span>
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
