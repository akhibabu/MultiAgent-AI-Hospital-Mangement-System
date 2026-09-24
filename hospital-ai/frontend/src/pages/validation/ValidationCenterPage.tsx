import { useEffect, useMemo, useState } from 'react';
import apiClient from '@/services/apiClient';

type Task = {
  task_id: string;
  task: string;
  status: string;
  cases_evaluated: number;
  cases_in_benchmark: number;
  metric?: string | null;
  value?: number | null;
  planned_metric?: string | null;
  dataset?: string | null;
  note?: string | null;
};
type Agent = { agent_id: string; agent: string; tasks: Task[] };
type Overview = { as_of?: string; source?: string; disclaimer: string; agents: Agent[] };
type CaseRow = { case_id: string; task_id: string; status: string; prediction?: unknown; ground_truth?: unknown; metrics?: Record<string, unknown> };

function statusClass(status: string) {
  if (status === 'VALIDATED') return 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600';
  if (status === 'PENDING_HUMAN_REVIEW') return 'border-amber-500/30 bg-amber-500/10 text-amber-600';
  if (status === 'PENDING_DATASET') return 'border-blue-500/30 bg-blue-500/10 text-blue-600';
  if (status === 'IN_PROGRESS') return 'border-violet-500/30 bg-violet-500/10 text-violet-600';
  return 'border-slate-500/30 bg-slate-500/10 text-[var(--text-secondary)]';
}

