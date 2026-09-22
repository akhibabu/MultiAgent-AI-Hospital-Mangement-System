import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import Badge, { type BadgeTone } from '@/components/common/Badge';
import Card from '@/components/common/Card';
import Loading from '@/components/ui/Loading';
import {
  useSchedulingResult,
  useStartScheduling,
} from '@/hooks/useScheduling';
import { usePatients } from '@/hooks/usePatients';
import { useDepartments, useDoctors } from '@/hooks/useDoctors';
import { useCreateAppointment } from '@/hooks/useAppointments';
import { getApiErrorMessage } from '@/services/apiClient';
import {
  APPOINTMENT_STATUSES,
  VISIT_TYPES,
  type AppointmentFormValues,
} from '@/types/appointment';
import type {
  SchedulingStartResult,
  SchedulingResult,
  SlotRecommendation,
} from '@/types/scheduling';
import {
  addDays,
  formatDateLabel,
  formatTimeLabel,
  toDateInputValue,
} from '@/utils/appointmentValidation';

const STAGES = [
  'Doctor Assignment',
  'Appointment Scheduling',
  'Surgery Scheduling',
  'Follow-Up Planning',
  'Queue Optimization',
  'Workload Balancing',
];

function tone(level?: string | null): BadgeTone {
  if (!level) return 'gray';
  if (level === 'Critical' || level === 'High') return 'red';
  if (level === 'Urgent' || level === 'Moderate') return 'amber';
  if (level === 'Semi-Urgent') return 'blue';
  return 'green';
}

function normalizeResult(
  live: SchedulingStartResult | undefined,
  persisted: SchedulingResult | undefined,
): {
  doctor_assignment: SchedulingResult['doctor_assignment_json'] | undefined;
  appointment_scheduling: SchedulingResult['appointment_scheduling_json'] | undefined;
  surgery_scheduling: SchedulingResult['surgery_scheduling_json'] | undefined;
  follow_up_planning: SchedulingResult['follow_up_planning_json'] | undefined;
  queue_optimization: SchedulingResult['queue_optimization_json'] | undefined;
  workload_balancing: SchedulingResult['workload_balancing_json'] | undefined;
  summary: string | null | undefined;
  warnings: string[];
  emergency_priority_level: string;
  emergency_priority_score: number;
} {
  if (live) {
    return {
      doctor_assignment: live.doctor_assignment,
      appointment_scheduling: live.appointment_scheduling,
      surgery_scheduling: live.surgery_scheduling,
      follow_up_planning: live.follow_up_planning,
      queue_optimization: live.queue_optimization,
      workload_balancing: live.workload_balancing,
      summary: live.summary,
      warnings: live.warnings,
      emergency_priority_level: live.emergency_priority_level,
      emergency_priority_score: live.emergency_priority_score,
    };
  }
  return {
    doctor_assignment: persisted?.doctor_assignment_json,
    appointment_scheduling: persisted?.appointment_scheduling_json,
    surgery_scheduling: persisted?.surgery_scheduling_json,
    follow_up_planning: persisted?.follow_up_planning_json,
    queue_optimization: persisted?.queue_optimization_json,
    workload_balancing: persisted?.workload_balancing_json,
    summary: persisted?.summary,
    warnings: persisted?.warnings_json ?? [],
    emergency_priority_level: 'Routine',
    emergency_priority_score: 0,
  };
}

