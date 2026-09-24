import { Link } from 'react-router-dom';
import Card from '@/components/common/Card';

type AgentValidation = {
  agent: string;
  checks: number;
  passed: number;
  scope: string;
  details: string;
};

const OPERATIONAL_VALIDATION: AgentValidation[] = [
  {
    agent: 'Emergency Agent',
    checks: 17,
    passed: 17,
    scope: 'Deterministic operational verification',
    details:
      'Vital thresholds, critical-event detection, triage escalation, ICU signalling, alert generation, and bounded priority scoring.',
  },
  {
    agent: 'Scheduling Agent',
    checks: 15,
    passed: 15,
    scope: 'Deterministic operational verification',
    details:
      'Doctor matching, appointment slots, surgery planning, follow-up intervals, queue ordering, and workload balancing.',
  },
  {
    agent: 'Resource Allocation Agent',
    checks: 12,
    passed: 12,
    scope: 'Deterministic operational verification',
    details:
      'Upstream context, resource and specialist matching, shortages, conflicts, priority ordering, and allocation-score invariants.',
  },
];

export default function ValidationCenterPage() {
  const totalChecks = OPERATIONAL_VALIDATION.reduce((sum, item) => sum + item.checks, 0);
  const passedChecks = OPERATIONAL_VALIDATION.reduce((sum, item) => sum + item.passed, 0);

  return (
    <section className="mx-auto max-w-6xl space-y-8">
      <header className="space-y-3">
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary-600">
          Quality & Verification
        </p>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-[var(--text-primary)]">
              Validation Center
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[var(--text-secondary)]">
              Central view of the project&apos;s validation evidence. Dataset-grounded
              evaluation and deterministic operational verification are kept separate
              so the dashboard does not turn unlike metrics into a meaningless single score.
            </p>
          </div>
          <Link
            to="/ai"
            className="rounded-xl border border-[var(--border-color)] px-3 py-2 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-navbar)]"
          >
            Back to AI Center
          </Link>
        </div>
      </header>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-xs text-[var(--text-secondary)]">Operational checks</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">
            {passedChecks}/{totalChecks}
          </p>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">Verified by GitHub Actions</p>
        </Card>
        <Card>
          <p className="text-xs text-[var(--text-secondary)]">Operational pass rate</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">
            {totalChecks ? Math.round((passedChecks / totalChecks) * 100) : 0}%
          </p>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">Engineering verification only</p>
        </Card>
        <Card>
          <p className="text-xs text-[var(--text-secondary)]">Last recorded run</p>
          <p className="mt-1 text-lg font-semibold">24 Sep 2026</p>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">Operational Agent Validation</p>
        </Card>
      </div>

      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold">Emergency, Scheduling & Resource Allocation</h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              These three agents are currently validated through deterministic behavioral
              checks rather than a clinician-labelled accuracy benchmark.
            </p>
          </div>
          <span className="rounded-full border border-emerald-500/30 px-3 py-1 text-xs font-medium text-emerald-600">
            {passedChecks}/{totalChecks} checks passed
          </span>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          {OPERATIONAL_VALIDATION.map((item) => (
            <div
              key={item.agent}
              className="rounded-xl border border-[var(--border-color)] p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold">{item.agent}</h3>
                  <p className="mt-1 text-xs text-[var(--text-secondary)]">{item.scope}</p>
                </div>
                <span className="rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-600">
                  {item.passed}/{item.checks}
                </span>
              </div>
              <p className="mt-4 text-sm leading-relaxed text-[var(--text-secondary)]">
                {item.details}
              </p>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h2 className="text-base font-semibold">How to interpret the results</h2>
        <div className="mt-4 space-y-3 text-sm leading-relaxed text-[var(--text-secondary)]">
          <p>
            <span className="font-medium text-[var(--text-primary)]">Operational verification:</span>{' '}
            a passed check means the implementation satisfied the deterministic invariant
            represented by that verification fixture.
          </p>
          <p>
            <span className="font-medium text-[var(--text-primary)]">Dataset-grounded validation:</span>{' '}
            benchmark-backed agents use task-specific metrics such as F1, Recall@5,
            NDCG@5, or field accuracy. Those values should not be averaged with the
            44 operational checks above.
          </p>
          <p>
            <span className="font-medium text-[var(--text-primary)]">Clinical limitation:</span>{' '}
            the operational suite is not evidence of clinical accuracy, clinical safety,
            or readiness for patient care. Emergency triage and ICU outputs remain
            project-level decision-support signals.
          </p>
        </div>
      </Card>
    </section>
  );
}
