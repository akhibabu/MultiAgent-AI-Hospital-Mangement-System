/**
 * Research Agent — validates and enriches Diagnosis Agent output with evidence.
 *
 * Never invents medical information. Never prescribes medication.
 */
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import Badge, { type BadgeTone } from '@/components/common/Badge';
import Card from '@/components/common/Card';
import { usePatients } from '@/hooks/usePatients';
import { useDiagnosisResult } from '@/hooks/useDiagnosis';
import {
  useResearchHistory,
  useResearchResult,
  useStartResearch,
} from '@/hooks/useResearch';
import type {
  ClinicalEvidence,
  ClinicalTrialItem,
  DrugEvidenceItem,
  EvidenceLevel,
  GuidelineItem,
  LiteratureItem,
  ResearchRecommendation,
} from '@/types/research';
import { EVIDENCE_LEVEL_TONE } from '@/types/research';

const WORKFLOW_MODULES = [
  {
    id: 'pubmed',
    label: 'PubMed Search',
    description: 'Retrieve research papers, review articles, and case reports.',
  },
  {
    id: 'trials',
    label: 'Clinical Trial Search',
    description: 'Retrieve relevant trials — status, outcomes, and eligibility.',
  },
  {
    id: 'guidelines',
    label: 'Treatment Guideline Retrieval',
    description: 'Retrieve WHO, CDC, hospital, and medical-society guidelines.',
  },
  {
    id: 'drug',
    label: 'Drug Efficacy Analysis',
    description: 'Analyze published effectiveness, side effects, and interactions.',
  },
  {
    id: 'ranking',
    label: 'Evidence Ranking',
    description: 'Rank sources by recency, quality, relevance, and confidence.',
  },
  {
    id: 'recommendation',
    label: 'Recommendation Generation',
    description: 'Synthesize clinician-friendly evidence summaries.',
  },
] as const;

