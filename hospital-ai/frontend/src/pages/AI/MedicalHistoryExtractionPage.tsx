import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import Loading from '@/components/ui/Loading';
import ErrorState from '@/components/ui/ErrorState';
import { usePatients } from '@/hooks/usePatients';
import { useProcessingJobs } from '@/hooks/useRegistration';
import {
  useExtractMedicalHistory,
  useMedicalHistory,
} from '@/hooks/useMedicalHistory';
import type { TimelineEvent } from '@/types/medicalHistory';

function Panel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4">
      <h3 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
        {title}
      </h3>
      {children}
    </section>
  );
}

function ChipList({ items }: { items: string[] }) {
  if (!items.length) {
    return (
      <p className="text-sm text-[var(--text-secondary)]">None recorded</p>
    );
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span
          key={item}
          className="rounded-md border border-[var(--border-color)] px-2 py-0.5 text-xs"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function TimelineViz({ events }: { events: TimelineEvent[] }) {
  if (!events.length) {
    return (
      <p className="text-sm text-[var(--text-secondary)]">
        No timeline events yet.
      </p>
    );
  }
  return (
    <ol className="relative max-h-96 space-y-3 overflow-auto border-l border-[var(--border-color)] pl-4">
      {events.map((event, idx) => (
        <li key={`${event.reference_id || event.summary}-${idx}`} className="text-sm">
          <span className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full bg-primary-600" />
          <p className="text-[10px] uppercase tracking-wide text-[var(--text-secondary)]">
            {event.date || 'Unknown date'} · {event.event_type}
          </p>
          <p className="font-medium text-[var(--text-primary)]">{event.summary}</p>
          <p className="text-xs text-[var(--text-secondary)]">
            {[event.doctor, event.department].filter(Boolean).join(' · ') ||
              '—'}
          </p>
        </li>
      ))}
    </ol>
  );
}

export default function MedicalHistoryExtractionPage() {
  const [patientId, setPatientId] = useState('');
  const [jobId, setJobId] = useState('');

  const patientsQuery = usePatients({
    page: 1,
    page_size: 100,
    sort_by: 'created_at',
    sort_order: 'desc',
  });
  const jobsQuery = useProcessingJobs(patientId || undefined);
  const historyQuery = useMedicalHistory(patientId || undefined);
  const extractMutation = useExtractMedicalHistory(patientId || undefined);

  const patients = patientsQuery.data?.items ?? [];
  const jobs = jobsQuery.data ?? [];
  const history = historyQuery.data?.medical_history;
  const timeline = historyQuery.data?.timeline ?? history?.timeline ?? [];

  const eligibleJobs = useMemo(
    () =>
      jobs.filter(
        (j) =>
          j.current_stage === 'Patient Registration' ||
          j.current_stage === 'Medical History Extraction' ||
          j.current_stage === 'OCR',
      ),
    [jobs],
  );

  async function handleExtract() {
    const target =
      jobId ||
      eligibleJobs.find((j) => j.current_stage === 'Patient Registration')?.id ||
      eligibleJobs[0]?.id;
    if (!target) {
      return;
    }
    await extractMutation.mutateAsync(target);
  }

  const patient = history?.patient as
    | {
        full_name?: string;
        patient_number?: string;
        gender?: string;
        blood_group?: string;
        date_of_birth?: string;
      }
    | undefined;

  return (
    <ErrorBoundary title="Medical History Extraction error">
      <section className="space-y-6">
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-primary-600">
              AI Center · Intake Agent · Stage 2
            </p>
            <h2 className="text-2xl font-semibold text-[var(--text-primary)]">
              Medical History Extraction
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">
              Consolidates existing HMS records into a unified history. Does not
              OCR or analyze the newly uploaded document. Next stage marker:{' '}
              <span className="font-medium">OCR</span>.
            </p>
          </div>
          <div className="flex gap-2">
            <Link
              to="/ai/intake"
              className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-sm"
            >
              Patient Registration
            </Link>
            <Link
              to="/ai"
              className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-sm"
            >
              AI Center
            </Link>
          </div>
        </header>

        <div className="flex flex-wrap items-end gap-3 rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4">
          <label className="min-w-[220px] flex-1 text-sm">
            <span className="mb-1 block text-[var(--text-secondary)]">
              Patient
            </span>
            <select
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2"
              value={patientId}
              onChange={(e) => {
                setPatientId(e.target.value);
                setJobId('');
              }}
            >
              <option value="">Select patient…</option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.first_name} {p.last_name}
                  {p.patient_number ? ` (${p.patient_number})` : ''}
                </option>
              ))}
            </select>
          </label>

          <label className="min-w-[260px] flex-1 text-sm">
            <span className="mb-1 block text-[var(--text-secondary)]">
              Processing Job
            </span>
            <select
              className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2"
              value={jobId}
              disabled={!patientId}
              onChange={(e) => setJobId(e.target.value)}
            >
              <option value="">
                {!patientId
                  ? 'Select patient first…'
                  : eligibleJobs.length
                    ? 'Latest eligible job (auto)'
                    : 'No jobs — register first'}
              </option>
              {eligibleJobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.document_name} · {j.current_stage} · {j.status}
                </option>
              ))}
            </select>
          </label>

          <button
            type="button"
            disabled={!patientId || extractMutation.isPending || !jobs.length}
            onClick={handleExtract}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {extractMutation.isPending
              ? 'Extracting…'
              : 'Run History Extraction'}
          </button>
        </div>

        {!patientId ? (
          <p className="rounded-xl border border-dashed border-[var(--border-color)] px-4 py-10 text-center text-sm text-[var(--text-secondary)]">
            Select a patient who completed Patient Registration.
          </p>
        ) : historyQuery.isLoading ? (
          <Loading message="Loading medical history…" />
        ) : historyQuery.isError ? (
          <ErrorState
            message="Could not load history. Ensure migration 008 is applied."
            onRetry={() => historyQuery.refetch()}
          />
        ) : (
          <>
            <div className="grid gap-3 sm:grid-cols-3">
              <Panel title="Current Stage">
                <p className="text-lg font-semibold text-[var(--text-primary)]">
                  {historyQuery.data?.current_stage || '—'}
                </p>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  Next: {historyQuery.data?.next_stage || 'OCR'}
                </p>
              </Panel>
              <Panel title="Processing Job">
                <p className="break-all font-mono text-xs text-[var(--text-primary)]">
                  {historyQuery.data?.processing_job?.id || '—'}
                </p>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  {historyQuery.data?.processing_job?.status || 'No job'}
                </p>
              </Panel>
              <Panel title="Summary">
                <p className="text-sm text-[var(--text-primary)]">
                  {history?.latest_summary ||
                    historyQuery.data?.warnings?.[0] ||
                    'Not extracted yet'}
                </p>
              </Panel>
            </div>

            {historyQuery.data?.warnings?.length ? (
              <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-200">
                {historyQuery.data.warnings.join(' · ')}
              </div>
            ) : null}

            {!history ? (
              <p className="rounded-xl border border-dashed border-[var(--border-color)] px-4 py-8 text-center text-sm text-[var(--text-secondary)]">
                No extracted history yet. Click <strong>Run History Extraction</strong>.
              </p>
            ) : (
              <div className="grid gap-4 lg:grid-cols-2">
                <Panel title="Patient Overview">
                  <dl className="space-y-1 text-sm">
                    <div className="flex justify-between gap-2">
                      <dt className="text-[var(--text-secondary)]">Name</dt>
                      <dd>{patient?.full_name || '—'}</dd>
                    </div>
                    <div className="flex justify-between gap-2">
                      <dt className="text-[var(--text-secondary)]">Number</dt>
                      <dd>{patient?.patient_number || '—'}</dd>
                    </div>
                    <div className="flex justify-between gap-2">
                      <dt className="text-[var(--text-secondary)]">DOB</dt>
                      <dd>{patient?.date_of_birth || '—'}</dd>
                    </div>
                    <div className="flex justify-between gap-2">
                      <dt className="text-[var(--text-secondary)]">Gender</dt>
                      <dd>{patient?.gender || '—'}</dd>
                    </div>
                    <div className="flex justify-between gap-2">
                      <dt className="text-[var(--text-secondary)]">Blood</dt>
                      <dd>{patient?.blood_group || '—'}</dd>
                    </div>
                  </dl>
                </Panel>

                <Panel title="Insurance Details">
                  <dl className="space-y-1 text-sm">
                    <div className="flex justify-between gap-2">
                      <dt className="text-[var(--text-secondary)]">Provider</dt>
                      <dd>
                        {String(history.insurance?.provider || '—')}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-2">
                      <dt className="text-[var(--text-secondary)]">Number</dt>
                      <dd>{String(history.insurance?.number || '—')}</dd>
                    </div>
                  </dl>
                </Panel>

                <Panel title="Past Conditions">
                  <ChipList items={history.conditions} />
                </Panel>

                <Panel title="Past Medications">
                  <ChipList items={history.medications} />
                </Panel>

                <Panel title="Allergies">
                  <ChipList items={history.allergies} />
                </Panel>

                <Panel title="Previous Diagnoses">
                  <ChipList items={history.previous_diagnoses} />
                </Panel>

                <Panel title="Previous Doctors">
                  {!history.doctors.length ? (
                    <p className="text-sm text-[var(--text-secondary)]">None</p>
                  ) : (
                    <ul className="space-y-1 text-sm">
                      {history.doctors.map((d) => (
                        <li key={String(d.id)}>
                          {String(d.name)}
                          {d.specialization
                            ? ` — ${String(d.specialization)}`
                            : ''}
                        </li>
                      ))}
                    </ul>
                  )}
                </Panel>

                <Panel title="Appointment History">
                  {!history.appointments.length ? (
                    <p className="text-sm text-[var(--text-secondary)]">
                      No appointments
                    </p>
                  ) : (
                    <ul className="max-h-48 space-y-1 overflow-auto text-sm">
                      {history.appointments.map((a) => (
                        <li
                          key={String(a.id)}
                          className="border-b border-[var(--border-color)] py-1 last:border-0"
                        >
                          {String(a.appointment_number || a.id)} ·{' '}
                          {String(a.date || '—')} · {String(a.status || '')}
                        </li>
                      ))}
                    </ul>
                  )}
                </Panel>

                <Panel title="Previous Reports">
                  {!history.reports.length ? (
                    <p className="text-sm text-[var(--text-secondary)]">
                      No uploaded reports
                    </p>
                  ) : (
                    <ul className="max-h-48 space-y-1 overflow-auto text-sm">
                      {history.reports.map((r) => (
                        <li key={String(r.id)}>
                          {String(r.file_name || r.id)}
                          {r.file_type ? (
                            <span className="text-[var(--text-secondary)]">
                              {' '}
                              · {String(r.file_type)}
                            </span>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  )}
                </Panel>

                <Panel title="Medical Timeline">
                  <TimelineViz events={timeline} />
                </Panel>

                <div className="lg:col-span-2">
                  <Panel title="Timeline Visualization">
                    <div className="flex flex-wrap gap-2">
                      {timeline.map((event, idx) => (
                        <div
                          key={`viz-${event.reference_id}-${idx}`}
                          className="min-w-[140px] flex-1 rounded-lg border border-[var(--border-color)] px-3 py-2"
                        >
                          <p className="text-[10px] uppercase text-primary-600">
                            {event.event_type}
                          </p>
                          <p className="text-xs font-medium text-[var(--text-primary)]">
                            {event.date || '—'}
                          </p>
                          <p className="mt-1 line-clamp-2 text-[11px] text-[var(--text-secondary)]">
                            {event.summary}
                          </p>
                        </div>
                      ))}
                    </div>
                  </Panel>
                </div>
              </div>
            )}
          </>
        )}
      </section>
    </ErrorBoundary>
  );
}
