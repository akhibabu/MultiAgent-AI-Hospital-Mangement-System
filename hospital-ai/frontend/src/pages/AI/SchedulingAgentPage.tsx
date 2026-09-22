import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import Badge, { type BadgeTone } from '@/components/common/Badge';
import Card from '@/components/common/Card';
import Loading from '@/components/ui/Loading';
import { usePatients } from '@/hooks/usePatients';
import { useSchedulingResult, useStartScheduling } from '@/hooks/useScheduling';
import { useCreateAppointment } from '@/hooks/useAppointments';
import { getApiErrorMessage } from '@/services/apiClient';
import { formatDateLabel, formatTimeLabel, toDateInputValue } from '@/utils/appointmentValidation';
import type { AppointmentFormValues } from '@/types/appointment';
import type { SchedulingResult, SchedulingStartResult, SlotRecommendation } from '@/types/scheduling';

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

type SchedulingView = {
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
  visit_type: string;
  derived_department: string | null;
  derived_specialists: string[];
  surgery_recommendation: string[];
  source_availability: Record<string, boolean>;
  recommended_tests: string[];
  recommended_imaging: string[];
  recommended_medications: string[];
  treatment_validation_status: string | null;
};

function buildView(live?: SchedulingStartResult, saved?: SchedulingResult): SchedulingView {
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
      visit_type: live.visit_type,
      derived_department: live.derived_department,
      derived_specialists: live.derived_specialists,
      surgery_recommendation: live.surgery_recommendation,
      source_availability: live.source_availability,
      recommended_tests: live.recommended_tests,
      recommended_imaging: live.recommended_imaging,
      recommended_medications: live.recommended_medications,
      treatment_validation_status: live.treatment_validation_status,
    };
  }
  return {
    doctor_assignment: saved?.doctor_assignment_json,
    appointment_scheduling: saved?.appointment_scheduling_json,
    surgery_scheduling: saved?.surgery_scheduling_json,
    follow_up_planning: saved?.follow_up_planning_json,
    queue_optimization: saved?.queue_optimization_json,
    workload_balancing: saved?.workload_balancing_json,
    summary: saved?.summary,
    warnings: saved?.warnings_json ?? [],
    emergency_priority_level: saved?.emergency_priority_level ?? 'Routine',
    emergency_priority_score: saved?.emergency_priority_score ?? 0,
    visit_type: saved?.visit_type ?? 'Consultation',
    derived_department: saved?.derived_department ?? null,
    derived_specialists: saved?.derived_specialists_json ?? [],
    surgery_recommendation: saved?.surgery_recommendation_json ?? [],
    source_availability: saved?.source_availability_json ?? {},
    recommended_tests: saved?.recommended_tests_json ?? [],
    recommended_imaging: saved?.recommended_imaging_json ?? [],
    recommended_medications: saved?.recommended_medications_json ?? [],
    treatment_validation_status: saved?.treatment_validation_status ?? null,
  };
}

