/**
 * Diagnosis Agent — Clinical Decision Support.
 *
 * Consumes only the Intake Agent's Patient Context and Knowledge Graph.
 * Assists — never replaces — a physician. Never prescribes medication.
 */
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import Badge, { type BadgeTone } from '@/components/common/Badge';
import Card from '@/components/common/Card';
import { usePatients } from '@/hooks/usePatients';
import {
  useDiagnosisHistory,
  useDiagnosisResult,
  useStartDiagnosis,
} from '@/hooks/useDiagnosis';
import { useStartResearch } from '@/hooks/useResearch';
import type {
  ClinicalDecisionSupport,
  DifferentialDiagnosis,
  DiseaseProbability,
  SeverityAssessment,
  SymptomAnalysis,
  TreatmentPath,
} from '@/types/diagnosis';
import { SEVERITY_LEVEL_TONE } from '@/types/diagnosis';

const WORKFLOW_STAGES = [
  {
    id: 'symptom',
    label: 'Symptom Analysis',
    description: 'Cluster symptoms by body system using history, vitals, and labs.',
  },
  {
    id: 'differential',
    label: 'Differential Diagnosis',
    description: 'Rank candidate conditions with supporting and contradicting evidence.',
  },
  {
    id: 'probability',
    label: 'Disease Probability Scoring',
    description: 'Calculate calibrated probability for each candidate condition.',
  },
  {
    id: 'severity',
    label: 'Severity Prediction',
    description: 'Estimate Very Low → Critical severity with an explanation.',
  },
  {
    id: 'treatment',
    label: 'Treatment Path Recommendation',
    description: 'Suggest specialist referral, department, and diagnostic tests only.',
  },
  {
    id: 'cds',
    label: 'Clinical Decision Support',
    description: 'Assemble the clinician-facing decision-support report.',
  },
] as const;

function severityTone(level?: string | null): BadgeTone {
  if (!level) return 'gray';
  return SEVERITY_LEVEL_TONE[level] || 'gray';
}

function formatWhen(iso?: string | null) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return `${d.toLocaleDateString()} · ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  } catch {
    return iso;
  }
}

function ConfidenceBar({ value, tone = 'blue' }: { value: number; tone?: BadgeTone }) {
  const pct = Math.round(Math.min(1, Math.max(0, value)) * 100);
  const barTone =
    tone === 'red'
      ? 'bg-red-500'
      : tone === 'amber'
        ? 'bg-amber-500'
        : tone === 'green'
          ? 'bg-emerald-500'
          : 'bg-primary-600';
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-full max-w-[140px] overflow-hidden rounded-full bg-black/5 dark:bg-white/10">
        <div className={`h-full rounded-full ${barTone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium text-[var(--text-secondary)]">{pct}%</span>
    </div>
  );
}

