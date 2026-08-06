/**
 * Provider fleet panel — the operational heart of the AI Infrastructure page.
 *
 * Shows every declared AI provider in failover order with its live health,
 * so an operator can answer the two questions that actually matter during an
 * incident: "who is serving traffic right now?" and "what do I do about it?"
 *
 * The second question is why unconfigured providers are shown rather than
 * hidden — a fleet with one usable provider has no failover at all, and the
 * fastest fix is a free API key from the linked console. API keys themselves
 * never reach the browser; the backend reports only whether one is present.
 */
import Badge, { type BadgeTone } from '@/components/common/Badge';
import Card from '@/components/common/Card';
import { useReloadProviders, useResetProvider } from '@/hooks/useAIOrchestrator';
import type {
  ProviderEvent,
  ProviderFleet,
  ProviderFleetEntry,
  ProviderStatus,
} from '@/types/aiOrchestrator';

const STATUS_TONE: Record<ProviderStatus, BadgeTone> = {
  healthy: 'green',
  warning: 'amber',
  offline: 'red',
  not_configured: 'gray',
};

const EVENT_TONE: Record<ProviderEvent['event'], BadgeTone> = {
  recovered: 'green',
  failover: 'amber',
  offline: 'red',
  quota_exhausted: 'red',
};

/** Turn a machine reason into something a human can act on. */
const REASON_LABEL: Record<string, string> = {
  quota_exceeded: 'Daily quota exhausted',
  rate_limited: 'Rate limited',
  invalid_api_key: 'Invalid API key',
  model_not_found: 'Model not available',
  timeout: 'Timed out',
  network_failure: 'Network failure',
  server_error: 'Provider server error',
  invalid_response: 'Empty/invalid response',
  provider_offline: 'Provider offline',
  malformed_request: 'Malformed request',
  probe_succeeded: 'Recovered',
  not_configured: 'No API key',
};

function label(reason?: string | null) {
  if (!reason) return '';
  return REASON_LABEL[reason] ?? reason.replace(/_/g, ' ');
}

function cooldown(seconds: number) {
  if (seconds <= 0) return '';
  if (seconds < 60) return `${Math.ceil(seconds)}s`;
  return `${Math.ceil(seconds / 60)}m`;
}

function when(epochSeconds: number) {
  try {
    return new Date(epochSeconds * 1000).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return '';
  }
}

function ProviderRow({ entry }: { entry: ProviderFleetEntry }) {
  const resetProvider = useResetProvider();
  const { health } = entry;
  const status = entry.configured ? health.status : 'not_configured';
  const inCooldown = health.cooldown_remaining_seconds > 0;

  return (
    <div className="rounded-xl border border-[var(--border-color)] px-3 py-2.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {entry.failover_position ? (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary-600/15 text-[11px] font-semibold text-primary-700 dark:text-primary-300">
              {entry.failover_position}
            </span>
          ) : (
            <span className="flex h-5 w-5 items-center justify-center text-[11px] text-[var(--text-secondary)]">
              –
            </span>
          )}
          <div>
            <p className="text-sm font-medium capitalize text-[var(--text-primary)]">
              {entry.name.replace(/_/g, ' ')}
              {entry.failover_position === 1 ? (
                <span className="ml-2 text-xs font-normal text-[var(--text-secondary)]">
                  primary
                </span>
              ) : null}
            </p>
            <p className="text-xs text-[var(--text-secondary)]">
              {entry.models.default || Object.values(entry.models)[0] || 'no model'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {health.quota_exhausted ? <Badge tone="red">quota</Badge> : null}
          {inCooldown ? (
            <Badge tone="amber">
              retry in {cooldown(health.cooldown_remaining_seconds)}
            </Badge>
          ) : null}
          <Badge tone={STATUS_TONE[status as ProviderStatus] ?? 'gray'}>
            {status.replace(/_/g, ' ')}
          </Badge>
        </div>
      </div>

      {entry.configured ? (
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--text-secondary)]">
          <span>{health.total_requests} req</span>
          <span>{Math.round(health.success_rate * 100)}% success</span>
          <span>{Math.round(health.avg_latency_ms)} ms avg</span>
          {health.total_tokens > 0 ? (
            <span>{health.total_tokens.toLocaleString()} tokens</span>
          ) : null}
          {health.estimated_cost_usd > 0 ? (
            <span>~${health.estimated_cost_usd.toFixed(4)}</span>
          ) : null}
          {health.times_skipped > 0 ? <span>{health.times_skipped} skipped</span> : null}
          {entry.limits?.max_request_tokens ? (
            <span
              title="Max prompt + reserved completion tokens this provider accepts in one request"
            >
              {entry.limits.max_request_tokens.toLocaleString()} tok/req limit
            </span>
          ) : null}
        </div>
      ) : (
        <p className="mt-2 text-xs text-[var(--text-secondary)]">
          {entry.enabled ? 'No API key configured.' : 'Disabled in providers.yaml.'}{' '}
          {entry.console_url ? (
            <a
              href={entry.console_url}
              target="_blank"
              rel="noreferrer"
              className="underline"
            >
              Get a key
            </a>
          ) : null}
        </p>
      )}

      {health.last_error && status !== 'healthy' ? (
        <p className="mt-1.5 text-xs text-red-600 dark:text-red-400">
          {label(health.last_error_reason)}
          {health.last_error_reason ? ' — ' : ''}
          {health.last_error}
        </p>
      ) : null}

      {inCooldown ? (
        <button
          type="button"
          onClick={() => resetProvider.mutate(entry.name)}
          disabled={resetProvider.isPending}
          className="mt-2 rounded-lg border border-[var(--border-color)] px-2.5 py-1 text-xs text-[var(--text-secondary)] transition hover:border-primary-500/40 disabled:opacity-50"
        >
          {resetProvider.isPending ? 'Restoring…' : 'Retry now'}
        </button>
      ) : null}
    </div>
  );
}

