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
    description: 'Clinical decision support and differential suggestions.',
    ready: false,
  },
  {
    path: '/ai/research',
    name: 'Research Agent',
    description: 'Literature and protocol research assistant.',
    ready: false,
  },
  {
    path: '/ai/prescription',
    name: 'Prescription Agent',
    description: 'Medication recommendations and interaction checks.',
    ready: false,
  },
  {
    path: '/ai/scheduling',
    name: 'Scheduling Agent',
    description: 'Smart appointment slot optimization.',
    ready: false,
  },
  {
    path: '/ai/emergency',
    name: 'Emergency Agent',
    description: 'Triage prioritization and escalation.',
    ready: false,
  },
  {
    path: '/ai/digital-twin',
    name: 'Digital Twin',
    description: 'Hospital capacity and flow simulation.',
    ready: false,
  },
  {
    path: '/ai/insurance',
    name: 'Insurance Agent',
    description: 'Coverage checks and claim assistance.',
    ready: false,
  },
  {
    path: '/ai/medical-report',
    name: 'Medical Report Agent',
    description: 'Summaries and structured report generation.',
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
            with sequential stages.
          </p>
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
