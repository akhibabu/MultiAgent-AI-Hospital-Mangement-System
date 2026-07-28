import { Link } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';

const AGENTS = [
  {
    path: '/ai/intake',
    name: 'Intake Agent',
    description:
      'Unified workflow: Registration → History → Context → OCR → NER → Risk → Knowledge Graph.',
    ready: true,
  },
  {
    path: '/ai/diagnosis',
    name: 'Diagnosis Agent',
    description:
      'Differential diagnoses, disease probability, severity, and treatment pathways. Assists — never replaces — a physician.',
    ready: true,
  },
  {
    path: '/ai/research',
    name: 'Research Agent',
    description:
      'Evidence-backed literature, clinical trials, guidelines, and drug efficacy for every diagnosis.',
    ready: true,
  },
  {
    path: '/ai/prescription',
    name: 'Prescription Agent',
    description: 'Medication recommendations and interaction checks. (Coming Soon)',
    ready: false,
  },
  {
    path: '/ai/scheduling',
    name: 'Scheduling Agent',
    description: 'Smart appointment slot optimization. (Coming Soon)',
    ready: false,
  },
  {
    path: '/ai/emergency',
    name: 'Emergency Agent',
    description: 'Triage prioritization and escalation. (Coming Soon)',
    ready: false,
  },
  {
    path: '/ai/digital-twin',
    name: 'Digital Twin',
    description: 'Hospital capacity and flow simulation. (Coming Soon)',
    ready: false,
  },
  {
    path: '/ai/insurance',
    name: 'Insurance Agent',
    description: 'Coverage checks and claim assistance. (Coming Soon)',
    ready: false,
  },
  {
    path: '/ai/medical-report',
    name: 'Medical Report Agent',
    description: 'Summaries and structured report generation. (Coming Soon)',
    ready: false,
  },
  {
    path: '/ai/resource-allocation',
    name: 'Resource Allocation Agent',
    description: 'Bed, staff, and equipment allocation optimization. (Coming Soon)',
    ready: false,
  },
];

