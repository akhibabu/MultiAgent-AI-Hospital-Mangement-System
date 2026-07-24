import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Appointment } from '@/types/appointment';
import { CALENDAR_EVENT_COLORS } from '@/types/appointment';
import {
  addDays,
  formatTimeLabel,
  startOfWeek,
  toDateInputValue,
} from '@/utils/appointmentValidation';

type CalendarMode = 'day' | 'week' | 'month';

interface AppointmentCalendarProps {
  items: Appointment[];
  focusDate?: string;
  onFocusDateChange?: (date: string) => void;
}

function eventColor(appt: Appointment): string {
  if (appt.visit_type === 'Emergency' && appt.status !== 'Cancelled') {
    return CALENDAR_EVENT_COLORS.Emergency;
  }
  return CALENDAR_EVENT_COLORS[appt.status];
}

function apptsOnDate(items: Appointment[], dateStr: string): Appointment[] {
  return items
    .filter((a) => a.appointment_date === dateStr)
    .sort((a, b) => a.start_time.localeCompare(b.start_time));
}

export default function AppointmentCalendar({
  items,
  focusDate,
  onFocusDateChange,
}: AppointmentCalendarProps) {
  const [mode, setMode] = useState<CalendarMode>('week');
  const [cursor, setCursor] = useState(() =>
    focusDate ? new Date(`${focusDate}T00:00:00`) : new Date(),
  );

  const focus = toDateInputValue(cursor);

  function setCursorDate(d: Date) {
    setCursor(d);
    onFocusDateChange?.(toDateInputValue(d));
  }

  const weekDays = useMemo(() => {
    const start = startOfWeek(cursor);
    return Array.from({ length: 7 }, (_, i) => addDays(start, i));
  }, [cursor]);

  const monthCells = useMemo(() => {
    const first = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
    const start = startOfWeek(first);
    return Array.from({ length: 42 }, (_, i) => addDays(start, i));
  }, [cursor]);

  function shift(delta: number) {
    if (mode === 'day') setCursorDate(addDays(cursor, delta));
    else if (mode === 'week') setCursorDate(addDays(cursor, delta * 7));
    else {
      const next = new Date(cursor);
      next.setMonth(next.getMonth() + delta);
      setCursorDate(next);
    }
  }

  return (
    <div className="space-y-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => shift(-1)}
            className="rounded-lg border border-[var(--border-color)] px-2 py-1 text-sm"
          >
            ←
          </button>
          <button
            type="button"
            onClick={() => setCursorDate(new Date())}
            className="rounded-lg border border-[var(--border-color)] px-2 py-1 text-sm"
          >
            Today
          </button>
          <button
            type="button"
            onClick={() => shift(1)}
            className="rounded-lg border border-[var(--border-color)] px-2 py-1 text-sm"
          >
            →
          </button>
          <h3 className="ml-2 text-sm font-semibold text-[var(--text-primary)]">
            {mode === 'month'
              ? cursor.toLocaleDateString(undefined, {
                  month: 'long',
                  year: 'numeric',
                })
              : mode === 'week'
                ? `Week of ${weekDays[0].toLocaleDateString()}`
                : cursor.toLocaleDateString(undefined, {
                    weekday: 'long',
                    month: 'long',
                    day: 'numeric',
                    year: 'numeric',
                  })}
          </h3>
        </div>
        <div className="flex gap-1 rounded-lg border border-[var(--border-color)] p-1">
          {(['day', 'week', 'month'] as CalendarMode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`rounded-md px-3 py-1 text-xs font-medium capitalize ${
                mode === m
                  ? 'bg-primary-600 text-white'
                  : 'text-[var(--text-secondary)] hover:bg-surface-100 dark:hover:bg-surface-800'
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-3 text-[10px] uppercase tracking-wide text-[var(--text-secondary)]">
        <span className="inline-flex items-center gap-1">
          <i className="h-2 w-2 rounded-sm bg-sky-600" /> Scheduled
        </span>
        <span className="inline-flex items-center gap-1">
          <i className="h-2 w-2 rounded-sm bg-emerald-600" /> Completed
        </span>
        <span className="inline-flex items-center gap-1">
          <i className="h-2 w-2 rounded-sm bg-rose-600" /> Cancelled
        </span>
        <span className="inline-flex items-center gap-1">
          <i className="h-2 w-2 rounded-sm bg-orange-600" /> Emergency
        </span>
        <span className="inline-flex items-center gap-1">
          <i className="h-2 w-2 rounded-sm bg-violet-600" /> Rescheduled
        </span>
      </div>

      {mode === 'day' ? (
        <DayColumn date={cursor} items={apptsOnDate(items, focus)} />
      ) : null}

      {mode === 'week' ? (
        <div className="grid gap-2 md:grid-cols-7">
          {weekDays.map((d) => {
            const key = toDateInputValue(d);
            return (
              <DayColumn
                key={key}
                date={d}
                items={apptsOnDate(items, key)}
                compact
              />
            );
          })}
        </div>
      ) : null}

      {mode === 'month' ? (
        <div className="grid grid-cols-7 gap-1">
          {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => (
            <div
              key={d}
              className="px-1 pb-1 text-center text-[10px] font-semibold uppercase text-[var(--text-secondary)]"
            >
              {d}
            </div>
          ))}
          {monthCells.map((d) => {
            const key = toDateInputValue(d);
            const inMonth = d.getMonth() === cursor.getMonth();
            const dayItems = apptsOnDate(items, key);
            return (
              <button
                key={key}
                type="button"
                onClick={() => {
                  setCursorDate(d);
                  setMode('day');
                }}
                className={`min-h-[72px] rounded-lg border border-[var(--border-color)] p-1 text-left ${
                  inMonth ? 'bg-transparent' : 'opacity-40'
                } ${key === focus ? 'ring-2 ring-primary-500' : ''}`}
              >
                <span className="text-xs font-medium text-[var(--text-primary)]">
                  {d.getDate()}
                </span>
                <div className="mt-1 space-y-0.5">
                  {dayItems.slice(0, 3).map((a) => (
                    <div
                      key={a.id}
                      className={`truncate rounded px-1 text-[9px] text-white ${eventColor(a)}`}
                    >
                      {a.start_time.slice(0, 5)}
                    </div>
                  ))}
                  {dayItems.length > 3 ? (
                    <p className="text-[9px] text-[var(--text-secondary)]">
                      +{dayItems.length - 3} more
                    </p>
                  ) : null}
                </div>
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function DayColumn({
  date,
  items,
  compact,
}: {
  date: Date;
  items: Appointment[];
  compact?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border border-[var(--border-color)] ${
        compact ? 'p-2' : 'p-3'
      }`}
    >
      <p className="text-xs font-semibold text-[var(--text-primary)]">
        {date.toLocaleDateString(undefined, {
          weekday: compact ? 'short' : 'long',
          month: 'short',
          day: 'numeric',
        })}
      </p>
      <div className={`mt-2 space-y-1.5 ${compact ? 'min-h-[120px]' : ''}`}>
        {!items.length ? (
          <p className="text-[11px] text-[var(--text-secondary)]">No appointments</p>
        ) : (
          items.map((a) => (
            <Link
              key={a.id}
              to={`/appointments/${a.id}`}
              className={`block rounded border px-2 py-1 text-white ${eventColor(a)}`}
            >
              <p className="text-[10px] font-semibold">
                {formatTimeLabel(a.start_time)}
                {!compact ? ` – ${formatTimeLabel(a.end_time)}` : ''}
              </p>
              <p className="truncate text-[11px]">
                {a.patient
                  ? `${a.patient.first_name} ${a.patient.last_name}`
                  : a.appointment_number}
              </p>
              {!compact ? (
                <p className="truncate text-[10px] opacity-90">
                  {a.visit_type} · {a.status}
                </p>
              ) : null}
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