export default function ValidationCenterPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [selectedAgent, setSelectedAgent] = useState('intake');
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [caseLoading, setCaseLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.get<Overview>('/validation/overview')
      .then((response) => setData(response.data))
      .catch(() => setError('Validation data could not be loaded. Check that the backend is running.'))
      .finally(() => setLoading(false));
  }, []);

  const agent = useMemo(
    () => data?.agents.find((item) => item.agent_id === selectedAgent),
    [data, selectedAgent],
  );

  async function openTask(task: Task) {
    setSelectedTask(task);
    setCaseLoading(true);
    try {
      const response = await apiClient.get<{ cases: CaseRow[] }>(`/validation/tasks/${task.task_id}`);
      setCases(response.data.cases ?? []);
    } catch {
      setCases([]);
    } finally {
      setCaseLoading(false);
    }
  }

  if (loading) return <section className="p-6 text-sm text-[var(--text-secondary)]">Loading validation evidence…</section>;
  if (error || !data) return <section className="p-6"><h1 className="text-2xl font-semibold">Validation Center</h1><p className="mt-2 text-sm text-red-600">{error ?? 'Validation data is unavailable.'}</p></section>;

  const validatedTasks = data.agents.reduce((total, item) => total + item.tasks.filter((task) => task.status === 'VALIDATED').length, 0);
  const totalTasks = data.agents.reduce((total, item) => total + item.tasks.length, 0);
  const evaluatedCases = data.agents.reduce((total, item) => total + item.tasks.reduce((subtotal, task) => subtotal + task.cases_evaluated, 0), 0);
  const benchmarkCases = data.agents.reduce((total, item) => total + item.tasks.reduce((subtotal, task) => subtotal + task.cases_in_benchmark, 0), 0);

  return (
    <section className="mx-auto max-w-7xl space-y-6">
      <header>
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary-600">Dataset-grounded evaluation</p>
        <h1 className="mt-1 text-3xl font-semibold">Validation Center</h1>
        <p className="mt-2 max-w-5xl text-sm leading-relaxed text-[var(--text-secondary)]">{data.disclaimer}</p>
      </header>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-[var(--border-color)] p-4"><p className="text-xs text-[var(--text-secondary)]">Validated tasks</p><p className="mt-1 text-2xl font-semibold">{validatedTasks}/{totalTasks}</p></div>
        <div className="rounded-xl border border-[var(--border-color)] p-4"><p className="text-xs text-[var(--text-secondary)]">Cases evaluated</p><p className="mt-1 text-2xl font-semibold tabular-nums">{evaluatedCases.toLocaleString()}</p></div>
        <div className="rounded-xl border border-[var(--border-color)] p-4"><p className="text-xs text-[var(--text-secondary)]">Benchmark cases</p><p className="mt-1 text-2xl font-semibold tabular-nums">{benchmarkCases.toLocaleString()}</p></div>
      </div>

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        {data.agents.map((item) => (
          <button
            key={item.agent_id}
            type="button"
            onClick={() => { setSelectedAgent(item.agent_id); setSelectedTask(null); setCases([]); }}
            className={`rounded-xl border p-3 text-left transition ${selectedAgent === item.agent_id ? 'border-primary-500 bg-primary-500/5' : 'border-[var(--border-color)] hover:bg-[var(--bg-navbar)]'}`}
          >
            <div className="text-sm font-semibold">{item.agent.replace(' Agent', '')}</div>
            <div className="mt-1 text-xs text-[var(--text-secondary)]">{item.tasks.filter((task) => task.status === 'VALIDATED').length}/{item.tasks.length} validated</div>
            <div className="mt-1 text-xs text-[var(--text-secondary)]">{item.tasks.reduce((s, task) => s + task.cases_evaluated, 0).toLocaleString()} cases</div>
          </button>
        ))}
      </div>

      {agent ? (
        <div className="overflow-x-auto rounded-xl border border-[var(--border-color)]">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-[var(--border-color)] bg-[var(--bg-navbar)] text-xs uppercase tracking-wide text-[var(--text-secondary)]">
              <tr><th className="px-4 py-3">Task</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Cases</th><th className="px-4 py-3">Metric</th><th className="px-4 py-3">Result</th></tr>
            </thead>
            <tbody>
              {agent.tasks.map((task) => (
                <tr key={task.task_id} className="border-b border-[var(--border-color)] last:border-0">
                  <td className="px-4 py-3">
                    <button type="button" onClick={() => openTask(task)} className="text-left font-medium hover:underline">{task.task}</button>
                    {task.dataset ? <p className="mt-1 text-xs text-[var(--text-secondary)]">Dataset: {task.dataset}</p> : null}
                  </td>
                  <td className="px-4 py-3"><span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${statusClass(task.status)}`}>{task.status.replace(/_/g, ' ')}</span></td>
                  <td className="px-4 py-3 tabular-nums">{task.cases_evaluated.toLocaleString()} / {task.cases_in_benchmark.toLocaleString()}</td>
                  <td className="px-4 py-3">{task.metric ?? task.planned_metric ?? '—'}</td>
                  <td className="px-4 py-3 tabular-nums">{task.value == null ? '—' : `${task.value.toFixed(1)}%`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {selectedTask ? (
        <div className="rounded-xl border border-[var(--border-color)] p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div><h2 className="text-lg font-semibold">{selectedTask.task}</h2><p className="mt-1 text-sm text-[var(--text-secondary)]">{selectedTask.note ?? 'Per-case predictions and ground truth are shown when a benchmark result file is available.'}</p></div>
            <span className={`rounded-full border px-3 py-1 text-xs font-medium ${statusClass(selectedTask.status)}`}>{selectedTask.status.replace(/_/g, ' ')}</span>
          </div>
          {caseLoading ? <p className="mt-4 text-sm text-[var(--text-secondary)]">Loading cases…</p> : cases.length ? (
            <div className="mt-4 max-h-[28rem] overflow-auto rounded-lg border border-[var(--border-color)]">
              <table className="min-w-full text-left text-xs">
                <thead className="border-b border-[var(--border-color)]"><tr><th className="px-3 py-2">Case</th><th className="px-3 py-2">Prediction</th><th className="px-3 py-2">Ground Truth</th><th className="px-3 py-2">Comparison</th></tr></thead>
                <tbody>{cases.map((item) => { const match = item.metrics?.match; return <tr key={item.case_id} className="border-b border-[var(--border-color)] last:border-0"><td className="px-3 py-2">{item.case_id}</td><td className="px-3 py-2">{JSON.stringify(item.prediction)}</td><td className="px-3 py-2">{JSON.stringify(item.ground_truth)}</td><td className="px-3 py-2">{match == null ? item.status : match ? 'MATCH' : 'MISMATCH'}</td></tr>; })}</tbody>
              </table>
            </div>
          ) : <div className="mt-4 rounded-lg border border-dashed border-[var(--border-color)] p-4 text-sm text-[var(--text-secondary)]">No per-case result file is available for this task yet. The aggregate values shown above are preserved frozen results from the existing benchmark work, not newly generated numbers.</div>}
        </div>
      ) : null}

      <div className="rounded-xl border border-[var(--border-color)] p-5">
        <h2 className="text-base font-semibold">Evaluation pipeline</h2>
        <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">Real dataset input → agent output → task-specific ground truth → task-specific comparison → stored per-case result → aggregate metric. Classification tasks use accuracy/F1 where appropriate; extraction uses entity or field F1; retrieval/ranking uses Recall@K/NDCG@K; structured outputs use field-level accuracy. Tasks with no defensible ground truth remain NOT VALIDATABLE rather than receiving an invented score.</p>
        <p className="mt-3 text-xs text-[var(--text-secondary)]">Frozen results date: {data.as_of ?? '—'} · Source: {data.source ?? '—'}</p>
      </div>
    </section>
  );
}