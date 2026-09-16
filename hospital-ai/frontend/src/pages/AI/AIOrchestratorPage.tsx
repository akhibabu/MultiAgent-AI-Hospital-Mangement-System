/**
 * AI Infrastructure dashboard.
 *
 * Every AI Agent (Intake, Diagnosis, Research, Prescription, Medical Report)
 * delegates model selection, prompt loading, context assembly, memory,
 * caching, retries, provider selection, and automatic failover to the AI
 * Orchestrator. This page is the operator's view of that machinery.
 *
 * The header answers "is the AI working?" at fleet level rather than for any
 * single provider — with automatic failover, one provider being out of quota
 * is a routine event, not an outage.
 */
import { Link } from 'react-router-dom';
import AIRequestQueuePanel from '@/components/ai/AIRequestQueuePanel';
import ProviderFleetPanel from '@/components/ai/ProviderFleetPanel';
import Badge, { type BadgeTone } from '@/components/common/Badge';
import Card from '@/components/common/Card';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import SimpleChart from '@/components/dashboard/SimpleChart';
import {
  useAICacheStats,
  useAIHealth,
  useAIRequestQueue,
  useOrchestratorLogs,
  useOrchestratorStats,
  useOrchestratorStatus,
  useProviderFleet,
} from '@/hooks/useAIOrchestrator';

