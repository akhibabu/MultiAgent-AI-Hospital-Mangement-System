/** AI Orchestrator types — single entry point for every AI/LLM request in the system. */

export interface ModelHealth {
  agent: string;
  provider: string;
  model: string;
  available: boolean;
  error?: string | null;
}

export interface OrchestratorStatus {
  /** Provider currently first in the failover chain. */
  provider: string;
  /** Base URL/endpoint of the active provider. */
  provider_base_url: string;
  available_providers: string[];
  /** Ordered failover chain: [primary, first fallback, ...]. */
  failover_chain: string[];
  load_balancer_strategy: string;
  failover_enabled: boolean;
  models: Record<string, string>;
  model_health: ModelHealth[];
  cache_ttl_seconds: number;
  max_retries: number;
  temperature: number;
  max_tokens: number;
}

/* -------------------------------------------------------------------------
 * Provider fleet
 * ---------------------------------------------------------------------- */

export type ProviderStatus = 'healthy' | 'warning' | 'offline' | 'not_configured';

export interface ProviderCapabilities {
  streaming: boolean;
  vision: boolean;
  long_context: boolean;
}

export interface ProviderPricing {
  input_per_1m: number;
  output_per_1m: number;
}

/**
 * How much this provider accepts in one call.
 *
 * `max_request_tokens` bounds `prompt + reserved completion`, not the prompt
 * alone — which is why a large MAX_TOKENS quietly shrinks the usable context.
 * `0` means no declared limit.
 */
export interface ProviderLimits {
  max_request_tokens: number;
  min_completion_tokens: number;
}

/** Live reliability state for one provider, from the health monitor. */
export interface ProviderHealth {
  provider: string;
  status: ProviderStatus;
  total_requests: number;
  total_successes: number;
  total_failures: number;
  consecutive_failures: number;
  success_rate: number;
  failure_rate: number;
  avg_latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  quota_exhausted: boolean;
  cooldown_remaining_seconds: number;
  times_skipped: number;
  last_success_at?: number | null;
  last_failure_at?: number | null;
  last_error?: string | null;
  last_error_reason?: string | null;
}

/**
 * One provider's config + live health. API keys are never sent to the
 * frontend — only `has_api_key`, so the UI can tell you which credential is
 * missing without the secret ever leaving the backend.
 */
export interface ProviderFleetEntry {
  name: string;
  enabled: boolean;
  priority: number;
  configured: boolean;
  has_api_key: boolean;
  requires_api_key: boolean;
  base_url: string;
  console_url: string;
  timeout_seconds: number;
  models: Record<string, string>;
  capabilities: ProviderCapabilities;
  pricing: ProviderPricing;
  limits: ProviderLimits;
  health: ProviderHealth;
  in_failover_chain: boolean;
  failover_position?: number | null;
}

export interface ProviderEvent {
  provider: string;
  event: 'offline' | 'recovered' | 'failover' | 'quota_exhausted';
  reason: string;
  detail: string;
  at: number;
}

export interface ProviderFleet {
  strategy: string;
  failover_enabled: boolean;
  max_providers_per_request: number;
  config_source: string;
  config_error?: string | null;
  providers: ProviderFleetEntry[];
  events: ProviderEvent[];
}

/* -------------------------------------------------------------------------
 * Request queue
 * ---------------------------------------------------------------------- */

export interface QueuedRequest {
  id: string;
  agent: string;
  task: string;
  priority: string;
  patient_id: string;
  state: string;
  stage: string;
  percent: number;
  wait_ms: number;
  running_ms: number;
  enqueued_at: number;
}

export interface QueueStatus {
  max_concurrent: number;
  active: number;
  queued: number;
  completed: number;
  cancelled: number;
  timed_out: number;
  failed: number;
  active_requests: QueuedRequest[];
  queued_requests: QueuedRequest[];
}

/* -------------------------------------------------------------------------
 * Cache
 * ---------------------------------------------------------------------- */