function evidenceTone(level?: string | null): BadgeTone {
  if (!level) return 'gray';
  return EVIDENCE_LEVEL_TONE[level] || 'gray';
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

function RecommendationCard({ item }: { item: ResearchRecommendation }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="rounded-xl border border-[var(--border-color)] p-4">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full flex-wrap items-start justify-between gap-3 text-left"
      >
        <p className="text-sm font-semibold text-[var(--text-primary)]">{item.condition}</p>
        <Badge tone={item.confidence_score >= 0.7 ? 'green' : item.confidence_score >= 0.5 ? 'amber' : 'gray'}>
          Confidence {(item.confidence_score * 100).toFixed(0)}%
        </Badge>
      </button>
      {open ? (
        <div className="mt-3 space-y-3 border-t border-[var(--border-color)] pt-3 text-sm">
          <p className="text-[var(--text-secondary)]">{item.evidence_summary}</p>
          {item.supporting_literature.length ? (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                Supporting literature
              </p>
              <ul className="mt-1 space-y-1">
                {item.supporting_literature.map((l) => (
                  <li key={l}>• {l}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {item.clinical_guidelines.length ? (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                Clinical guidelines
              </p>
              <ul className="mt-1 space-y-1">
                {item.clinical_guidelines.map((g) => (
                  <li key={g}>• {g}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {item.recommended_diagnostic_tests.length ? (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                Recommended diagnostic tests
              </p>
              <p className="mt-1">{item.recommended_diagnostic_tests.join(', ')}</p>
            </div>
          ) : null}
          {item.research_highlights.length ? (
            <ul className="space-y-1 text-xs text-[var(--text-secondary)]">
              {item.research_highlights.map((h) => (
                <li key={h}>• {h}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export default function ResearchAgentPage() {
  const [patientId, setPatientId] = useState('');
  const [search, setSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState<EvidenceLevel | 'All'>('All');

  const patientsQuery = usePatients({
    page: 1,
    page_size: 100,
    sort_by: 'created_at',
    sort_order: 'desc',
  });

  const diagnosisQuery = useDiagnosisResult(patientId || undefined);
  const resultQuery = useResearchResult(patientId || undefined);
  const historyQuery = useResearchHistory(patientId || undefined);
  const startMutation = useStartResearch(patientId || undefined);

  const liveReport = startMutation.data;
  const persisted = resultQuery.data;
  const hasResult = Boolean(liveReport || persisted);

  const conditionsResearched: string[] =
    liveReport?.conditions_researched || persisted?.conditions_researched_json || [];
  const pubmedResults: LiteratureItem[] = liveReport?.pubmed_results || persisted?.pubmed_json || [];
  const clinicalTrials: ClinicalTrialItem[] =
    liveReport?.clinical_trials || persisted?.clinical_trials_json || [];
  const guidelines: GuidelineItem[] = liveReport?.guidelines || persisted?.guidelines_json || [];
  const drugEfficacy: DrugEvidenceItem[] =
    liveReport?.drug_efficacy || persisted?.drug_efficacy_json || [];
  const evidenceCounts: Record<string, number> =
    liveReport?.evidence_level_counts || persisted?.evidence_ranking_summary_json || {};
  const recommendations: ResearchRecommendation[] =
    liveReport?.recommendations || persisted?.recommendation_json || [];
  const evidence: ClinicalEvidence[] = liveReport?.evidence || [];
  const summary = liveReport?.summary || persisted?.summary;
  const warnings = liveReport?.warnings || [];

  const filteredEvidence = useMemo(() => {
    return evidence.filter((e) => {
      if (levelFilter !== 'All' && e.evidence_level !== levelFilter) return false;
      if (search.trim()) {
        const q = search.trim().toLowerCase();
        if (!e.title.toLowerCase().includes(q) && !e.condition.toLowerCase().includes(q)) {
          return false;
        }
      }
      return true;
    });
  }, [evidence, search, levelFilter]);

  const isRunning = startMutation.isPending;
  const isLoadingExisting = resultQuery.isLoading && !hasResult;
  const hasDiagnosis = Boolean(diagnosisQuery.data);

  async function handleRun() {
    if (!patientId) return;
    await startMutation.mutateAsync(diagnosisQuery.data?.id);
  }

  return (
    <ErrorBoundary title="Research Agent error">
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary-600">
                AI Center
              </p>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[var(--text-primary)]">
                Research Agent
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">
                Validates and enriches every Diagnosis Agent result with evidence-backed
                clinical information — literature, trials, guidelines, and published drug
                evidence. Never invents medical information; never prescribes medication.
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
              <p className="text-xs text-[var(--text-secondary)]">Conditions researched</p>
              <p className="mt-1 truncate text-sm font-semibold text-[var(--text-primary)]">
                {conditionsResearched.join(', ') || '—'}
              </p>
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Evidence quality</p>
              <div className="mt-1 flex gap-2 text-xs">
                <Badge tone="green">{evidenceCounts.High || 0} High</Badge>
                <Badge tone="amber">{evidenceCounts.Medium || 0} Med</Badge>
                <Badge tone="gray">{evidenceCounts.Low || 0} Low</Badge>
              </div>
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
            <button
              type="button"
              disabled={!patientId || isRunning}
              onClick={handleRun}
              className="rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {isRunning ? 'Running Research Agent…' : 'Run Research Agent'}
            </button>
            {patientId && !hasDiagnosis ? (
              <Link
                to="/ai/diagnosis"
                className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-2.5 text-sm text-amber-900 dark:text-amber-100"
              >
                Run Diagnosis Agent first for best results
              </Link>
            ) : null}
          </div>
          {startMutation.isError ? (
            <p className="mt-3 text-sm text-red-600">
              Research Agent failed. Try again or check the patient&apos;s records.
            </p>
          ) : null}
        </Card>

        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          {/* Workflow */}
          <Card>
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">Workflow</h2>
            <ol className="mt-5 space-y-0">
              {WORKFLOW_MODULES.map((stage, i) => {
                const status = hasResult ? 'complete' : isRunning ? (i === 0 ? 'active' : 'future') : 'future';
                return (
                  <li key={stage.id} className="relative flex gap-3 pb-5 last:pb-0">
                    {i < WORKFLOW_MODULES.length - 1 ? (
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
                <p className="text-sm text-[var(--text-secondary)]">Loading existing research…</p>
              </Card>
            ) : null}

            {!patientId ? (
              <Card>
                <p className="text-sm text-[var(--text-secondary)]">
                  Select a patient to view or generate research.
                </p>
              </Card>
            ) : null}

            {patientId && !hasResult && !isLoadingExisting ? (
              <Card>
                <p className="text-sm text-[var(--text-secondary)]">
                  No research on record for this patient yet. Run the Research Agent to
                  gather evidence for the latest Diagnosis Agent result.
                </p>
              </Card>
            ) : null}

            {hasResult ? (
              <>
                {/* Summary */}
                <Card>
                  <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                    Research Summary
                  </h2>
                  <p className="mt-2 text-sm leading-relaxed text-[var(--text-primary)]">{summary}</p>
                  {warnings.length ? (
                    <ul className="mt-3 space-y-1 text-sm text-amber-800 dark:text-amber-200">
                      {warnings.map((w) => (
                        <li key={w}>{w}</li>
                      ))}
                    </ul>
                  ) : null}
                </Card>

                {/* Recommendations */}
                <Card>
                  <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                    6. Recommendation Generation
                  </h2>
                  <div className="mt-4 space-y-3">
                    {recommendations.length ? (
                      recommendations.map((r) => <RecommendationCard key={r.condition} item={r} />)
                    ) : (
                      <p className="text-sm text-[var(--text-secondary)]">No recommendations yet.</p>
                    )}
                  </div>
                </Card>

                {/* PubMed */}
                <Card>
                  <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                    1. PubMed Search
                  </h2>
                  <div className="mt-4 space-y-3">
                    {pubmedResults.map((item) => (
                      <div
                        key={item.reference_id}
                        className="rounded-xl border border-[var(--border-color)] p-4"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <p className="text-sm font-medium text-[var(--text-primary)]">{item.title}</p>
                          <Badge tone="gray">{item.study_type}</Badge>
                        </div>
                        <p className="mt-1 text-xs text-[var(--text-secondary)]">
                          {item.journal} · {item.publication_year} · {item.authors.join(', ')}
                        </p>
                        <p className="mt-2 text-sm text-[var(--text-secondary)]">{item.summary}</p>
                      </div>
                    ))}
                    {!pubmedResults.length ? (
                      <p className="text-sm text-[var(--text-secondary)]">No literature retrieved.</p>
                    ) : null}
                  </div>
                </Card>

                {/* Clinical Trials */}
                <Card>
                  <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                    2. Clinical Trial Search
                  </h2>
                  <div className="mt-4 space-y-3">
                    {clinicalTrials.map((item) => (
                      <div
                        key={item.trial_id}
                        className="rounded-xl border border-[var(--border-color)] p-4"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <p className="text-sm font-medium text-[var(--text-primary)]">{item.title}</p>
                          <Badge tone={item.status === 'Completed' ? 'green' : 'blue'}>{item.status}</Badge>
                        </div>
                        <p className="mt-1 text-xs text-[var(--text-secondary)]">
                          {item.trial_id} · {item.phase}
                        </p>
                        <p className="mt-2 text-sm text-[var(--text-secondary)]">{item.outcome_summary}</p>
                        <p className="mt-1 text-xs text-[var(--text-secondary)]">
                          Eligibility: {item.eligibility_summary}
                        </p>
                      </div>
                    ))}
                    {!clinicalTrials.length ? (
                      <p className="text-sm text-[var(--text-secondary)]">No clinical trials retrieved.</p>
                    ) : null}
                  </div>
                </Card>

                {/* Guidelines */}
                <Card>
                  <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                    3. Treatment Guideline Retrieval
                  </h2>
                  <div className="mt-4 space-y-3">
                    {guidelines.map((item) => (
                      <div
                        key={`${item.source}-${item.title}`}
                        className="rounded-xl border border-[var(--border-color)] p-4"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <p className="text-sm font-medium text-[var(--text-primary)]">{item.title}</p>
                          <Badge tone="blue">{item.source}</Badge>
                        </div>
                        <p className="mt-1 text-xs text-[var(--text-secondary)]">
                          Published {item.published_year}
                        </p>
                        <p className="mt-2 text-sm text-[var(--text-secondary)]">{item.recommendation}</p>
                      </div>
                    ))}
                    {!guidelines.length ? (
                      <p className="text-sm text-[var(--text-secondary)]">No guidelines retrieved.</p>
                    ) : null}
                  </div>
                </Card>

                {/* Drug Efficacy */}
                <Card>
                  <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                    4. Drug Efficacy Analysis
                  </h2>
                  <p className="mt-1 text-xs text-[var(--text-secondary)]">
                    Analysis of published evidence only — this system does not prescribe drugs.
                  </p>
                  <div className="mt-4 space-y-3">
                    {drugEfficacy.map((item) => (
                      <div
                        key={`${item.drug_name}-${item.condition}`}
                        className="rounded-xl border border-[var(--border-color)] p-4"
                      >
                        <p className="text-sm font-medium text-[var(--text-primary)]">
                          {item.drug_name} <span className="text-[var(--text-secondary)]">for {item.condition}</span>
                        </p>
                        <p className="mt-2 text-sm text-[var(--text-secondary)]">{item.effectiveness_summary}</p>
                        <div className="mt-2 grid gap-2 text-xs text-[var(--text-secondary)] sm:grid-cols-3">
                          <p>Side effects: {item.known_side_effects.join(', ') || '—'}</p>
                          <p>Contraindications: {item.contraindications.join(', ') || '—'}</p>
                          <p>Interactions: {item.drug_interactions.join(', ') || '—'}</p>
                        </div>
                      </div>
                    ))}
                    {!drugEfficacy.length ? (
                      <p className="text-sm text-[var(--text-secondary)]">No drug evidence retrieved.</p>
                    ) : null}
                  </div>
                </Card>

                {/* Evidence Ranking */}
                <Card>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                      5. Evidence Ranking
                    </h2>
                    <div className="flex flex-wrap gap-2">
                      <input
                        type="text"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Search evidence…"
                        className="w-44 rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-1.5 text-sm"
                      />
                      <select
                        value={levelFilter}
                        onChange={(e) => setLevelFilter(e.target.value as EvidenceLevel | 'All')}
                        className="rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-1.5 text-sm"
                      >
                        <option value="All">All levels</option>
                        <option value="High">High</option>
                        <option value="Medium">Medium</option>
                        <option value="Low">Low</option>
                      </select>
                    </div>
                  </div>
                  {!evidence.length ? (
                    <p className="mt-3 text-sm text-[var(--text-secondary)]">
                      Evidence ranking is only available immediately after a fresh run.
                    </p>
                  ) : (
                    <ul className="mt-4 space-y-2">
                      {filteredEvidence.map((e, idx) => (
                        <li
                          key={`${e.reference_id}-${idx}`}
                          className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[var(--border-color)] px-3 py-2 text-sm"
                        >
                          <div>
                            <p className="font-medium text-[var(--text-primary)]">{e.title}</p>
                            <p className="text-xs text-[var(--text-secondary)]">
                              {e.evidence_type} · {e.condition} · {e.source}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge tone={evidenceTone(e.evidence_level)}>{e.evidence_level}</Badge>
                            <span className="text-xs text-[var(--text-secondary)]">
                              {(e.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </Card>

                {/* History */}
                <Card>
                  <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                    Research history
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
                              {h.conditions_researched.join(', ') || 'No conditions'}
                            </p>
                            <p className="text-xs text-[var(--text-secondary)]">{formatWhen(h.created_at)}</p>
                          </div>
                          <Badge tone="gray">{h.status}</Badge>
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