export default function ProviderFleetPanel({
  fleet,
  isLoading,
}: {
  fleet: ProviderFleet | undefined;
  isLoading: boolean;
}) {
  const reload = useReloadProviders();
  const usable = fleet?.providers.filter((p) => p.in_failover_chain) ?? [];
  const noFailover = usable.length <= 1;

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">
              Provider fleet &amp; failover chain
            </h2>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              Providers are tried in the numbered order. If one hits its quota, rate
              limits, or goes down, the next takes over automatically — no AI Agent
              is aware it happened.
            </p>
          </div>
          <button
            type="button"
            onClick={() => reload.mutate()}
            disabled={reload.isPending}
            className="rounded-lg border border-[var(--border-color)] px-2.5 py-1 text-xs text-[var(--text-secondary)] transition hover:border-primary-500/40 disabled:opacity-50"
          >
            {reload.isPending ? 'Reloading…' : 'Reload providers.yaml'}
          </button>
        </div>

        {fleet?.config_error ? (
          <p className="mt-3 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2.5 text-xs text-red-700 dark:text-red-300">
            Could not read <code>providers.yaml</code>: {fleet.config_error}. Running on
            a single-provider fallback — automatic failover is disabled until this is
            fixed.
          </p>
        ) : null}

        {fleet && noFailover ? (
          <p className="mt-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2.5 text-xs text-amber-900 dark:text-amber-100">
            Only {usable.length} provider is configured, so there is nothing to fail
            over to. Add a second free API key (Gemini, OpenRouter, or HuggingFace) in{' '}
            <code>backend/.env</code> to make the system fault tolerant.
          </p>
        ) : null}

        <div className="mt-4 space-y-2">
          {fleet?.providers.length ? (
            fleet.providers.map((entry) => (
              <ProviderRow key={entry.name} entry={entry} />
            ))
          ) : (
            <p className="text-sm text-[var(--text-secondary)]">
              {isLoading ? 'Loading provider fleet…' : 'No providers declared.'}
            </p>
          )}
        </div>

        {fleet ? (
          <p className="mt-4 text-xs text-[var(--text-secondary)]">
            Strategy: <code>{fleet.strategy}</code> · Max providers per request:{' '}
            {fleet.max_providers_per_request} · Failover{' '}
            {fleet.failover_enabled ? 'enabled' : 'disabled'}
          </p>
        ) : null}
      </Card>

      <Card>
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">
          Provider history
        </h2>
        <p className="mt-1 text-xs text-[var(--text-secondary)]">
          Recent failovers, outages, and recoveries — the record of when and why
          traffic moved between providers.
        </p>
        <div className="mt-4 space-y-1.5">
          {fleet?.events.length ? (
            fleet.events.map((event, i) => (
              <div
                key={`${event.provider}-${event.at}-${i}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--border-color)] px-3 py-2 text-xs"
              >
                <span className="flex items-center gap-2">
                  <Badge tone={EVENT_TONE[event.event] ?? 'gray'}>
                    {event.event.replace(/_/g, ' ')}
                  </Badge>
                  <span className="font-medium capitalize text-[var(--text-primary)]">
                    {event.provider}
                  </span>
                  <span className="text-[var(--text-secondary)]">
                    {label(event.reason)} {event.detail}
                  </span>
                </span>
                <span className="text-[var(--text-secondary)]">{when(event.at)}</span>
              </div>
            ))
          ) : (
            <p className="text-sm text-[var(--text-secondary)]">
              No provider incidents recorded — every request has been served by its
              primary provider.
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}
