/**
 * Prescription Agent — physician-review treatment recommendations.
 *
 * Consumes Diagnosis Agent + Research Agent output plus Patient Context.
 * NEVER a final prescription. NEVER replaces a physician. Technical/raw
 * output lives only under Developer Mode.
 */
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import Badge, { type BadgeTone } from '@/components/common/Badge';
import Card from '@/components/common/Card';
import { usePatients } from '@/hooks/usePatients';
import {
  usePrescriptionHistory,
  usePrescriptionResult,
  useStartPrescription,
} from '@/hooks/usePrescription';
import { useStartMedicalReport } from '@/hooks/useMedicalReport';
import type {
  AllergyCheckItem,
  DosageRecommendation,
  DrugInteraction,
  MedicationRecommendation,
  PrescriptionValidation,
  TreatmentPlan,
} from '@/types/prescription';
import {
  ALLERGY_STATUS_TONE,
  APPROVAL_STATUS_TONE,
  INTERACTION_LEVEL_TONE,
} from '@/types/prescription';

const WORKFLOW_STAGES = [
  {
    id: 'selection',
    label: 'Medication Selection',
    description: 'Recommend medications supported by diagnosis, evidence, and guidelines.',
  },
  {
    id: 'interaction',
    label: 'Drug Interaction Check',
    description: 'Analyze current + suggested medications for known interactions.',
  },
  {
    id: 'allergy',
    label: 'Allergy Verification',
    description: 'Compare patient allergies against drug ingredients and cross-reactivity.',
  },
  {
    id: 'dosage',
    label: 'Dosage Optimization',
    description: 'Estimate dosage ranges from age, weight, organ function, and severity.',
  },
  {
    id: 'plan',
    label: 'Treatment Plan Creation',
    description: 'Synthesize medication plan, lifestyle advice, monitoring, and follow-up.',
  },
  {
    id: 'validation',
    label: 'Prescription Validation',
    description: 'Final safety gate — duplicates, contraindications, confidence, approval status.',
  },
] as const;

function approvalTone(status?: string | null): BadgeTone {
  if (!status) return 'gray';
  return APPROVAL_STATUS_TONE[status] || 'gray';
}

function interactionTone(level?: string | null): BadgeTone {
  if (!level) return 'gray';
  return INTERACTION_LEVEL_TONE[level] || 'gray';
}