function formatWhen(iso?: string | null) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return `${d.toLocaleDateString()} · ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  } catch {
    return iso;
  }
}

const FLEET_TONE: Record<string, BadgeTone> = {
  healthy: 'green',
  degraded: 'amber',
  unavailable: 'red',
  unknown: 'gray',
};

function statusTone(status: string): BadgeTone {
  return status === 'success' ? 'green' : 'red';
}

export default function AIOrchestratorPage() {
  const statusQuery = useOrchestratorStatus();
  const healthQuery = useAIHealth();
  const fleetQuery = useProviderFleet();
  const queueQuery = useAIRequestQueue();
  const cacheQuery = useAICacheStats();
  const statsQuery = useOrchestratorStats();
  const logsQuery = useOrchestratorLogs(30);

  const status = statusQuery.data;
  const health = healthQuery.data;
  const stats = statsQuery.data;
  const logs = logsQuery.data?.logs ?? [];

  const latencyChartData = (stats?.by_agent ?? []).map((a) => ({
    label: a.agent,
    value: Math.round(a.avg_duration_ms),
  }));

  const providerChartData = (fleetQuery.data?.providers ?? [])
    .filter((p) => p.health.total_requests > 0)
    .map((p) => ({ label: p.name, value: p.health.total_requests }));

  const failovers = logs.filter((log) => log.fallback_used).length;

  return (
    <ErrorBoundary title="AI Orchestrator error">
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary-600">
                AI Infrastructure
              </p>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[var(--text-primary)]">
                AI Orchestrator
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">
                The single entry point for every AI request in the system. Handles
                model routing, prompt loading, patient context assembly and
                compression, conversation memory, response caching, request queueing,
                retries, and automatic failover across multiple AI providers. No agent
                talks to a provider directly, or knows which one answered.
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
              <p className="text-xs text-[var(--text-secondary)]">Serving provider</p>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <p className="text-sm font-semibold uppercase text-[var(--text-primary)]">
                  {status?.provider ?? '—'}
                </p>
                {health ? (
                  <Badge tone={FLEET_TONE[health.status] ?? 'gray'}>{health.status}</Badge>
                ) : null}
              </div>
              {health ? (
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  {health.healthy_provider_count} of {health.configured_provider_count}{' '}
                  configured provider(s) healthy
                </p>
              ) : null}
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Requests today</p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                {stats?.requests_today ?? '—'}
              </p>
              <p className="mt-1 text-xs text-[var(--text-secondary)]">
                {queueQuery.data
                  ? `${queueQuery.data.active} active · ${queueQuery.data.queued} queued`
                  : '\u00a0'}
              </p>
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Avg response time</p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                {stats ? `${Math.round(stats.avg_duration_ms)} ms` : '—'}
              </p>
              <p className="mt-1 text-xs text-[var(--text-secondary)]">
                {stats ? `${Math.round(stats.retry_rate * 100)}% retried` : '\u00a0'}
              </p>
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Cache hit rate</p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                {cacheQuery.data
                  ? `${Math.round(cacheQuery.data.hit_rate * 100)}%`
                  : stats
                    ? `${Math.round(stats.cache_hit_rate * 100)}%`
                    : '—'}
              </p>
              <p className="mt-1 text-xs text-[var(--text-secondary)]">
                {failovers > 0
                  ? `${failovers} failover(s) in recent activity`
                  : 'No recent failovers'}
              </p>
            </Card>
          </div>
        </header>

        {statusQuery.isError ? (
          <Card>
            <p className="text-sm text-red-600">
              Could not reach the AI Orchestrator status endpoint. The backend may be
              offline.
            </p>
          </Card>
        ) : null}

        {health?.status === 'unavailable' ? (
          <Card>
            <p className="text-sm text-red-600 dark:text-red-400">
              No AI provider is configured. Set at least one provider API key in{' '}
              <code>backend/.env</code> — Groq, Gemini, OpenRouter, and HuggingFace all
              have free tiers.
            </p>
          </Card>
        ) : null}

        {/* Provider fleet, failover chain, and provider history */}
        <ProviderFleetPanel fleet={fleetQuery.data} isLoading={fleetQuery.isLoading} />

        {/* Live queue + cache controls */}
        <AIRequestQueuePanel queue={queueQuery.data} cache={cacheQuery.data} />

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Agent routing / model status */}
          <Card>
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">
              Agent routing &amp; model status
            </h2>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              Each agent is routed to a model on the current primary provider. If
              failover occurs, the fallback provider serves the same agent with its
              own configured model.
            </p>
            <div className="mt-4 space-y-2">
              {status?.model_health?.length ? (
                status.model_health.map((m) => (
                  <div
                    key={m.agent}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[var(--border-color)] px-3 py-2.5"
                  >
                    <div>
                      <p className="text-sm font-medium capitalize text-[var(--text-primary)]">
                        {m.agent.replace('_', ' ')}
                      </p>
                      <p className="text-xs text-[var(--text-secondary)]">
                        {m.provider} · {m.model}
                      </p>
                      {m.error ? (
                        <p className="mt-0.5 text-xs text-red-600">{m.error}</p>
                      ) : null}
                    </div>
                    <Badge tone={m.available ? 'green' : 'red'}>
                      {m.available ? 'Available' : 'Unavailable'}
                    </Badge>
                  </div>
                ))
              ) : (
                <p className="text-sm text-[var(--text-secondary)]">
                  {statusQuery.isLoading
                    ? 'Checking model health…'
                    : 'No model routing configured.'}
                </p>
              )}
            </div>
            {status ? (
              <p className="mt-4 text-xs text-[var(--text-secondary)]">
                Endpoint: <code>{status.provider_base_url || '—'}</code> · Failover
                chain: {status.failover_chain.join(' → ') || 'none'}
              </p>
            ) : null}
          </Card>

          {/* Runtime configuration */}
          <Card>
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">
              Runtime configuration
            </h2>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <p className="text-[var(--text-secondary)]">Routing strategy</p>
              <p className="text-right font-medium text-[var(--text-primary)]">
                {status?.load_balancer_strategy ?? '—'}
              </p>
              <p className="text-[var(--text-secondary)]">Automatic failover</p>
              <p className="text-right font-medium text-[var(--text-primary)]">
                {status ? (status.failover_enabled ? 'Enabled' : 'Disabled') : '—'}
              </p>
              <p className="text-[var(--text-secondary)]">Max concurrent requests</p>
              <p className="text-right font-medium text-[var(--text-primary)]">
                {queueQuery.data?.max_concurrent ?? '—'}
              </p>
              <p className="text-[var(--text-secondary)]">Cache TTL (base)</p>
              <p className="text-right font-medium text-[var(--text-primary)]">
                {status ? `${status.cache_ttl_seconds}s` : '—'}
              </p>
              <p className="text-[var(--text-secondary)]">Max retries</p>
              <p className="text-right font-medium text-[var(--text-primary)]">
                {status?.max_retries ?? '—'}
              </p>
              <p className="text-[var(--text-secondary)]">Temperature</p>
              <p className="text-right font-medium text-[var(--text-primary)]">
                {status?.temperature ?? '—'}
              </p>
              <p className="text-[var(--text-secondary)]">Max tokens</p>
              <p className="text-right font-medium text-[var(--text-primary)]">
                {status?.max_tokens ?? '—'}
              </p>
            </div>
            <div className="mt-4">
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                Model map (primary provider)
              </p>
              <div className="mt-2 space-y-1">
                {Object.entries(status?.models ?? {}).map(([agent, model]) => (
                  <div key={agent} className="flex justify-between text-sm">
                    <span className="capitalize text-[var(--text-secondary)]">
                      {agent.replace('_', ' ')}
                    </span>
                    <span className="font-medium text-[var(--text-primary)]">{model}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>

        {/* Usage metrics */}
        <div className="grid gap-6 lg:grid-cols-2">
          <SimpleChart title="Avg latency by agent (ms)" data={latencyChartData} type="bar" />
          {providerChartData.length ? (
            <SimpleChart
              title="Requests served by provider"
              data={providerChartData}
              type="bar"
            />
          ) : (
            <Card>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                Usage by agent
              </h2>
              <div className="mt-4 space-y-2">
                {stats?.by_agent?.length ? (
                  stats.by_agent.map((a) => (
                    <div
                      key={a.agent}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[var(--border-color)] px-3 py-2 text-sm"
                    >
                      <span className="font-medium capitalize text-[var(--text-primary)]">
                        {a.agent.replace('_', ' ')}
                      </span>
                      <span className="text-[var(--text-secondary)]">
                        {a.requests} req · {a.cache_hits} cached · {a.errors} err ·{' '}
                        {Math.round(a.avg_duration_ms)} ms
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-[var(--text-secondary)]">
                    No usage recorded yet.
                  </p>
                )}
              </div>
            </Card>
          )}
        </div>

        {/* Recent activity */}
        <Card>
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">Recent activity</h2>
          <div className="mt-4 overflow-x-auto">
            {logs.length ? (
              <table className="w-full min-w-[820px] text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border-color)] text-xs uppercase tracking-wide text-[var(--text-secondary)]">
                    <th className="py-2 pr-4">When</th>
                    <th className="py-2 pr-4">Agent</th>
                    <th className="py-2 pr-4">Task</th>
                    <th className="py-2 pr-4">Provider</th>
                    <th className="py-2 pr-4">Model</th>
                    <th className="py-2 pr-4">Duration</th>
                    <th className="py-2 pr-4">Tokens</th>
                    <th className="py-2 pr-4">Cache</th>
                    <th className="py-2 pr-4">Retries</th>
                    <th className="py-2 pr-4">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log, i) => (
                    <tr
                      key={log.id ?? `${log.agent}-${log.task}-${i}`}
                      className="border-b border-[var(--border-color)] last:border-0"
                    >
                      <td className="py-2 pr-4 text-xs text-[var(--text-secondary)]">
                        {formatWhen(log.created_at)}
                      </td>
                      <td className="py-2 pr-4 capitalize">{log.agent.replace('_', ' ')}</td>
                      <td className="py-2 pr-4">{log.task}</td>
                      <td className="py-2 pr-4 text-xs">
                        {log.provider}
                        {log.fallback_used ? (
                          <span className="ml-1.5">
                            <Badge tone="amber">
                              failover{log.fallback_reason ? `: ${log.fallback_reason}` : ''}
                            </Badge>
                          </span>
                        ) : null}
                      </td>
                      <td className="py-2 pr-4 text-xs">{log.model}</td>
                      <td className="py-2 pr-4">{log.duration_ms} ms</td>
                      <td className="py-2 pr-4 text-xs text-[var(--text-secondary)]">
                        {log.total_tokens || '—'}
                      </td>
                      <td className="py-2 pr-4">
                        {log.cache_hit ? (
                          <Badge tone="green">hit</Badge>
                        ) : (
                          <Badge tone="gray">miss</Badge>
                        )}
                      </td>
                      <td className="py-2 pr-4">{log.retry_count}</td>
                      <td className="py-2 pr-4">
                        <Badge tone={statusTone(log.status)}>{log.status}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-sm text-[var(--text-secondary)]">
                {logsQuery.isLoading
                  ? 'Loading recent activity…'
                  : 'No AI interactions logged yet.'}
              </p>
            )}
          </div>
        </Card>
      </div>
    </ErrorBoundary>
  );
}