export default function AICenterPage() {
  return (
    <ErrorBoundary title="AI Center error">
      <section className="space-y-6">
        <header>
          <h2 className="text-2xl font-semibold text-[var(--text-primary)]">
            AI Center
          </h2>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Multi-agent clinical intelligence. The Intake Agent is one workflow
            with sequential stages; Diagnosis and Research consume its output.
          </p>
          <ul className="mt-4 flex flex-wrap gap-2 text-xs">
            <li className="rounded-md border border-emerald-500/40 px-2.5 py-1 font-medium text-emerald-700 dark:text-emerald-300">
              ✓ Intake Agent
            </li>
            <li className="rounded-md border border-emerald-500/40 px-2.5 py-1 font-medium text-emerald-700 dark:text-emerald-300">
              ✓ Diagnosis Agent
            </li>
            <li className="rounded-md border border-emerald-500/40 px-2.5 py-1 font-medium text-emerald-700 dark:text-emerald-300">
              ✓ Research Agent
            </li>
            {AGENTS.filter((a) => !a.ready).map((a) => (
              <li
                key={a.path}
                className="rounded-md border border-dashed border-[var(--border-color)] px-2.5 py-1 text-[var(--text-secondary)]"
              >
                {a.name} (Coming Soon)
              </li>
            ))}
          </ul>
        </header>

        <Link
          to="/ai/intake"
          className="block rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5 transition hover:border-primary-500/50"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-primary-600">
                Intake Agent · Unified Workflow
              </p>
              <h3 className="mt-1 text-lg font-semibold text-[var(--text-primary)]">
                Intake Agent
              </h3>
              <p className="mt-1 max-w-xl text-sm text-[var(--text-secondary)]">
                Staff-friendly intake workflow for doctors and reception.
                Registration through Knowledge Graph — technical details stay in
                Developer Mode.
              </p>
            </div>
            <span className="rounded-md bg-primary-600/10 px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-primary-600">
              Available
            </span>
          </div>
          <ul className="mt-4 flex flex-wrap gap-2 text-xs text-[var(--text-secondary)]">
            <li className="rounded-md border border-emerald-500/40 px-2 py-1 text-emerald-700 dark:text-emerald-300">
              ✓ Registration
            </li>
            <li className="rounded-md border border-emerald-500/40 px-2 py-1 text-emerald-700 dark:text-emerald-300">
              ✓ History
            </li>
            <li className="rounded-md border border-emerald-500/40 px-2 py-1 text-emerald-700 dark:text-emerald-300">
              ✓ Context Builder
            </li>
            <li className="rounded-md border border-emerald-500/40 px-2 py-1 text-emerald-700 dark:text-emerald-300">
              ✓ Document Processing
            </li>
            <li className="rounded-md border border-emerald-500/40 px-2 py-1 text-emerald-700 dark:text-emerald-300">
              ✓ Entity Recognition
            </li>
            <li className="rounded-md border border-emerald-500/40 px-2 py-1 text-emerald-700 dark:text-emerald-300">
              ✓ Risk Profiling
            </li>
            <li className="rounded-md border border-emerald-500/40 px-2 py-1 text-emerald-700 dark:text-emerald-300">
              ✓ Knowledge Graph
            </li>
            <li className="rounded-md border border-emerald-500/40 px-2 py-1 text-emerald-700 dark:text-emerald-300">
              ✓ Intake Completed
            </li>
          </ul>
        </Link>

        <div className="grid gap-4 lg:grid-cols-2">
          <Link
            to="/ai/diagnosis"
            className="block rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5 transition hover:border-primary-500/50"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-primary-600">
                  Diagnosis Agent
                </p>
                <h3 className="mt-1 text-lg font-semibold text-[var(--text-primary)]">
                  Clinical Decision Support
                </h3>
                <p className="mt-1 max-w-xl text-sm text-[var(--text-secondary)]">
                  Symptom analysis, differential diagnoses, probability scoring,
                  severity prediction, and treatment pathways. Assists — never
                  replaces — a physician.
                </p>
              </div>
              <span className="rounded-md bg-primary-600/10 px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-primary-600">
                Available
              </span>
            </div>
          </Link>

          <Link
            to="/ai/research"
            className="block rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5 transition hover:border-primary-500/50"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-primary-600">
                  Research Agent
                </p>
                <h3 className="mt-1 text-lg font-semibold text-[var(--text-primary)]">
                  Evidence Enrichment
                </h3>
                <p className="mt-1 max-w-xl text-sm text-[var(--text-secondary)]">
                  Literature, clinical trials, treatment guidelines, and drug
                  efficacy evidence for every Diagnosis Agent result.
                </p>
              </div>
              <span className="rounded-md bg-primary-600/10 px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-primary-600">
                Available
              </span>
            </div>
          </Link>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
            All agents
          </h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {AGENTS.map((agent) => (
              <Link
                key={agent.path}
                to={agent.path}
                className={`rounded-xl border bg-[var(--bg-navbar)] p-4 hover:border-primary-500/50 ${
                  agent.ready
                    ? 'border-[var(--border-color)]'
                    : 'border-dashed border-[var(--border-color)]'
                }`}
              >
                <p className="text-sm font-semibold text-[var(--text-primary)]">
                  {agent.name}
                </p>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  {agent.description}
                </p>
                <p className="mt-3 font-mono text-[10px] uppercase tracking-wider text-primary-600">
                  {agent.ready ? 'Available' : 'Coming soon'}
                </p>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </ErrorBoundary>
  );
}

export function AIAgentPlaceholderPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <ErrorBoundary title={`${title} error`}>
      <section className="mx-auto max-w-2xl space-y-4 rounded-xl border border-dashed border-[var(--border-color)] bg-[var(--bg-navbar)] p-8 text-center">
        <h2 className="text-2xl font-semibold text-[var(--text-primary)]">
          {title}
        </h2>
        <p className="text-sm text-[var(--text-secondary)]">{description}</p>
        <p className="font-mono text-xs uppercase tracking-wider text-primary-600">
          Coming soon
        </p>
        <Link
          to="/ai"
          className="inline-block rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm"
        >
          Back to AI Center
        </Link>
      </section>
    </ErrorBoundary>
  );
}