export interface CacheStats {
  entries: number;
  ttl_seconds: number;
  max_entries: number;
  hits: number;
  misses: number;
  hit_rate: number;
  evictions: number;
  invalidations: number;
  entries_by_agent: Record<string, number>;
  category_ttl_seconds: Record<string, number>;
}

export interface CacheInvalidation {
  removed: number;
  scope: string;
}

export interface AgentUsage {
  agent: string;
  requests: number;
  cache_hits: number;
  errors: number;
  avg_duration_ms: number;
}

export interface OrchestratorStats {
  requests_total: number;
  requests_today: number;
  avg_duration_ms: number;
  cache_hit_rate: number;
  retry_rate: number;
  error_rate: number;
  by_agent: AgentUsage[];
}

export interface InteractionLog {
  id?: string | null;
  patient_id?: string | null;
  agent: string;
  task: string;
  provider: string;
  model: string;
  status: string;
  duration_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cache_hit: boolean;
  retry_count: number;
  error_message?: string | null;
  /** Populated once migration 018 is applied. */
  primary_provider?: string | null;
  fallback_used: boolean;
  fallback_reason?: string | null;
  estimated_cost_usd: number;
  attempts: ProviderAttempt[];
  created_at?: string | null;
}

/** One provider's turn at a request — a Developer Mode timeline row. */
export interface ProviderAttempt {
  provider: string;
  model: string;
  outcome: 'success' | 'failed' | 'skipped';
  duration_ms: number;
  retries: number;
  reason: string;
  error: string;
}

export interface OrchestratorLogs {
  logs: InteractionLog[];
}

/** Per-call developer-mode debug info attached to every agent report (`ai_debug`). */
export interface OrchestratorDebugInfo {
  agent: string;
  task: string;
  provider: string;
  model: string;
  prompt_name: string;
  prompt_version: string;
  processing_time_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  retry_count: number;
  cache_hit: boolean;
  raw_response: string;
  status: string;
  error?: string | null;
  /** Best-effort USD estimate for this call (0 on cache hits / unknown pricing). */
  estimated_cost_usd: number;
  /** Provider the load balancer chose first for this request. */
  primary_provider: string;
  /** True when a fallback provider answered instead of the primary. */
  fallback_used: boolean;
  /** Why the primary was abandoned (quota_exceeded, rate_limited, …). */
  fallback_reason: string;
  /** Ordered execution timeline, one entry per provider attempted. */
  attempts: ProviderAttempt[];
  /** Before/after sizes from the context compressor. */
  context_compression: ContextCompressionInfo;
  /** How long this request waited for a queue slot. */
  queue_wait_ms: number;
  created_at: string;
}

export interface ContextCompressionInfo {
  original_chars?: number;
  compressed_chars?: number;
  saved_chars?: number;
  ratio?: number;
  estimated_tokens_saved?: number;
  /** Character ceiling applied, derived from the roomiest usable provider. */
  budget_chars?: number;
  /** True when context had to be trimmed further to fit that ceiling. */
  budget_enforced?: boolean;
}

/** One provider line in the `/ai/health` fleet summary. */
export interface AIProviderHealthSummary {
  provider: string;
  status: ProviderStatus | 'unknown';
  configured: boolean;
  in_failover_chain: boolean;
  failover_position?: number | null;
  current_model: string;
  avg_latency_ms: number;
  success_rate: number;
  quota_exhausted: boolean;
  last_error_reason?: string | null;
}

/**
 * `GET /ai/health` — AI infrastructure health.
 *
 * `status` describes the whole fleet, not one provider: the system is
 * `healthy` while any provider can serve a request, `degraded` when all
 * configured providers are cooling down, and `unavailable` only when no
 * provider is configured at all.
 */
export interface AIHealth {
  provider: string;
  status: 'healthy' | 'degraded' | 'unavailable' | 'unknown';
  connected: boolean;
  provider_base_url: string;
  available_models: string[];
  current_models: Record<string, string>;
  avg_latency_ms: number;
  error?: string | null;
  checked_at: string;
  failover_enabled: boolean;
  failover_chain: string[];
  providers: AIProviderHealthSummary[];
  healthy_provider_count: number;
  configured_provider_count: number;
}