function DifferentialCard({ item, rank }: { item: DifferentialDiagnosis; rank: number }) {
  const [open, setOpen] = useState(rank === 0);
  const tone: BadgeTone = item.confidence >= 0.6 ? 'red' : item.confidence >= 0.35 ? 'amber' : 'gray';
  return (
    <div className="rounded-xl border border-[var(--border-color)] p-4">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full flex-wrap items-start justify-between gap-3 text-left"
      >
        <div>
          <p className="text-xs text-[var(--text-secondary)]">#{rank + 1} · {item.body_system || 'General'}</p>
          <p className="mt-0.5 text-sm font-semibold text-[var(--text-primary)]">{item.condition}</p>
        </div>
        <ConfidenceBar value={item.confidence} tone={tone} />
      </button>
      {open ? (
        <div className="mt-4 space-y-3 border-t border-[var(--border-color)] pt-3 text-sm">
          {item.supporting_symptoms.length ? (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                Supporting symptoms
              </p>
              <p className="mt-1">{item.supporting_symptoms.join(', ')}</p>
            </div>
          ) : null}
          {item.supporting_labs.length ? (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                Supporting labs
              </p>
              <p className="mt-1">{item.supporting_labs.join(', ')}</p>
            </div>
          ) : null}
          {item.supporting_history.length ? (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                Supporting history
              </p>
              <p className="mt-1">{item.supporting_history.join(', ')}</p>
            </div>
          ) : null}
          {item.contradicting_evidence.length ? (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                Contradicting evidence
              </p>
              <ul className="mt-1 space-y-1 text-amber-800 dark:text-amber-200">
                {item.contradicting_evidence.map((c) => (
                  <li key={c}>• {c}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {item.recommended_specialists.length ? (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                Recommended specialists
              </p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {item.recommended_specialists.map((s) => (
                  <Badge key={s} tone="blue">{s}</Badge>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export default function DiagnosisAgentPage() {
  const [patientId, setPatientId] = useState('');
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [conditionFilter, setConditionFilter] = useState('');

  const patientsQuery = usePatients({
    page: 1,
    page_size: 100,
    sort_by: 'created_at',
    sort_order: 'desc',
  });

  const resultQuery = useDiagnosisResult(patientId || undefined);
  const historyQuery = useDiagnosisHistory(patientId || undefined);
  const startMutation = useStartDiagnosis(patientId || undefined);
  const startResearchMutation = useStartResearch(patientId || undefined);

  const liveReport = startMutation.data;
  const persisted = resultQuery.data;

  const hasResult = Boolean(liveReport || persisted);
  const symptomAnalysis: SymptomAnalysis | undefined =
    liveReport?.symptom_analysis || persisted?.symptom_analysis_json;
  const differentials: DifferentialDiagnosis[] =
    liveReport?.differential_diagnoses || persisted?.differential_diagnoses_json || [];
  const probabilities: DiseaseProbability[] =
    liveReport?.probability_scores || persisted?.probability_scores_json || [];
  const severity: SeverityAssessment | undefined =
    liveReport?.severity_assessment || persisted?.severity_assessment_json;
  const treatmentPath: TreatmentPath | undefined =
    liveReport?.treatment_path || persisted?.treatment_path_json;
  const cds: ClinicalDecisionSupport | undefined =
    liveReport?.clinical_decision_support || persisted?.clinical_decision_support_json;
  const summary = liveReport?.summary || persisted?.summary;
  const warnings = liveReport?.warnings || [];
  const diagnosisResultId = liveReport?.diagnosis_result?.id || persisted?.id;

  const filteredDifferentials = useMemo(() => {
    if (!conditionFilter.trim()) return differentials;
    const q = conditionFilter.trim().toLowerCase();
    return differentials.filter((d) => d.condition.toLowerCase().includes(q));
  }, [differentials, conditionFilter]);

  const isRunning = startMutation.isPending;
  const isLoadingExisting = resultQuery.isLoading && !hasResult;

  async function handleRun() {
    if (!patientId) return;
    await startMutation.mutateAsync({
      chief_complaint: chiefComplaint || undefined,
    });
  }

  async function handleRunResearch() {
    if (!patientId) return;
    await startResearchMutation.mutateAsync(diagnosisResultId);
  }

  return (
    <ErrorBoundary title="Diagnosis Agent error">
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary-600">
                AI Center
              </p>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[var(--text-primary)]">
                Diagnosis Agent
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">
                Analyzes the Patient Context and Knowledge Graph to assist clinicians with
                differential diagnoses and clinical insights. Clinical decision support
                only — assists, never replaces, a physician. Does not prescribe medication.
              </p>
            </div>
            <Link
              to="/ai"
              className="rounded-xl border border-[var(--border-color)] px-3 py-2 text-sm text-[var(--text-secondary)] transition hover:border-primary-500/40"
            >
              Back to AI Center
            </Link>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Status</p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                {isRunning ? 'Running' : hasResult ? 'Completed' : 'Not started'}
              </p>
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Top condition</p>
              <p className="mt-1 truncate text-sm font-semibold text-[var(--text-primary)]">
                {probabilities[0]?.condition || '—'}
              </p>
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Severity</p>
              {severity ? (
                <Badge tone={severityTone(severity.level)}>{severity.level}</Badge>
              ) : (
                <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">—</p>
              )}
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Processing time</p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                {liveReport?.processing_time_ms != null
                  ? `${liveReport.processing_time_ms} ms`
                  : persisted?.processing_time_ms != null
                    ? `${persisted.processing_time_ms} ms`
                    : '—'}
              </p>
            </Card>
          </div>
        </header>

        {/* Patient picker + run controls */}
        <Card>
          <div className="flex flex-wrap items-end gap-3">
            <label className="min-w-[220px] flex-1 text-sm">
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
            <label className="min-w-[260px] flex-1 text-sm">
              <span className="mb-1.5 block text-[var(--text-secondary)]">
                Chief complaint (optional)
              </span>
              <input
                type="text"
                value={chiefComplaint}
                onChange={(e) => setChiefComplaint(e.target.value)}
                placeholder="e.g. Chest discomfort for 2 days"
                className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5"
              />
            </label>
            <button
              type="button"
              disabled={!patientId || isRunning}
              onClick={handleRun}
              className="rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {isRunning ? 'Running Diagnosis Agent…' : 'Run Diagnosis Agent'}
            </button>
            {hasResult ? (
              <button
                type="button"
                disabled={!patientId || startResearchMutation.isPending}
                onClick={handleRunResearch}
                className="rounded-xl border border-[var(--border-color)] px-4 py-2.5 text-sm font-medium text-[var(--text-primary)] disabled:opacity-50"
              >
                {startResearchMutation.isPending ? 'Sending to Research Agent…' : 'Send to Research Agent'}
              </button>
            ) : null}
          </div>
          {startMutation.isError ? (
            <p className="mt-3 text-sm text-red-600">
              Diagnosis Agent failed. Ensure the patient has completed Intake Agent stages.
            </p>
          ) : null}
        </Card>

        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          {/* Workflow */}
          <Card>
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">Workflow</h2>
            <ol className="mt-5 space-y-0">
              {WORKFLOW_STAGES.map((stage, i) => {
                const status = hasResult ? 'complete' : isRunning ? (i === 0 ? 'active' : 'future') : 'future';
                return (
                  <li key={stage.id} className="relative flex gap-3 pb-5 last:pb-0">
                    {i < WORKFLOW_STAGES.length - 1 ? (
                      <span className="absolute left-[11px] top-7 h-[calc(100%-12px)] w-px bg-[var(--border-color)]" />
                    ) : null}
                    <span
                      className={`relative z-10 mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                        status === 'complete'
                          ? 'bg-emerald-500 text-white'
                          : status === 'active'
                            ? 'animate-pulse bg-primary-600 text-white'
                            : 'border border-[var(--border-color)] text-[var(--text-secondary)]'
                      }`}
                    >
                      {status === 'complete' ? '✓' : status === 'active' ? '…' : ''}
                    </span>
                    <div className={status === 'future' && !hasResult ? 'opacity-70' : ''}>
                      <p className="text-sm font-medium text-[var(--text-primary)]">{stage.label}</p>
                      <p className="mt-0.5 text-xs leading-relaxed text-[var(--text-secondary)]">
                        {stage.description}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </Card>

          <div className="space-y-6">
            {isLoadingExisting ? (
              <Card>
                <p className="text-sm text-[var(--text-secondary)]">Loading existing diagnosis…</p>
              </Card>
            ) : null}

            {resultQuery.isError && !hasResult && patientId ? (
              <Card>
                <p className="text-sm text-[var(--text-secondary)]">
                  No diagnosis on record for this patient yet. Run the Diagnosis Agent to generate one.
                </p>
              </Card>
            ) : null}

            {!patientId ? (
              <Card>
                <p className="text-sm text-[var(--text-secondary)]">
                  Select a patient to view or generate a diagnosis.
                </p>
              </Card>
            ) : null}

            {hasResult ? (
              <>
                {/* Summary */}
                <Card>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                        Diagnosis Summary
                      </h2>
                      <p className="mt-2 text-sm leading-relaxed text-[var(--text-primary)]">
                        {summary}
                      </p>
                    </div>
                    {severity ? (
                      <Badge tone={severityTone(severity.level)}>{severity.level} severity</Badge>
                    ) : null}
                  </div>
                  {warnings.length ? (
                    <ul className="mt-3 space-y-1 text-sm text-amber-800 dark:text-amber-200">
                      {warnings.map((w) => (
                        <li key={w}>{w}</li>
                      ))}
                    </ul>
                  ) : null}
                </Card>

                {/* Symptom Analysis */}
                {symptomAnalysis ? (
                  <Card>
                    <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                      1. Symptom Analysis
                    </h2>
                    <p className="mt-1 text-sm text-[var(--text-secondary)]">
                      {symptomAnalysis.narrative}
                    </p>
                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      {symptomAnalysis.clusters.map((cluster) => (
                        <div
                          key={cluster.body_system}
                          className="rounded-xl border border-[var(--border-color)] p-4"
                        >
                          <div className="flex items-center justify-between">
                            <p className="text-sm font-semibold">{cluster.body_system}</p>
                            {cluster.duration_hint ? (
                              <Badge tone="gray">{cluster.duration_hint}</Badge>
                            ) : null}
                          </div>
                          <p className="mt-2 text-sm text-[var(--text-secondary)]">
                            {cluster.symptoms.join(', ')}
                          </p>
                          {cluster.related_conditions.length ? (
                            <p className="mt-2 text-xs text-[var(--text-secondary)]">
                              Related: {cluster.related_conditions.join(', ')}
                            </p>
                          ) : null}
                        </div>
                      ))}
                      {!symptomAnalysis.clusters.length ? (
                        <p className="text-sm text-[var(--text-secondary)]">
                          No symptom clusters available.
                        </p>
                      ) : null}
                    </div>
                  </Card>
                ) : null}

                {/* Differential Diagnoses */}
                <Card>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                      2. Differential Diagnoses
                    </h2>
                    <input
                      type="text"
                      value={conditionFilter}
                      onChange={(e) => setConditionFilter(e.target.value)}
                      placeholder="Filter conditions…"
                      className="w-52 rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-1.5 text-sm"
                    />
                  </div>
                  <div className="mt-4 space-y-3">
                    {filteredDifferentials.length ? (
                      filteredDifferentials.map((d, i) => (
                        <DifferentialCard key={d.condition} item={d} rank={i} />
                      ))
                    ) : (
                      <p className="text-sm text-[var(--text-secondary)]">
                        No matching conditions found.
                      </p>
                    )}
                  </div>
                </Card>

                {/* Disease Probability Scores */}
                <Card>
                  <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                    3. Disease Probability Scores
                  </h2>
                  <div className="mt-4 space-y-3">
                    {probabilities.map((p) => (
                      <div
                        key={p.condition}
                        className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--border-color)] px-4 py-3"
                      >
                        <div>
                          <p className="text-sm font-medium text-[var(--text-primary)]">{p.condition}</p>
                          <p className="text-xs text-[var(--text-secondary)]">
                            {p.risk_category ? `Risk category: ${p.risk_category} · ` : ''}
                            Confidence {(p.confidence * 100).toFixed(0)}%
                          </p>
                        </div>
                        <div className="flex items-center gap-3">
                          <ConfidenceBar
                            value={p.probability_pct / 100}
                            tone={p.probability_pct >= 60 ? 'red' : p.probability_pct >= 35 ? 'amber' : 'gray'}
                          />
                          <span className="text-sm font-semibold">{p.probability_pct.toFixed(0)}%</span>
                        </div>
                      </div>
                    ))}
                    {!probabilities.length ? (
                      <p className="text-sm text-[var(--text-secondary)]">No probability scores available.</p>
                    ) : null}
                  </div>
                </Card>

                {/* Severity Assessment */}
                {severity ? (
                  <Card>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                        4. Severity Prediction
                      </h2>
                      <Badge tone={severityTone(severity.level)}>{severity.level}</Badge>
                    </div>
                    <div className="mt-3 h-3 overflow-hidden rounded-full bg-black/5 dark:bg-white/10">
                      <div
                        className={`h-full rounded-full transition-all ${
                          severity.score >= 76
                            ? 'bg-red-600'
                            : severity.score >= 51
                              ? 'bg-orange-500'
                              : severity.score >= 31
                                ? 'bg-amber-500'
                                : 'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.min(100, Math.max(4, severity.score))}%` }}
                      />
                    </div>
                    <p className="mt-3 text-sm leading-relaxed text-[var(--text-primary)]">
                      {severity.explanation}
                    </p>
                    {severity.contributing_factors.length ? (
                      <ul className="mt-3 space-y-1 text-sm text-[var(--text-secondary)]">
                        {severity.contributing_factors.map((f) => (
                          <li key={f}>• {f}</li>
                        ))}
                      </ul>
                    ) : null}
                  </Card>
                ) : null}

                {/* Treatment Path */}
                {treatmentPath ? (
                  <Card>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                        5. Treatment Path Recommendation
                      </h2>
                      <Badge tone="blue">{treatmentPath.urgency}</Badge>
                    </div>
                    <div className="mt-4 grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                          Recommended specialists
                        </p>
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {treatmentPath.recommended_specialists.map((s) => (
                            <Badge key={s} tone="blue">{s}</Badge>
                          ))}
                        </div>
                        {treatmentPath.recommended_department ? (
                          <p className="mt-2 text-xs text-[var(--text-secondary)]">
                            Department: {treatmentPath.recommended_department}
                          </p>
                        ) : null}
                      </div>
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                          Diagnostic tests
                        </p>
                        <p className="mt-1 text-sm">
                          {treatmentPath.diagnostic_tests.join(', ') || '—'}
                        </p>
                        {treatmentPath.imaging.length ? (
                          <>
                            <p className="mt-3 text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                              Imaging
                            </p>
                            <p className="mt-1 text-sm">{treatmentPath.imaging.join(', ')}</p>
                          </>
                        ) : null}
                      </div>
                    </div>
                    <p className="mt-4 text-xs italic text-[var(--text-secondary)]">
                      {treatmentPath.notes}
                    </p>
                  </Card>
                ) : null}

                {/* Clinical Decision Support */}
                {cds ? (
                  <Card>
                    <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                      6. Clinical Decision Support Report
                    </h2>
                    <div className="mt-4 grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                          Possible diagnoses
                        </p>
                        <p className="mt-1 text-sm">{cds.possible_diagnoses.join(', ') || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                          Suggested tests
                        </p>
                        <p className="mt-1 text-sm">{cds.suggested_tests.join(', ') || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                          Risk factors
                        </p>
                        <p className="mt-1 text-sm">{cds.risk_factors.join(', ') || '—'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                          Relevant history
                        </p>
                        <p className="mt-1 text-sm">{cds.relevant_history.join(', ') || '—'}</p>
                      </div>
                    </div>
                    <div className="mt-4">
                      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                        Supporting evidence
                      </p>
                      <ul className="mt-2 space-y-1 text-sm text-[var(--text-secondary)]">
                        {cds.supporting_evidence.map((e) => (
                          <li key={e}>• {e}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="mt-4">
                      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                        Clinical notes
                      </p>
                      <ul className="mt-2 space-y-1 text-sm text-[var(--text-secondary)]">
                        {cds.clinical_notes.map((n) => (
                          <li key={n}>{n}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="mt-5 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-xs text-amber-900 dark:text-amber-100">
                      {cds.disclaimer}
                    </div>
                  </Card>
                ) : null}

                {/* History */}
                <Card>
                  <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                    Diagnosis history
                  </h2>
                  {historyQuery.data?.length ? (
                    <ol className="mt-4 space-y-3">
                      {historyQuery.data.map((h) => (
                        <li
                          key={h.id}
                          className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[var(--border-color)] px-3 py-2 text-sm"
                        >
                          <div>
                            <p className="font-medium text-[var(--text-primary)]">
                              {h.top_condition || 'No condition identified'}
                            </p>
                            <p className="text-xs text-[var(--text-secondary)]">
                              {formatWhen(h.created_at)}
                            </p>
                          </div>
                          {h.severity_level ? (
                            <Badge tone={severityTone(h.severity_level)}>{h.severity_level}</Badge>
                          ) : null}
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="mt-3 text-sm text-[var(--text-secondary)]">No prior runs yet.</p>
                  )}
                </Card>
              </>
            ) : null}
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}
