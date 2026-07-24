import { Link } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';

const AGENTS = [
  {
    path: '/ai/diagnosis',
    name: 'Diagnosis Agent',
    description: 'Clinical decision support and differential suggestions.',
  },
  {
    path: '/ai/research',
    name: 'Research Agent',
    description: 'Literature and protocol research assistant.',
  },
  {
    path: '/ai/prescription',
    name: 'Prescription Agent',
    description: 'Medication recommendations and interaction checks.',
  },
  {
    path: '/ai/scheduling',
    name: 'Scheduling Agent',
    description: 'Smart appointment slot optimization.',
  },
  {
    path: '/ai/emergency',
    name: 'Emergency Agent',
    description: 'Triage prioritization and escalation.',
  },
  {
    path: '/ai/digital-twin',
    name: 'Digital Twin',
    description: 'Hospital capacity and flow simulation.',
  },
  {
    path: '/ai/insurance',
    name: 'Insurance Agent',
    description: 'Coverage checks and claim assistance.',
  },
  {
    path: '/ai/medical-report',
    name: 'Medical Report Agent',
    description: 'Summaries and structured report generation.',
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
            Multi-agent clinical intelligence — coming in Week 2.
          </p>
        </header>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {AGENTS.map((agent) => (
            <Link
              key={agent.path}
              to={agent.path}
              className="rounded-xl border border-dashed border-[var(--border-color)] bg-[var(--bg-navbar)] p-4 hover:border-primary-500/50"
            >
              <p className="text-sm font-semibold text-[var(--text-primary)]">
                {agent.name}
              </p>
              <p className="mt-1 text-xs text-[var(--text-secondary)]">
                {agent.description}
              </p>
              <p className="mt-3 font-mono text-[10px] uppercase tracking-wider text-primary-600">
                Coming in Week 2
              </p>
            </Link>
          ))}
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
          Coming in Week 2
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
