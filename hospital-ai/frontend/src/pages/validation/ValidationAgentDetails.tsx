import { Link, useParams } from 'react-router-dom';
import HumanReviewPanel from '@/components/validation/HumanReviewPanel';
import NotValidatablePanel from '@/components/validation/NotValidatablePanel';
import { ValidationQueryGate } from '@/components/validation/QueryState';
import ValidationStatusBadge from '@/components/validation/ValidationStatusBadge';
import { useSelectedRunId, useValidationAgent } from '@/hooks/useValidation';
import { formatCount, formatHeadlineValue, formatPercent } from '@/utils/validationDisplay';
import {
  applyMedicalReportAgentDemo,
  isMedicalReportAgent,
  MEDICAL_REPORT_DEMO_NOTE,
} from '@/utils/medicalReportValidationDemo';

export default function ValidationAgentDetails() {
  const { agentId = '' } = useParams();
  const runId = useSelectedRunId();
  const query = useValidationAgent(agentId, runId);

  return (
    <ValidationQueryGate query={query} loadingLabel="Loading agent details…">
      {(raw) => {
        const data = isMedicalReportAgent(agentId) ? applyMedicalReportAgentDemo(raw) : raw;
        const agent = data.summary;
        return (
          <section className="space-y-6">
            <header>
              <p className="text-xs uppercase tracking-wide text-[var(--text-secondary)]">
                {agent.agent}
              </p>
              <h1 className="mt-1 text-2xl font-semibold">{agent.agent}</h1>
              <p className="mt-2 max-w-3xl text-sm text-[var(--text-secondary)]">
                {agent.description}
              </p>
              <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
                <div>
                  <dt className="text-xs text-[var(--text-secondary)]">Validated tasks</dt>
                  <dd className="font-semibold tabular-nums">
                    {agent.tasks_validated}/{agent.tasks_total}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-[var(--text-secondary)]">Unsupported</dt>
                  <dd className="font-semibold tabular-nums">{agent.tasks_not_validatable}</dd>
                </div>
                <div>
                  <dt className="text-xs text-[var(--text-secondary)]">Cases scored</dt>
                  <dd className="font-semibold tabular-nums">
                    {formatCount(agent.cases_evaluated)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-[var(--text-secondary)]">Execution success</dt>
                  <dd className="font-semibold tabular-nums">
                    {formatPercent(agent.execution_success_rate)}
                  </dd>
                </div>
              </dl>
              {isMedicalReportAgent(agentId) ? (
                <p className="mt-2 text-xs text-[var(--text-secondary)]">{MEDICAL_REPORT_DEMO_NOTE}</p>
              ) : null}
            </header>

            <div className="overflow-x-auto rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)]">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-[var(--border-color)] text-xs uppercase tracking-wide text-[var(--text-secondary)]">
                  <tr>
                    <th className="px-4 py-3">Task</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Cases</th>
                    <th className="px-4 py-3">Primary metric</th>
                    <th className="px-4 py-3">Value</th>
                  </tr>
                </thead>
                <tbody>
                  {data.tasks.map((task) => (
                    <tr key={task.task_id} className="border-b border-[var(--border-color)] last:border-0">
                      <td className="px-4 py-3">
                        <Link
                          to={`/validation/tasks/${task.task_id}`}
                          className="font-medium hover:underline"
                        >
                          {task.task}
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <ValidationStatusBadge state={task.validation_state} />
                      </td>
                      <td className="px-4 py-3 tabular-nums">
                        {formatCount(task.cases_evaluated)} / {formatCount(task.cases_in_benchmark)}
                      </td>
                      <td className="px-4 py-3">{task.headline?.metric ?? '—'}</td>
                      <td className="px-4 py-3 tabular-nums">
                        {formatHeadlineValue(task.headline?.metric, task.headline?.value)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {data.tasks.some((task) => task.validation_state === 'PENDING_HUMAN_REVIEW') ? (
              <HumanReviewPanel />
            ) : null}
            {data.tasks.some((task) => task.validation_state === 'NOT_VALIDATABLE') ? (
              <NotValidatablePanel reason="Some tasks for this agent have no suitable benchmark." />
            ) : null}
          </section>
        );
      }}
    </ValidationQueryGate>
  );
}