export default function SchedulingAgentPage() {
  const tomorrow = useMemo(() => toDateInputValue(addDays(new Date(), 1)), []);
  const [patientId, setPatientId] = useState('');
  const [preferredDate, setPreferredDate] = useState(tomorrow);
  const [visitType, setVisitType] = useState<(typeof VISIT_TYPES)[number]>('Consultation');
  const [departmentId, setDepartmentId] = useState('');
  const [preferredDoctorId, setPreferredDoctorId] = useState('');
  const [reason, setReason] = useState('');
  const [surgeryRequired, setSurgeryRequired] = useState(false);
  const [surgeryDuration, setSurgeryDuration] = useState('120');
  const [followUpDays, setFollowUpDays] = useState('14');

  const patientsQuery = usePatients({
    page: 1,
    page_size: 100,
    sort_by: 'created_at',
    sort_order: 'desc',
  });
  const doctorsQuery = useDoctors({
    page: 1,
    page_size: 100,
    sort_by: 'last_name',
    sort_order: 'asc',
  });
  const departmentsQuery = useDepartments();
  const resultQuery = useSchedulingResult(patientId || undefined);
  const startMutation = useStartScheduling();
  const createAppointment = useCreateAppointment();

  const live = startMutation.data;
  const persisted = resultQuery.data;
  const data = normalizeResult(live, persisted);
  const hasResult = Boolean(live || persisted);

  async function handleRun() {
    if (!patientId) return;
    await startMutation.mutateAsync({
      patient_id: patientId,
      preferred_date: preferredDate,
      visit_type: visitType,
      reason_for_visit: reason.trim() || null,
      department_id: departmentId || null,
      preferred_doctor_id: preferredDoctorId || null,
      surgery_required: surgeryRequired,
      surgery_duration_minutes: Number(surgeryDuration) || 120,
      follow_up_days: Number(followUpDays) || 14,
    });
  }

  async function handleBook(slot: SlotRecommendation) {
    const department = data.doctor_assignment?.candidates.find(
      (c) => c.doctor_id === slot.doctor_id,
    )?.department_id;
    const values: AppointmentFormValues = {
      patient_id: patientId,
      doctor_id: slot.doctor_id,
      department_id: department || departmentId || '',
      appointment_date: slot.appointment_date,
      start_time: slot.start_time.slice(0, 5),
      end_time: slot.end_time.slice(0, 5),
      visit_type: visitType,
      reason_for_visit: reason.trim(),
      notes: 'Booked from Scheduling Agent recommendation.',
      status: APPOINTMENT_STATUSES[0],
    };
    await createAppointment.mutateAsync(values);
  }

  return (
    <ErrorBoundary title="Scheduling Agent error">
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary-600">
                AI Center · Hospital Operations
              </p>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[var(--text-primary)]">
                Scheduling Agent
              </h1>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[var(--text-secondary)]">
                Assigns doctors, finds open appointment windows, prepares surgery and
                follow-up plans, recommends queue ordering, and balances workload.
                Booking remains an explicit staff action.
              </p>
            </div>
            <Link
              to="/ai"
              className="rounded-xl border border-[var(--border-color)] px-3 py-2 text-sm text-[var(--text-secondary)]"
            >
              Back to AI Center
            </Link>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Status</p>
              <p className="mt-1 text-sm font-semibold">
                {startMutation.isPending ? 'Running' : hasResult ? 'Completed' : 'Not started'}
              </p>
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Emergency priority</p>
              {hasResult ? (
                <Badge tone={tone(data.emergency_priority_level)}>
                  {data.emergency_priority_level} · {data.emergency_priority_score}/100
                </Badge>
              ) : (
                <p className="mt-1 text-sm font-semibold">—</p>
              )}
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Assigned doctor</p>
              <p className="mt-1 text-sm font-semibold">
                {data.doctor_assignment?.selected_doctor_name || '—'}
              </p>
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Recommended slot</p>
              {data.appointment_scheduling?.recommended_slot ? (
                <p className="mt-1 text-sm font-semibold">
                  {formatDateLabel(data.appointment_scheduling.recommended_slot.appointment_date)}
                  <br />
                  <span className="text-xs font-normal">
                    {formatTimeLabel(data.appointment_scheduling.recommended_slot.start_time)}
                  </span>
                </p>
              ) : (
                <p className="mt-1 text-sm font-semibold">—</p>
              )}
            </Card>
          </div>
        </header>

        <Card>
          <div className="grid gap-4 lg:grid-cols-6">
            <label className="lg:col-span-2 text-sm">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Patient</span>
              {patientsQuery.isLoading ? (
                <Loading message="Loading patients…" />
              ) : (
                <select
                  value={patientId}
                  onChange={(e) => setPatientId(e.target.value)}
                  className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5"
                >
                  <option value="">Select a patient…</option>
                  {(patientsQuery.data?.items ?? []).map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.first_name} {p.last_name}
                      {p.patient_number ? ` (${p.patient_number})` : ''}
                    </option>
                  ))}
                </select>
              )}
            </label>

            <label className="text-sm">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Preferred date</span>
              <input
                type="date"
                value={preferredDate}
                onChange={(e) => setPreferredDate(e.target.value)}
                className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5"
              />
            </label>

            <label className="text-sm">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Visit type</span>
              <select
                value={visitType}
                onChange={(e) => setVisitType(e.target.value as typeof visitType)}
                className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5"
              >
                {VISIT_TYPES.map((type) => <option key={type}>{type}</option>)}
              </select>
            </label>

            <label className="text-sm">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Department</span>
              <select
                value={departmentId}
                onChange={(e) => setDepartmentId(e.target.value)}
                className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5"
              >
                <option value="">Auto-select</option>
                {(departmentsQuery.data?.items ?? []).map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </label>

            <label className="text-sm">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Preferred doctor</span>
              <select
                value={preferredDoctorId}
                onChange={(e) => setPreferredDoctorId(e.target.value)}
                className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5"
              >
                <option value="">Auto-select</option>
                {(doctorsQuery.data?.items ?? []).map((d) => (
                  <option key={d.id} value={d.id}>Dr. {d.first_name} {d.last_name}</option>
                ))}
              </select>
            </label>

            <label className="text-sm lg:col-span-3">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Reason for visit</span>
              <input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Optional scheduling context"
                className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5"
              />
            </label>

            <label className="flex items-center gap-2 text-sm lg:col-span-1">
              <input
                type="checkbox"
                checked={surgeryRequired}
                onChange={(e) => setSurgeryRequired(e.target.checked)}
              />
              Surgery required
            </label>

            <label className="text-sm">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Surgery duration</span>
              <input
                type="number"
                min={30}
                max={480}
                step={30}
                value={surgeryDuration}
                onChange={(e) => setSurgeryDuration(e.target.value)}
                disabled={!surgeryRequired}
                className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5 disabled:opacity-50"
              />
            </label>

            <label className="text-sm">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Follow-up days</span>
              <input
                type="number"
                min={1}
                max={180}
                value={followUpDays}
                onChange={(e) => setFollowUpDays(e.target.value)}
                className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5"
              />
            </label>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              disabled={!patientId || startMutation.isPending}
              onClick={handleRun}
              className="rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {startMutation.isPending ? 'Running Scheduling Agent…' : 'Run Scheduling Agent'}
            </button>
            {resultQuery.isFetching ? (
              <span className="text-xs text-[var(--text-secondary)]">Loading saved result…</span>
            ) : null}
          </div>

          {startMutation.isError ? (
            <p className="mt-3 text-sm text-red-600">
              {getApiErrorMessage(startMutation.error, 'Scheduling Agent failed')}
            </p>
          ) : null}
        </Card>

        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          <Card>
            <h2 className="text-sm font-semibold">Workflow</h2>
            <ol className="mt-5 space-y-3">
              {STAGES.map((stage, index) => (
                <li key={stage} className="flex gap-3">
                  <span
                    className={
                      hasResult
                        ? 'flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-[10px] font-bold text-white'
                        : 'flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[var(--border-color)] text-[10px] text-[var(--text-secondary)]'
                    }
                  >
                    {hasResult ? '✓' : index + 1}
                  </span>
                  <span className="text-sm">{stage}</span>
                </li>
              ))}
            </ol>
          </Card>

          <div className="space-y-6">
            {!patientId ? (
              <Card>
                <p className="text-sm text-[var(--text-secondary)]">
                  Select a patient to load a previous scheduling result or generate a new plan.
                </p>
              </Card>
            ) : null}

            {hasResult ? (
              <>
                <Card>
                  <h2 className="text-sm font-semibold">Scheduling Summary</h2>
                  <p className="mt-2 text-sm leading-relaxed">{data.summary}</p>
                  {data.warnings.length ? (
                    <ul className="mt-3 space-y-1 text-sm text-amber-800 dark:text-amber-200">
                      {data.warnings.map((warning) => <li key={warning}>• {warning}</li>)}
                    </ul>
                  ) : null}
                </Card>

                <Card>
                  <h2 className="text-sm font-semibold">1. Doctor Assignment</h2>
                  <p className="mt-1 text-xs text-[var(--text-secondary)]">
                    Selected: {data.doctor_assignment?.selected_doctor_name || 'No doctor'}
                    {' · '}score {data.doctor_assignment?.selection_score ?? 0}/100
                  </p>
                  <div className="mt-4 grid gap-3">
                    {(data.doctor_assignment?.candidates ?? []).map((candidate) => (
                      <div key={candidate.doctor_id} className="rounded-xl border border-[var(--border-color)] p-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div>
                            <p className="text-sm font-semibold">{candidate.doctor_name}</p>
                            <p className="text-xs text-[var(--text-secondary)]">
                              {candidate.specialization}
                              {candidate.department_name ? ` · ${candidate.department_name}` : ''}
                            </p>
                          </div>
                          <Badge tone={tone(candidate.availability_status)}>{candidate.score}/100</Badge>
                        </div>
                        <p className="mt-2 text-xs text-[var(--text-secondary)]">
                          Workload: {candidate.workload_count} active appointment(s) in the horizon
                        </p>
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {candidate.reasons.slice(0, 5).map((r) => (
                            <span key={r} className="rounded-md bg-black/5 px-2 py-1 text-[11px] dark:bg-white/5">{r}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>

                <Card>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <h2 className="text-sm font-semibold">2. Appointment Scheduling</h2>
                      <p className="mt-1 text-xs text-[var(--text-secondary)]">
                        {data.appointment_scheduling?.booking_status}
                      </p>
                    </div>
                    {data.appointment_scheduling?.recommended_slot ? (
                      <button
                        type="button"
                        disabled={createAppointment.isPending}
                        onClick={() => handleBook(data.appointment_scheduling!.recommended_slot!)}
                        className="rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
                      >
                        {createAppointment.isPending ? 'Booking…' : 'Book recommended slot'}
                      </button>
                    ) : null}
                  </div>

                  {data.appointment_scheduling?.recommended_slot ? (
                    <div className="mt-4 rounded-xl border border-primary-500/40 bg-primary-500/5 p-4">
                      <p className="text-sm font-semibold">
                        {formatDateLabel(data.appointment_scheduling.recommended_slot.appointment_date)}
                        {' · '}
                        {formatTimeLabel(data.appointment_scheduling.recommended_slot.start_time)}
                        {'–'}
                        {formatTimeLabel(data.appointment_scheduling.recommended_slot.end_time)}
                      </p>
                      <p className="mt-1 text-xs text-[var(--text-secondary)]">
                        {data.appointment_scheduling.recommended_slot.doctor_name}
                        {' · score '}
                        {data.appointment_scheduling.recommended_slot.score}
                      </p>
                    </div>
                  ) : (
                    <p className="mt-4 text-sm text-[var(--text-secondary)]">
                      No open appointment slot found in the planning horizon.
                    </p>
                  )}

                  {(data.appointment_scheduling?.alternatives ?? []).length ? (
                    <div className="mt-4">
                      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Alternatives</p>
                      <div className="mt-2 grid gap-2 md:grid-cols-2">
                        {data.appointment_scheduling!.alternatives.map((slot) => (
                          <button
                            type="button"
                            key={slot.appointment_date + slot.start_time}
                            onClick={() => handleBook(slot)}
                            disabled={createAppointment.isPending}
                            className="rounded-lg border border-[var(--border-color)] p-3 text-left hover:border-primary-500/50 disabled:opacity-50"
                          >
                            <p className="text-sm font-medium">
                              {formatDateLabel(slot.appointment_date)} · {formatTimeLabel(slot.start_time)}
                            </p>
                            <p className="mt-1 text-xs text-[var(--text-secondary)]">{slot.doctor_name}</p>
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </Card>

                <div className="grid gap-4 md:grid-cols-2">
                  <Card>
                    <h2 className="text-sm font-semibold">3. Surgery Scheduling</h2>
                    <p className="mt-2 text-sm">
                      {data.surgery_scheduling?.required ? 'Surgery planning requested' : 'No surgery requested'}
                    </p>
                    {data.surgery_scheduling?.recommended_slot ? (
                      <p className="mt-3 text-sm">
                        {formatDateLabel(data.surgery_scheduling.recommended_slot.appointment_date)}
                        {' · '}
                        {formatTimeLabel(data.surgery_scheduling.recommended_slot.start_time)}
                      </p>
                    ) : null}
                    <p className="mt-3 text-xs text-[var(--text-secondary)]">
                      {data.surgery_scheduling?.operation_theatre_status}
                    </p>
                    <ul className="mt-3 space-y-1 text-xs text-[var(--text-secondary)]">
                      {(data.surgery_scheduling?.notes ?? []).map((n) => <li key={n}>• {n}</li>)}
                    </ul>
                  </Card>

                  <Card>
                    <h2 className="text-sm font-semibold">4. Follow-Up Planning</h2>
                    <p className="mt-3 text-sm">
                      Recommended date:{' '}
                      <strong>{data.follow_up_planning?.recommended_date
                        ? formatDateLabel(data.follow_up_planning.recommended_date)
                        : '—'}</strong>
                    </p>
                    <p className="mt-2 text-sm">
                      Interval: <strong>{data.follow_up_planning?.interval_days ?? '—'} day(s)</strong>
                    </p>
                    <p className="mt-2 text-xs text-[var(--text-secondary)]">
                      {data.follow_up_planning?.reason}
                    </p>
                  </Card>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <Card>
                    <h2 className="text-sm font-semibold">5. Queue Optimization</h2>
                    <p className="mt-1 text-xs text-[var(--text-secondary)]">
                      {data.queue_optimization?.changed_order_count ?? 0} position change(s) recommended
                    </p>
                    <div className="mt-4 space-y-2">
                      {(data.queue_optimization?.ordered_queue ?? []).map((item) => (
                        <div key={item.appointment_id} className="flex items-center justify-between gap-3 rounded-lg border border-[var(--border-color)] p-3">
                          <div className="min-w-0">
                            <p className="text-sm font-medium">
                              #{item.position} · {item.patient_name}
                            </p>
                            <p className="text-xs text-[var(--text-secondary)]">
                              {formatTimeLabel(item.start_time)}–{formatTimeLabel(item.end_time)}
                            </p>
                          </div>
                          <Badge tone={tone(item.priority_level)}>
                            {item.priority_level} · {item.priority_score}
                          </Badge>
                        </div>
                      ))}
                      {!data.queue_optimization?.ordered_queue?.length ? (
                        <p className="text-sm text-[var(--text-secondary)]">
                          No existing appointments for the selected doctor/date.
                        </p>
                      ) : null}
                    </div>
                    <ul className="mt-3 space-y-1 text-xs text-[var(--text-secondary)]">
                      {(data.queue_optimization?.rationale ?? []).map((r) => <li key={r}>• {r}</li>)}
                    </ul>
                  </Card>

                  <Card>
                    <h2 className="text-sm font-semibold">6. Workload Balancing</h2>
                    <p className="mt-1 text-xs text-[var(--text-secondary)]">
                      Next {data.workload_balancing?.horizon_days ?? 7} day(s) · balance gap {data.workload_balancing?.balance_gap ?? 0}
                    </p>
                    <div className="mt-4 space-y-2">
                      {(data.workload_balancing?.doctor_loads ?? []).slice(0, 8).map((doctor) => (
                        <div key={doctor.doctor_id} className="rounded-lg border border-[var(--border-color)] p-3">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-medium">{doctor.doctor_name}</p>
                            <Badge tone={tone(doctor.availability_status)}>
                              {doctor.active_appointments} appointment(s)
                            </Badge>
                          </div>
                          <p className="mt-1 text-xs text-[var(--text-secondary)]">
                            Workload score: {doctor.workload_score}/100
                          </p>
                        </div>
                      ))}
                    </div>
                    <p className="mt-3 text-xs text-[var(--text-secondary)]">
                      {data.workload_balancing?.recommendation}
                    </p>
                  </Card>
                </div>
              </>
            ) : null}
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}