function allergyTone(status?: string | null): BadgeTone {
  if (!status) return 'gray';
  return ALLERGY_STATUS_TONE[status] || 'gray';
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

function MedicationCard({ item }: { item: MedicationRecommendation }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-[var(--border-color)] p-4">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full flex-wrap items-start justify-between gap-3 text-left"
      >
        <div>
          <p className="text-xs text-[var(--text-secondary)]">{item.condition} · {item.drug_class}</p>
          <p className="mt-0.5 text-sm font-semibold text-[var(--text-primary)]">{item.medication_name}</p>
        </div>
        <ConfidenceBar value={item.confidence} tone={item.confidence >= 0.7 ? 'green' : 'amber'} />
      </button>
      {open ? (
        <div className="mt-4 space-y-2 border-t border-[var(--border-color)] pt-3 text-sm">
          <p><span className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Purpose: </span>{item.purpose}</p>
          <p><span className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Evidence source: </span>{item.evidence_source}</p>
          <p><span className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Clinical guideline: </span>{item.clinical_guideline}</p>
          <p><span className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Expected outcome: </span>{item.expected_outcome}</p>
          {item.alternative_drugs.length ? (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Alternative drugs</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {item.alternative_drugs.map((d) => (
                  <Badge key={d} tone="blue">{d}</Badge>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export default function PrescriptionAgentPage() {
  const [patientId, setPatientId] = useState('');
  const [medicationFilter, setMedicationFilter] = useState('');
  const [devOpen, setDevOpen] = useState(false);

  const patientsQuery = usePatients({
    page: 1,
    page_size: 100,
    sort_by: 'created_at',
    sort_order: 'desc',
  });

  const resultQuery = usePrescriptionResult(patientId || undefined);
  const historyQuery = usePrescriptionHistory(patientId || undefined);
  const startMutation = useStartPrescription(patientId || undefined);
  const startReportMutation = useStartMedicalReport(patientId || undefined);

  const liveReport = startMutation.data;
  const persisted = resultQuery.data;
  const hasResult = Boolean(liveReport || persisted);

  const medications: MedicationRecommendation[] =
    liveReport?.medication_recommendations || persisted?.medication_recommendations_json || [];
  const interactions: DrugInteraction[] =
    liveReport?.drug_interactions || persisted?.drug_interactions_json || [];
  const allergyChecks: AllergyCheckItem[] =
    liveReport?.allergy_checks || persisted?.allergy_checks_json || [];
  const dosages: DosageRecommendation[] =
    liveReport?.dosage_recommendations || persisted?.dosage_recommendations_json || [];
  const treatmentPlan: TreatmentPlan | undefined =
    liveReport?.treatment_plan || persisted?.treatment_plan_json;
  const validation: PrescriptionValidation | undefined =
    liveReport?.validation || persisted?.validation_summary_json;
  const summary = liveReport?.summary || persisted?.summary;
  const warnings = liveReport?.warnings || [];
  const targetConditions = liveReport?.target_conditions || persisted?.target_conditions_json || [];
  const prescriptionResultId = liveReport?.prescription_result?.id || persisted?.id;

  const filteredMedications = useMemo(() => {
    if (!medicationFilter.trim()) return medications;
    const q = medicationFilter.trim().toLowerCase();
    return medications.filter(
      (m) => m.medication_name.toLowerCase().includes(q) || m.condition.toLowerCase().includes(q),
    );
  }, [medications, medicationFilter]);

  const isRunning = startMutation.isPending;
  const isLoadingExisting = resultQuery.isLoading && !hasResult;

  async function handleRun() {
    if (!patientId) return;
    await startMutation.mutateAsync(undefined);
  }

  async function handleGenerateReport() {
    if (!patientId) return;
    await startReportMutation.mutateAsync({ prescription_result_id: prescriptionResultId });
  }

  return (
    <ErrorBoundary title="Prescription Agent error">
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary-600">
                AI Center
              </p>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[var(--text-primary)]">
                Prescription Agent
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">
                Generates physician-review treatment recommendations from Diagnosis Agent and
                Research Agent output. Never a final prescription — assists, never replaces, a
                physician.
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
              <p className="text-xs text-[var(--text-secondary)]">Approval status</p>
              {validation ? (
                <Badge tone={approvalTone(validation.approval_status)}>{validation.approval_status}</Badge>
              ) : (
                <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">—</p>
              )}
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Confidence</p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                {validation ? `${Math.round(validation.confidence_score * 100)}%` : '—'}
              </p>
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
            <label className="min-w-[260px] flex-1 text-sm">
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
              disabled={!patientId || isRunning}
              onClick={handleRun}
              className="rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {isRunning ? 'Running Prescription Agent…' : 'Run Prescription Agent'}
            </button>
            {hasResult ? (
              <button
                type="button"
                disabled={!patientId || startReportMutation.isPending}
                onClick={handleGenerateReport}
                className="rounded-xl border border-[var(--border-color)] px-4 py-2.5 text-sm font-medium text-[var(--text-primary)] disabled:opacity-50"
              >
                {startReportMutation.isPending ? 'Generating Medical Report…' : 'Send to Medical Report Agent'}
              </button>
            ) : null}
          </div>
          {startMutation.isError ? (
            <p className="mt-3 text-sm text-red-600">
              Prescription Agent failed. Ensure the patient has a completed Diagnosis Agent run.
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
                <p className="text-sm text-[var(--text-secondary)]">Loading existing prescription…</p>
              </Card>
            ) : null}

            {resultQuery.isError && !hasResult && patientId ? (
              <Card>
                <p className="text-sm text-[var(--text-secondary)]">
                  No prescription on record for this patient yet. Run the Prescription Agent to generate one.
                </p>
              </Card>
            ) : null}

            {!patientId ? (
              <Card>
                <p className="text-sm text-[var(--text-secondary)]">
                  Select a patient to view or generate a treatment recommendation.
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
                        Prescription Summary
                      </h2>
                      <p className="mt-2 text-sm leading-relaxed text-[var(--text-primary)]">{summary}</p>
                      {targetConditions.length ? (
                        <p className="mt-2 text-xs text-[var(--text-secondary)]">
                          Target conditions: {targetConditions.join(', ')}
                        </p>
                      ) : null}
                    </div>
                    {validation ? (
                      <Badge tone={approvalTone(validation.approval_status)}>
                        {validation.approval_status}
                      </Badge>
                    ) : null}
                  </div>
                  {warnings.length ? (
                    <ul className="mt-3 space-y-1 text-sm text-amber-800 dark:text-amber-200">
                      {warnings.map((w) => (
                        <li key={w}>{w}</li>
                      ))}
                    </ul>
                  ) : null}
                  <div className="mt-4 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-xs text-amber-900 dark:text-amber-100">
                    Physician-review recommendation only. NOT a final prescription — a licensed
                    physician must review, adjust, and sign off before any medication is dispensed.
                  </div>
                </Card>

                {/* 1. Medication Cards */}
                <Card>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                      1. Medication Selection
                    </h2>
                    <input
                      type="text"
                      value={medicationFilter}
                      onChange={(e) => setMedicationFilter(e.target.value)}
                      placeholder="Search medications…"
                      className="w-52 rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-1.5 text-sm"
                    />
                  </div>
                  <div className="mt-4 space-y-3">
                    {filteredMedications.length ? (
                      filteredMedications.map((m, i) => (
                        <MedicationCard key={`${m.medication_name}-${m.condition}-${i}`} item={m} />
                      ))
                    ) : (
                      <p className="text-sm text-[var(--text-secondary)]">No medications recommended.</p>
                    )}
                  </div>
                </Card>

                {/* 2. Interaction Report */}
                <Card>
                  <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                    2. Drug Interaction Check
                  </h2>
                  <div className="mt-4 space-y-3">
                    {interactions.length ? (
                      interactions.map((i, idx) => (
                        <div
                          key={`${i.drug_a}-${i.drug_b}-${idx}`}
                          className="rounded-xl border border-[var(--border-color)] p-4"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-sm font-semibold text-[var(--text-primary)]">
                              {i.drug_a} + {i.drug_b}
                            </p>
                            <Badge tone={interactionTone(i.interaction_level)}>{i.interaction_level}</Badge>
                          </div>
                          <p className="mt-2 text-sm text-[var(--text-secondary)]">{i.explanation}</p>
                          <p className="mt-1 text-xs italic text-[var(--text-secondary)]">{i.recommendation}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-[var(--text-secondary)]">No known interactions detected.</p>
                    )}
                  </div>
                </Card>

                {/* 3. Allergy Report */}
                <Card>
                  <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                    3. Allergy Verification
                  </h2>
                  <div className="mt-4 space-y-3">
                    {allergyChecks.length ? (
                      allergyChecks.map((a) => (
                        <div
                          key={a.medication_name}
                          className="rounded-xl border border-[var(--border-color)] p-4"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-sm font-semibold text-[var(--text-primary)]">{a.medication_name}</p>
                            <Badge tone={allergyTone(a.status)}>{a.status}</Badge>
                          </div>
                          <p className="mt-2 text-sm text-[var(--text-secondary)]">{a.reason}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-[var(--text-secondary)]">No allergy checks available.</p>
                    )}
                  </div>
                </Card>

                {/* 4. Dosage Suggestions */}
                <Card>
                  <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                    4. Dosage Optimization
                  </h2>
                  <p className="mt-1 text-xs italic text-[var(--text-secondary)]">
                    Dosage ranges only — never a final prescribed dose.
                  </p>
                  <div className="mt-4 space-y-3">
                    {dosages.length ? (
                      dosages.map((d) => (
                        <div
                          key={d.medication_name}
                          className="rounded-xl border border-[var(--border-color)] p-4"
                        >
                          <p className="text-sm font-semibold text-[var(--text-primary)]">{d.medication_name}</p>
                          <div className="mt-2 grid gap-2 sm:grid-cols-3 text-sm">
                            <p><span className="text-xs text-[var(--text-secondary)]">Starting: </span>{d.starting_dose || '—'}</p>
                            <p><span className="text-xs text-[var(--text-secondary)]">Maintenance: </span>{d.maintenance_dose || '—'}</p>
                            <p><span className="text-xs text-[var(--text-secondary)]">Maximum: </span>{d.maximum_dose || '—'}</p>
                          </div>
                          {d.dose_adjustment.length ? (
                            <ul className="mt-2 space-y-1 text-xs text-[var(--text-secondary)]">
                              {d.dose_adjustment.map((note) => (
                                <li key={note}>• {note}</li>
                              ))}
                            </ul>
                          ) : null}
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-[var(--text-secondary)]">No dosage recommendations available.</p>
                    )}
                  </div>
                </Card>

                {/* 5. Treatment Plan */}
                {treatmentPlan ? (
                  <Card>
                    <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                      5. Treatment Plan Creation
                    </h2>
                    <div className="mt-4 grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Medication plan</p>
                        <ul className="mt-1 space-y-1 text-sm">
                          {treatmentPlan.medication_plan.map((m) => (
                            <li key={m}>• {m}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Lifestyle advice</p>
                        <ul className="mt-1 space-y-1 text-sm">
                          {treatmentPlan.lifestyle_advice.map((l) => (
                            <li key={l}>• {l}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Monitoring plan</p>
                        <ul className="mt-1 space-y-1 text-sm">
                          {treatmentPlan.monitoring_plan.map((m) => (
                            <li key={m}>• {m}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Recommended tests / imaging</p>
                        <p className="mt-1 text-sm">
                          {[...treatmentPlan.recommended_lab_tests, ...treatmentPlan.recommended_imaging].join(', ') || '—'}
                        </p>
                        <p className="mt-2 text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Recommended specialists</p>
                        <div className="mt-1 flex flex-wrap gap-1.5">
                          {treatmentPlan.recommended_specialists.map((s) => (
                            <Badge key={s} tone="blue">{s}</Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="mt-4 grid gap-2 sm:grid-cols-2 text-sm">
                      <p><span className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Follow-up interval: </span>{treatmentPlan.follow_up_interval}</p>
                    </div>
                    <div className="mt-3 rounded-xl border border-red-500/30 bg-red-500/5 px-4 py-3 text-xs text-red-800 dark:text-red-200">
                      <span className="font-semibold">Emergency advice: </span>{treatmentPlan.emergency_advice}
                    </div>
                  </Card>
                ) : null}

                {/* 6. Validation Report */}
                {validation ? (
                  <Card>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                        6. Prescription Validation Report
                      </h2>
                      <Badge tone={approvalTone(validation.approval_status)}>{validation.approval_status}</Badge>
                    </div>
                    <div className="mt-3 flex items-center gap-3">
                      <ConfidenceBar
                        value={validation.confidence_score}
                        tone={validation.confidence_score >= 0.7 ? 'green' : validation.confidence_score >= 0.4 ? 'amber' : 'red'}
                      />
                    </div>
                    <div className="mt-4 grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Duplicate drugs</p>
                        <p className="mt-1 text-sm">{validation.duplicate_drugs.join(', ') || 'None'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Contraindications found</p>
                        <p className="mt-1 text-sm">{validation.contraindications_found.join(', ') || 'None'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Allergy conflicts</p>
                        <p className="mt-1 text-sm">{validation.allergy_conflicts.join(', ') || 'None'}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Max dose flags</p>
                        <p className="mt-1 text-sm">{validation.max_dose_exceeded.join(', ') || 'None'}</p>
                      </div>
                    </div>
                    {validation.drug_warnings.length ? (
                      <div className="mt-4">
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Warnings</p>
                        <ul className="mt-2 space-y-1 text-sm text-amber-800 dark:text-amber-200">
                          {validation.drug_warnings.map((w) => (
                            <li key={w}>• {w}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    <div className="mt-4">
                      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">Notes</p>
                      <ul className="mt-2 space-y-1 text-sm text-[var(--text-secondary)]">
                        {validation.notes.map((n) => (
                          <li key={n}>{n}</li>
                        ))}
                      </ul>
                    </div>
                  </Card>
                ) : null}

                {/* History */}
                <Card>
                  <h2 className="text-sm font-semibold text-[var(--text-primary)]">Prescription history</h2>
                  {historyQuery.data?.length ? (
                    <ol className="mt-4 space-y-3">
                      {historyQuery.data.map((h) => (
                        <li
                          key={h.id}
                          className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[var(--border-color)] px-3 py-2 text-sm"
                        >
                          <div>
                            <p className="font-medium text-[var(--text-primary)]">
                              {h.target_conditions.join(', ') || 'No conditions on record'}
                            </p>
                            <p className="text-xs text-[var(--text-secondary)]">{formatWhen(h.created_at)}</p>
                          </div>
                          {h.approval_status ? (
                            <Badge tone={approvalTone(h.approval_status)}>{h.approval_status}</Badge>
                          ) : null}
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="mt-3 text-sm text-[var(--text-secondary)]">No prior runs yet.</p>
                  )}
                </Card>

                {/* Developer Mode */}
                <Card className="border-dashed">
                  <button
                    type="button"
                    onClick={() => setDevOpen((v) => !v)}
                    className="flex w-full items-center justify-between text-left"
                  >
                    <div>
                      <p className="text-sm font-semibold text-[var(--text-primary)]">Developer Mode</p>
                      <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                        Raw pipeline output and stage JSON. Hidden from clinical use.
                      </p>
                    </div>
                    <span className="text-xs text-primary-600">{devOpen ? 'Collapse' : 'Expand'}</span>
                  </button>
                  {devOpen ? (
                    <pre className="mt-4 max-h-96 overflow-auto rounded-lg bg-black/5 p-3 text-[11px] leading-relaxed dark:bg-white/5">
                      {JSON.stringify(liveReport || persisted, null, 2)}
                    </pre>
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
