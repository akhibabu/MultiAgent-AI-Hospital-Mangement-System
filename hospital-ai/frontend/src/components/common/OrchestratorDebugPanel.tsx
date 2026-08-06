/**
 * Shared "Developer Mode" AI Orchestrator debug panel.
 *
 * Renders the `ai_debug: OrchestratorDebugInfo[]` list every AI Agent report
 * carries — one entry per orchestrator call made during that pipeline run.
 *
 * Beyond the per-call basics (prompt, model, timing, tokens, cache status) it
 * shows the *execution timeline*: which providers were attempted, why each
 * one was abandoned, and which finally answered. In normal operation the
 * timeline has a single entry; when it has more, it is the record of the
 * system routing around a provider outage without the agent noticing.
 */
import Badge, { type BadgeTone } from '@/components/common/Badge';
import type { OrchestratorDebugInfo, ProviderAttempt } from '@/types/aiOrchestrator';

const OUTCOME_TONE: Record<ProviderAttempt['outcome'], BadgeTone> = {
  success: 'green',
  failed: 'red',
  skipped: 'gray',
};

/** Machine reason -> something a developer reads at a glance. */
const REASON_LABEL: Record<string, string> = {
  quota_exceeded: 'daily quota exhausted',
  rate_limited: 'rate limited',
  invalid_api_key: 'invalid API key',
  model_not_found: 'model not available',
  timeout: 'timed out',
  network_failure: 'network failure',
  server_error: 'provider server error',
  invalid_response: 'empty/invalid response',
  provider_offline: 'provider offline',
  malformed_request: 'malformed request',
  not_configured: 'no API key configured',
  no_model_configured: 'no model configured for this agent',
  adapter_unavailable: 'provider adapter unavailable',
};

function reasonLabel(reason: string) {
  if (!reason) return '';
  return REASON_LABEL[reason] ?? reason.replace(/_/g, ' ');
}

function ExecutionTimeline({ attempts }: { attempts: ProviderAttempt[] }) {
  return (
    <div className="mt-2">
      <p className="text-[var(--text-secondary)]">Execution timeline</p>
      <ol className="mt-1 space-y-1">
        {attempts.map((attempt, i) => (
          <li
            key={`${attempt.provider}-${i}`}
            className="flex flex-wrap items-center gap-2 rounded border border-[var(--border-color)] px-2 py-1"
          >
            <span className="text-[var(--text-secondary)]">{i + 1}.</span>
            <span className="font-medium text-[var(--text-primary)]">
              {attempt.provider}
            </span>
            <Badge tone={OUTCOME_TONE[attempt.outcome] ?? 'gray'}>{attempt.outcome}</Badge>
            {attempt.model ? (
              <span className="text-[var(--text-secondary)]">{attempt.model}</span>
            ) : null}
            {attempt.duration_ms ? (
              <span className="text-[var(--text-secondary)]">{attempt.duration_ms} ms</span>
            ) : null}
            {attempt.retries > 0 ? (
              <span className="text-[var(--text-secondary)]">
                {attempt.retries} retr{attempt.retries === 1 ? 'y' : 'ies'}
              </span>
            ) : null}
            {attempt.reason ? (
              <span className="text-amber-700 dark:text-amber-300">
                {reasonLabel(attempt.reason)}
              </span>
            ) : null}
          </li>
        ))}
      </ol>
    </div>
  );
}

export default function OrchestratorDebugPanel({
  entries,
}: {
  entries: OrchestratorDebugInfo[] | undefined;
}) {
  if (!entries || !entries.length) {
    return (
      <p className="text-xs text-[var(--text-secondary)]">
        No AI Orchestrator calls recorded for this run yet.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
        AI Orchestrator calls ({entries.length})
      </p>
      {entries.map((entry, i) => {
        const compression = entry.context_compression ?? {};
        const attempts = entry.attempts ?? [];
        return (
          <details
            key={`${entry.agent}-${entry.task}-${i}`}
            className="rounded-lg border border-[var(--border-color)] px-3 py-2 text-xs"
          >
            <summary className="flex cursor-pointer flex-wrap items-center justify-between gap-2">
              <span className="font-medium text-[var(--text-primary)]">
                {entry.agent} · {entry.task}
              </span>
              <span className="flex flex-wrap items-center gap-1.5">
                <Badge tone="blue">{entry.model}</Badge>
                {entry.fallback_used ? (
                  <Badge tone="amber">failover → {entry.provider}</Badge>
                ) : null}
                {entry.cache_hit ? <Badge tone="green">cache hit</Badge> : null}
                {entry.retry_count > 0 ? (
                  <Badge tone="amber">
                    {entry.retry_count} retr{entry.retry_count === 1 ? 'y' : 'ies'}
                  </Badge>
                ) : null}
                <Badge tone={entry.status === 'success' ? 'green' : 'red'}>
                  {entry.status}
                </Badge>
              </span>
            </summary>

            <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
              <p>
                <span className="text-[var(--text-secondary)]">Provider used: </span>
                {entry.provider}
              </p>
              <p>
                <span className="text-[var(--text-secondary)]">Primary provider: </span>
                {entry.primary_provider || entry.provider}
              </p>
              {entry.fallback_used ? (
                <p className="sm:col-span-2 text-amber-700 dark:text-amber-300">
                  <span className="text-[var(--text-secondary)]">Reason for switch: </span>
                  {reasonLabel(entry.fallback_reason)}
                </p>
              ) : null}
              <p>
                <span className="text-[var(--text-secondary)]">Prompt version: </span>
                {entry.prompt_version}
              </p>
              <p>
                <span className="text-[var(--text-secondary)]">Processing time: </span>
                {entry.processing_time_ms} ms
              </p>
              {entry.queue_wait_ms > 0 ? (
                <p>
                  <span className="text-[var(--text-secondary)]">Queue wait: </span>
                  {entry.queue_wait_ms} ms
                </p>
              ) : null}
              <p>
                <span className="text-[var(--text-secondary)]">
                  Tokens (prompt/completion):{' '}
                </span>
                {entry.prompt_tokens} / {entry.completion_tokens}
              </p>
              <p>
                <span className="text-[var(--text-secondary)]">Cost estimate: </span>
                {entry.estimated_cost_usd > 0
                  ? `~$${entry.estimated_cost_usd.toFixed(6)}`
                  : entry.cache_hit
                    ? '$0 (cache hit)'
                    : '—'}
              </p>
              {compression.estimated_tokens_saved ? (
                <p className="sm:col-span-2">
                  <span className="text-[var(--text-secondary)]">
                    Context compression:{' '}
                  </span>
                  {compression.original_chars?.toLocaleString()} →{' '}
                  {compression.compressed_chars?.toLocaleString()} chars (~
                  {compression.estimated_tokens_saved.toLocaleString()} tokens saved)
                  {compression.budget_enforced ? (
                    <span className="text-amber-700 dark:text-amber-300">
                      {' '}
                      — trimmed to fit a{' '}
                      {compression.budget_chars?.toLocaleString()}-char provider budget
                    </span>
                  ) : null}
                </p>
              ) : null}
            </div>

            {attempts.length ? <ExecutionTimeline attempts={attempts} /> : null}

            {entry.error ? (
              <p className="mt-2 text-red-600 dark:text-red-400">{entry.error}</p>
            ) : null}
            {entry.raw_response ? (
              <pre className="mt-2 max-h-48 overflow-auto rounded bg-black/5 p-2 leading-relaxed dark:bg-white/5">
                {entry.raw_response}
              </pre>
            ) : null}
          </details>
        );
      })}
    </div>
  );
}
