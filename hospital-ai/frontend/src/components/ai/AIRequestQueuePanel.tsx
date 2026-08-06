/**
 * Request queue + cache panel.
 *
 * The queue bounds how many AI requests hit providers simultaneously, so this
 * is where an operator sees whether work is actually moving or piling up.
 * Each running request reports its pipeline stage, and can be cancelled if it
 * is stuck behind a slow provider.
 *
 * Cache controls sit alongside it because they answer the neighbouring
 * question: a cached answer costs no tokens and no queue slot, so the hit
 * rate is the cheapest lever on both cost and latency. Per-patient
 * invalidation is the one an operator reaches for after new labs land.
 */
import Badge, { type BadgeTone } from '@/components/common/Badge';
import Card from '@/components/common/Card';
import { useCancelAIRequest, useInvalidateAICache } from '@/hooks/useAIOrchestrator';
import type { CacheStats, QueueStatus, QueuedRequest } from '@/types/aiOrchestrator';

const PRIORITY_TONE: Record<string, BadgeTone> = {
  critical: 'red',
  high: 'amber',
  normal: 'blue',
  low: 'gray',
};

function RequestRow({ request, cancellable }: { request: QueuedRequest; cancellable: boolean }) {
  const cancel = useCancelAIRequest();

  return (
    <div className="rounded-lg border border-[var(--border-color)] px-3 py-2 text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="flex items-center gap-2">
          <Badge tone={PRIORITY_TONE[request.priority] ?? 'gray'}>{request.priority}</Badge>
          <span className="font-medium capitalize text-[var(--text-primary)]">
            {request.agent.replace(/_/g, ' ')}
          </span>
          <span className="text-[var(--text-secondary)]">{request.task}</span>
        </span>
        <span className="flex items-center gap-2 text-[var(--text-secondary)]">
          {request.state === 'running' ? (
            <span>{Math.round(request.running_ms / 1000)}s</span>
          ) : (
            <span>waiting {Math.round(request.wait_ms / 1000)}s</span>
          )}
          {cancellable ? (
            <button
              type="button"
              onClick={() => cancel.mutate(request.id)}
              disabled={cancel.isPending}
              className="rounded border border-[var(--border-color)] px-2 py-0.5 transition hover:border-red-500/40 disabled:opacity-50"
            >
              Cancel
            </button>
          ) : null}
        </span>
      </div>
      {request.stage ? (
        <div className="mt-1.5">
          <div className="flex items-center justify-between text-[var(--text-secondary)]">
            <span>{request.stage}</span>
            <span>{Math.round(request.percent * 100)}%</span>
          </div>
          <div className="mt-1 h-1 overflow-hidden rounded-full bg-black/5 dark:bg-white/10">
            <div
              className="h-full rounded-full bg-primary-600 transition-all"
              style={{ width: `${Math.round(request.percent * 100)}%` }}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function AIRequestQueuePanel({
  queue,
  cache,
}: {
  queue: QueueStatus | undefined;
  cache: CacheStats | undefined;
}) {
  const invalidate = useInvalidateAICache();

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">
          Active AI requests
        </h2>
        <p className="mt-1 text-xs text-[var(--text-secondary)]">
          {queue
            ? `${queue.active} running / ${queue.max_concurrent} concurrent slots · ${queue.queued} waiting`
            : 'Loading queue…'}
        </p>

        <div className="mt-4 space-y-1.5">
          {queue?.active_requests.length ? (
            queue.active_requests.map((request) => (
              <RequestRow key={request.id} request={request} cancellable />
            ))
          ) : (
            <p className="text-sm text-[var(--text-secondary)]">
              No AI requests running right now.
            </p>
          )}
          {queue?.queued_requests.map((request) => (
            <RequestRow key={request.id} request={request} cancellable />
          ))}
        </div>

        {queue ? (
          <div className="mt-4 grid grid-cols-4 gap-2 border-t border-[var(--border-color)] pt-3 text-center text-xs">
            <div>
              <p className="text-[var(--text-secondary)]">Completed</p>
              <p className="mt-0.5 font-semibold text-[var(--text-primary)]">
                {queue.completed}
              </p>
            </div>
            <div>
              <p className="text-[var(--text-secondary)]">Failed</p>
              <p className="mt-0.5 font-semibold text-[var(--text-primary)]">
                {queue.failed}
              </p>
            </div>
            <div>
              <p className="text-[var(--text-secondary)]">Cancelled</p>
              <p className="mt-0.5 font-semibold text-[var(--text-primary)]">
                {queue.cancelled}
              </p>
            </div>
            <div>
              <p className="text-[var(--text-secondary)]">Timed out</p>
              <p className="mt-0.5 font-semibold text-[var(--text-primary)]">
                {queue.timed_out}
              </p>
            </div>
          </div>
        ) : null}
      </Card>

      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">
              Response cache
            </h2>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              Identical requests are served without touching a provider — no tokens,
              no quota, no latency.
            </p>
          </div>
          <button
            type="button"
            onClick={() => invalidate.mutate(undefined)}
            disabled={invalidate.isPending}
            className="rounded-lg border border-[var(--border-color)] px-2.5 py-1 text-xs text-[var(--text-secondary)] transition hover:border-primary-500/40 disabled:opacity-50"
          >
            {invalidate.isPending ? 'Clearing…' : 'Clear cache'}
          </button>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
          <p className="text-[var(--text-secondary)]">Hit rate</p>
          <p className="text-right font-medium text-[var(--text-primary)]">
            {cache ? `${Math.round(cache.hit_rate * 100)}%` : '—'}
          </p>
          <p className="text-[var(--text-secondary)]">Entries</p>
          <p className="text-right font-medium text-[var(--text-primary)]">
            {cache ? `${cache.entries} / ${cache.max_entries}` : '—'}
          </p>
          <p className="text-[var(--text-secondary)]">Hits / misses</p>
          <p className="text-right font-medium text-[var(--text-primary)]">
            {cache ? `${cache.hits} / ${cache.misses}` : '—'}
          </p>
          <p className="text-[var(--text-secondary)]">Invalidations</p>
          <p className="text-right font-medium text-[var(--text-primary)]">
            {cache?.invalidations ?? '—'}
          </p>
        </div>

        {cache && Object.keys(cache.category_ttl_seconds).length ? (
          <div className="mt-4">
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
              TTL by agent
            </p>
            <div className="mt-2 space-y-1">
              {Object.entries(cache.category_ttl_seconds).map(([agent, ttl]) => (
                <div key={agent} className="flex justify-between text-xs">
                  <span className="capitalize text-[var(--text-secondary)]">
                    {agent.replace(/_/g, ' ')}
                  </span>
                  <span className="text-[var(--text-primary)]">
                    {ttl}s
                    {cache.entries_by_agent[agent]
                      ? ` · ${cache.entries_by_agent[agent]} cached`
                      : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </Card>
    </div>
  );
}