export default function SchedulingAgentPage() {
  const [patientId, setPatientId] = useState('');
  const [preferredDate, setPreferredDate] = useState(toDateInputValue(new Date()));

  const patientsQuery = usePatients({
    page: 1,
    page_size: 100,
    sort_by: 'created_at',
    sort_order: 'desc',
  });
  const resultQuery = useSchedulingResult(patientId || undefined);
  const startMutation = useStartScheduling();
  const createAppointment = useCreateAppointment();

  const live = startMutation.data;
  const saved = resultQuery.data;
  const data = buildView(live, saved);
  const hasResult = Boolean(live || saved);

  const selectedPatient = useMemo(
    () => patientsQuery.data?.items.find((p) => p.id === patientId),
    [patientsQuery.data, patientId],
  );

  async function runScheduling() {
    if (!patientId) return;
    await startMutation.mutateAsync({
      patient_id: patientId,
      preferred_date: preferredDate,
    });
  }

  async function bookSlot(slot: SlotRecommendation) {
    const candidate = data.doctor_assignment?.candidates.find(
      (item) => item.doctor_id === slot.doctor_id,
    );
    const values: AppointmentFormValues = {
      patient_id: patientId,
      doctor_id: slot.doctor_id,
      department_id: candidate?.department_id || '',
      appointment_date: slot.appointment_date,
      start_time: slot.start_time.slice(0, 5),
      end_time: slot.end_time.slice(0, 5),
      visit_type: data.visit_type as AppointmentFormValues['visit_type'],
      reason_for_visit: data.derived_specialists.length
        ? `Scheduling based on prior recommendations: ${data.derived_specialists.join(', ')}.`
        : 'Scheduling based on prior clinical agent recommendations.',
      notes: 'Appointment created from Scheduling Agent recommendation. Staff/physician review completed before booking.',
      status: 'Scheduled',
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
                Scheduling is driven by the patient’s existing Diagnosis, Emergency,
                Prescription, and Medical Report results. The patient supplies only
                the scheduling date; clinical treatment and surgery decisions come
                from upstream agents.
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
              ) : <p className="mt-1 text-sm font-semibold">—</p>}
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Derived visit type</p>
              <p className="mt-1 text-sm font-semibold">{hasResult ? data.visit_type : '—'}</p>
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Assigned doctor</p>
              <p className="mt-1 text-sm font-semibold">
                {data.doctor_assignment?.selected_doctor_name || '—'}
              </p>
            </Card>
          </div>
        </header>

        <Card>
          <div className="flex flex-wrap items-end gap-3">
            <label className="min-w-[260px] flex-1 text-sm">
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
            <label className="w-48 text-sm">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Planning date</span>
              <input
                type="date"
                value={preferredDate}
                onChange={(e) => setPreferredDate(e.target.value)}
                className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5"
              />
            </label>
            <button
              type="button"
              disabled={!patientId || startMutation.isPending}
              onClick={runScheduling}
              className="rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {startMutation.isPending ? 'Running Scheduling Agent…' : 'Run Scheduling Agent'}
            </button>
            {selectedPatient ? (
              <span className="text-xs text-[var(--text-secondary)]">
                Clinical inputs are read from saved agent results for {selectedPatient.first_name} {selectedPatient.last_name}.
              </span>
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
                  <span className={hasResult
                    ? 'flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-[10px] font-bold text-white'
                    : 'flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[var(--border-color)] text-[10px] text-[var(--text-secondary)]'}>
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
                  Select a patient. Scheduling will collect the latest upstream agent
                  outputs automatically.
                </p>
              </Card>
            ) : null}

            {hasResult ? (
              <>
                <Card>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h2 className="text-sm font-semibold">Cross-Agent Clinical Context</h2>
                      <p className="mt-1 text-xs text-[var(--text-secondary)]">
                        Scheduling inputs are derived, not manually entered.
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(data.source_availability).map(([source, available]) => (
                        <span
                          key={source}
                          className={`rounded-md border px-2 py-1 text-[11px] ${available
                            ? 'border-emerald-500/40 text-emerald-700 dark:text-emerald-300'
                            : 'border-[var(--border-color)] text-[var(--text-secondary)]'}`}
                        >
                          {available ? '✓' : '○'} {source.replace('_', ' ')}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-3">
                    <div className="rounded-lg border border-[var(--border-color)] p-3">
                      <p className="text-xs text-[var(--text-secondary)]">Recommended department</p>
                      <p className="mt-1 text-sm font-semibold">{data.derived_department || 'Not specified by Diagnosis Agent'}</p>
                    </div>
                    <div className="rounded-lg border border-[var(--border-color)] p-3">
                      <p className="text-xs text-[var(--text-secondary)]">Recommended specialists</p>
                      <p className="mt-1 text-sm">{data.derived_specialists.join(', ') || 'No specialist recommendation'}</p>
                    </div>
                    <div className="rounded-lg border border-[var(--border-color)] p-3">
                      <p className="text-xs text-[var(--text-secondary)]">Follow-up / urgency</p>
                      <p className="mt-1 text-sm"><strong>{data.visit_type}</strong> · {data.follow_up_planning?.interval_days ?? '—'} day plan</p>
                    </div>
                  </div>
                  <div className="mt-4 rounded-xl border border-primary-500/30 bg-primary-500/5 p-4">
                    <p className="text-sm font-medium">Downstream scheduling inputs</p>
                    <p className="mt-1 text-xs text-[var(--text-secondary)]">
                      Diagnosis treatment path, Emergency priority/triage, Prescription treatment plan,
                      and Medical Report documentation are combined before doctor and slot selection.
                    </p>
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <div className="rounded-lg border border-[var(--border-color)] p-3">
                      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Treatment / investigations from prior agents</p>
                      <p className="mt-2 text-xs"><strong>Tests:</strong> {data.recommended_tests.join(', ') || 'None'}</p>
                      <p className="mt-2 text-xs"><strong>Imaging:</strong> {data.recommended_imaging.join(', ') || 'None'}</p>
                      <p className="mt-2 text-xs"><strong>Medicines:</strong> {data.recommended_medications.join(', ') || 'None'}</p>
                    </div>
                    <div className="rounded-lg border border-[var(--border-color)] p-3">
                      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Treatment validation</p>
                      <p className="mt-2 text-sm">{data.treatment_validation_status || 'No Prescription validation result available'}</p>
                      <p className="mt-2 text-xs text-[var(--text-secondary)]">These values are context for scheduling and future downstream agents. They do not constitute a new treatment decision.</p>
                    </div>
                  </div>
                </Card>

                <Card>
                  <h2 className="text-sm font-semibold">1. Doctor Assignment</h2>
                  <p className="mt-1 text-xs text-[var(--text-secondary)]">
                    Selected: {data.doctor_assignment?.selected_doctor_name || 'No doctor'} · score {data.doctor_assignment?.selection_score ?? 0}/100
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
                          Workload: {candidate.workload_count} active appointment(s)
                        </p>
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {candidate.reasons.slice(0, 5).map((reason) => (
                            <span key={reason} className="rounded-md bg-black/5 px-2 py-1 text-[11px] dark:bg-white/5">{reason}</span>
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
                      <p className="mt-1 text-xs text-[var(--text-secondary)]">Recommendation only until staff explicitly books.</p>
                    </div>
                    {data.appointment_scheduling?.recommended_slot ? (
                      <button
                        type="button"
                        disabled={createAppointment.isPending}
                        onClick={() => bookSlot(data.appointment_scheduling!.recommended_slot!)}
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
                        {' · '}{formatTimeLabel(data.appointment_scheduling.recommended_slot.start_time)}
                        {'–'}{formatTimeLabel(data.appointment_scheduling.recommended_slot.end_time)}
                      </p>
                      <p className="mt-1 text-xs text-[var(--text-secondary)]">
                        {data.appointment_scheduling.recommended_slot.doctor_name}
                      </p>
                    </div>
                  ) : (
                    <p className="mt-4 text-sm text-[var(--text-secondary)]">No open appointment slot found.</p>
                  )}
                  {data.appointment_scheduling?.alternatives?.length ? (
                    <div className="mt-4">
                      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Alternative slots</p>
                      <div className="mt-2 grid gap-2 md:grid-cols-2">
                        {data.appointment_scheduling.alternatives.map((slot) => (
                          <button key={slot.appointment_date + slot.start_time} type="button" onClick={() => bookSlot(slot)} className="rounded-lg border border-[var(--border-color)] p-3 text-left hover:border-primary-500/50">
                            <p className="text-sm font-medium">{formatDateLabel(slot.appointment_date)} · {formatTimeLabel(slot.start_time)}</p>
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
                    <div className="mt-3">
                      {data.surgery_scheduling?.required ? (
                        <>
                          <Badge tone="amber">Upstream recommendation detected</Badge>
                          <p className="mt-2 text-sm">Surgery/procedure planning was derived from prior agent recommendations.</p>
                          {data.surgery_recommendation.length ? (
                            <ul className="mt-3 space-y-1 text-xs text-[var(--text-secondary)]">
                              {data.surgery_recommendation.map((evidence) => <li key={evidence}>• {evidence}</li>)}
                            </ul>
                          ) : null}
                          {data.surgery_scheduling.recommended_slot ? (
                            <p className="mt-3 text-sm">
                              Candidate window: {formatDateLabel(data.surgery_scheduling.recommended_slot.appointment_date)}
                              {' · '}{formatTimeLabel(data.surgery_scheduling.recommended_slot.start_time)}
                            </p>
                          ) : (
                            <p className="mt-3 text-sm text-[var(--text-secondary)]">No open planning window found.</p>
                          )}
                          <p className="mt-3 text-xs text-[var(--text-secondary)]">
                            {data.surgery_scheduling.operation_theatre_status}
                          </p>
                        </>
                      ) : (
                        <>
                          <Badge tone="green">No explicit surgery recommendation</Badge>
                          <p className="mt-2 text-sm text-[var(--text-secondary)]">
                            No upstream agent currently contains explicit surgery/operative recommendation language.
                          </p>
                        </>
                      )}
                    </div>
                  </Card>

                  <Card>
                    <h2 className="text-sm font-semibold">4. Follow-Up Planning</h2>
                    <p className="mt-3 text-sm">
                      Recommended date:{' '}
                      <strong>{data.follow_up_planning?.recommended_date ? formatDateLabel(data.follow_up_planning.recommended_date) : '—'}</strong>
                    </p>
                    <p className="mt-2 text-sm">
                      Interval: <strong>{data.follow_up_planning?.interval_days ?? '—'} day(s)</strong>
                    </p>
                    <p className="mt-2 text-xs text-[var(--text-secondary)]">{data.follow_up_planning?.reason}</p>
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
                          <div><p className="text-sm font-medium">#{item.position} · {item.patient_name}</p><p className="text-xs text-[var(--text-secondary)]">{formatTimeLabel(item.start_time)}–{formatTimeLabel(item.end_time)}</p></div>
                          <Badge tone={tone(item.priority_level)}>{item.priority_level} · {item.priority_score}</Badge>
                        </div>
                      ))}
                      {!data.queue_optimization?.ordered_queue?.length ? <p className="text-sm text-[var(--text-secondary)]">No existing appointments for the selected doctor/date.</p> : null}
                    </div>
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
                            <Badge tone={tone(doctor.availability_status)}>{doctor.active_appointments} appointment(s)</Badge>
                          </div>
                          <p className="mt-1 text-xs text-[var(--text-secondary)]">Workload score: {doctor.workload_score}/100</p>
                        </div>
                      ))}
                    </div>
                    <p className="mt-3 text-xs text-[var(--text-secondary)]">{data.workload_balancing?.recommendation}</p>
                  </Card>
                </div>

                <Card>
                  <h2 className="text-sm font-semibold">Scheduling Summary</h2>
                  <p className="mt-2 text-sm leading-relaxed">{data.summary}</p>
                  {data.warnings.length ? (
                    <ul className="mt-3 space-y-1 text-sm text-amber-800 dark:text-amber-200">
                      {data.warnings.map((warning) => <li key={warning}>• {warning}</li>)}
                    </ul>
                  ) : null}
                </Card>
              </>
            ) : null}
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}
