/**
 * Emergency Agent — emergency decision support.
 *
 * Reads the shared Intake Patient Context and produces an auditable,
 * deterministic six-stage emergency acuity snapshot.
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import Badge, { type BadgeTone } from '@/components/common/Badge';
import Card from '@/components/common/Card';
import { usePatients } from '@/hooks/usePatients';
import { useEmergencyResult, useStartEmergency } from '@/hooks/useEmergency';
import { getApiErrorMessage } from '@/services/apiClient';

function toneForLevel(level?: string | null): BadgeTone {
  if (!level) return 'gray';
  if (level === 'Critical' || level === 'High') return 'red';
  if (level === 'Urgent' || level === 'Moderate') return 'amber';
  if (level === 'Semi-Urgent') return 'blue';
  if (level === 'Routine' || level === 'Low') return 'green';
  return 'gray';
}

const STAGES = [
  'Real-Time Vital Monitoring',
  'Triage Classification',
  'Critical Event Detection',
  'ICU Requirement Prediction',
  'Emergency Alert Generation',
  'Patient Priority Ranking',
];

export default function EmergencyAgentPage() {
  const [patientId, setPatientId] = useState('');
  const patientsQuery = usePatients({
    page: 1,
    page_size: 100,
    sort_by: 'created_at',
    sort_order: 'desc',
  });
  const resultQuery = useEmergencyResult(patientId || undefined);
  const startMutation = useStartEmergency(patientId || undefined);

  const report = startMutation.data;
  const persisted = resultQuery.data;
  const hasResult = Boolean(report || persisted);

  const triage = report?.triage_classification || persisted?.triage_classification_json;
  const monitoring = report?.vital_monitoring || persisted?.vital_monitoring_json;
  const events =
    report?.critical_event_detection || persisted?.critical_event_detection_json;
  const icu = report?.icu_requirement || persisted?.icu_requirement_json;
  const alerts = report?.emergency_alerts || persisted?.emergency_alerts_json;
  const priority = report?.patient_priority || persisted?.patient_priority_json;
  const warnings = report?.warnings || persisted?.warnings_json || [];

  async function handleRun() {
    if (patientId) await startMutation.mutateAsync();
  }

  return (
    <ErrorBoundary title="Emergency Agent error">
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary-600">
                AI Center
              </p>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[var(--text-primary)]">
                Emergency Agent
              </h1>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[var(--text-secondary)]">
                Analyzes the latest structured Intake Patient Context for emergency
                acuity signals. This is clinical decision support, not a bedside
                monitor, emergency protocol, diagnosis, or ICU admission decision.
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
              <p className="text-xs text-[var(--text-secondary)]">Triage</p>
              {triage?.category ? (
                <Badge tone={toneForLevel(triage.category)}>{triage.category}</Badge>
              ) : (
                <p className="mt-1 text-sm font-semibold">—</p>
              )}
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Priority</p>
              {priority?.priority_level ? (
                <Badge tone={toneForLevel(priority.priority_level)}>
                  {priority.priority_level}
                </Badge>
              ) : (
                <p className="mt-1 text-sm font-semibold">—</p>
              )}
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">ICU signal</p>
              {icu?.signal ? (
                <Badge tone={toneForLevel(icu.signal)}>{icu.signal}</Badge>
              ) : (
                <p className="mt-1 text-sm font-semibold">—</p>
              )}
            </Card>
          </div>
        </header>

        <Card>
          <div className="flex flex-wrap items-end gap-3">
            <label className="min-w-[240px] flex-1 text-sm">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Patient</span>
              <select
                className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
              >
                <option value="">Select a patient…</option>
                {(patientsQuery.data?.items ?? []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.first_name} {p.last_name}
                    {p.patient_number ? ` (${p.patient_number})` : ''}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              disabled={!patientId || startMutation.isPending}
              onClick={handleRun}
              className="rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {startMutation.isPending ? 'Running Emergency Agent…' : 'Run Emergency Agent'}
            </button>
          </div>
          {startMutation.isError ? (
            <p className="mt-3 text-sm text-red-600">
              {getApiErrorMessage(startMutation.error, 'Emergency Agent failed')}
            </p>
          ) : null}
        </Card>

        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          <Card>
            <h2 className="text-sm font-semibold">Workflow</h2>
            <ol className="mt-5 space-y-3">
              {STAGES.map((stage, index) => (
                <li key={stage} className="flex gap-3">
                  <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                    hasResult
                      ? 'bg-emerald-500 text-white'
                      : 'border border-[var(--border-color)] text-[var(--text-secondary)]'
                  }`}>
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
                  Select a patient to view or generate an emergency snapshot.
                </p>
              </Card>
            ) : null}

            {hasResult ? (
              <>
                <Card>
                  <h2 className="text-sm font-semibold">Emergency Summary</h2>
                  <p className="mt-2 text-sm leading-relaxed">{report?.summary || persisted?.summary}</p>
                  {warnings.length ? (
                    <ul className="mt-3 space-y-1 text-sm text-amber-800 dark:text-amber-200">
                      {warnings.map((warning: string) => <li key={warning}>• {warning}</li>)}
                    </ul>
                  ) : null}
                </Card>

                <div className="grid gap-4 md:grid-cols-2">
                  <Card>
                    <h2 className="text-sm font-semibold">Vital Monitoring</h2>
                    <div className="mt-3 space-y-2">
                      {(monitoring?.observations ?? []).map((observation: any) => (
                        <div key={`${observation.name}-${observation.value}`} className="flex items-center justify-between gap-3 rounded-lg border border-[var(--border-color)] p-3">
                          <div>
                            <p className="text-sm font-medium">{observation.name}</p>
                            <p className="text-xs text-[var(--text-secondary)]">{observation.message}</p>
                          </div>
                          <Badge tone={toneForLevel(observation.severity)}>
                            {observation.value} {observation.unit}
                          </Badge>
                        </div>
                      ))}
                      {!monitoring?.observations?.length ? (
                        <p className="text-sm text-[var(--text-secondary)]">No vital signs available.</p>
                      ) : null}
                    </div>
                  </Card>

                  <Card>
                    <h2 className="text-sm font-semibold">Critical Events</h2>
                    <p className="mt-1 text-xs text-[var(--text-secondary)]">
                      {events?.detected_event_count ?? 0} detected signal(s)
                    </p>
                    <div className="mt-3 space-y-2">
                      {(events?.events ?? []).map((event: any) => (
                        <div key={event.event_type} className="rounded-lg border border-[var(--border-color)] p-3">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-medium">{event.event_type}</p>
                            <Badge tone={toneForLevel(event.severity)}>{event.severity}</Badge>
                          </div>
                          <p className="mt-1 text-xs text-[var(--text-secondary)]">{event.message}</p>
                        </div>
                      ))}
                      {!events?.events?.length ? (
                        <p className="text-sm text-[var(--text-secondary)]">No critical event signal detected.</p>
                      ) : null}
                    </div>
                  </Card>

                  <Card>
                    <h2 className="text-sm font-semibold">Triage & Priority</h2>
                    <div className="mt-3 space-y-3 text-sm">
                      <p>Triage score: <strong>{triage?.score ?? '—'}/100</strong></p>
                      <p>Priority score: <strong>{priority?.priority_score ?? '—'}/100</strong></p>
                      {(triage?.reasons ?? []).map((reason: string) => (
                        <p key={reason} className="text-[var(--text-secondary)]">• {reason}</p>
                      ))}
                    </div>
                  </Card>

                  <Card>
                    <h2 className="text-sm font-semibold">Emergency Alerts</h2>
                    <div className="mt-3 space-y-2">
                      {(alerts?.alerts ?? []).map((alert: any) => (
                        <div key={`${alert.code}-${alert.message}`} className="rounded-lg border border-[var(--border-color)] p-3">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-medium">{alert.title}</p>
                            <Badge tone={toneForLevel(alert.severity)}>{alert.severity}</Badge>
                          </div>
                          <p className="mt-1 text-xs text-[var(--text-secondary)]">{alert.message}</p>
                          <p className="mt-2 text-xs font-medium">{alert.recommended_next_step}</p>
                        </div>
                      ))}
                      {!alerts?.alerts?.length ? (
                        <p className="text-sm text-[var(--text-secondary)]">No alert generated.</p>
                      ) : null}
                    </div>
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
