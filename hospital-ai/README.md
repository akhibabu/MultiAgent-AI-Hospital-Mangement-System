# Hospital AI — Multi-Agent Hospital Management System

Production-oriented **Clinical Decision Support** platform for hospital staff. Specialized AI agents run as sequential workflows (like a CI pipeline). They **assist clinicians** — they never replace physician judgment, never autonomously prescribe, and never claim certainty.

This is the **main README** for teammates. Everything you need to clone, configure keys, run migrations, and understand agents lives here.

---

## Table of contents

1. [Project status](#1-project-status)
2. [Architecture & frameworks](#2-architecture--frameworks)
3. [The AI Orchestrator](#3-the-ai-orchestrator)
   - [3.1 Provider failover](#31-provider-failover)
   - [3.2 Configuring the fleet — `providers.yaml`](#32-configuring-the-fleet--backendprovidersyaml)
   - [3.3 Adding a new provider](#33-adding-a-new-provider)
   - [3.4 Observability](#34-observability)
4. [Step-by-step setup](#4-step-by-step-setup)
5. [External APIs — what you NEED vs what we USED](#5-external-apis--what-you-need-vs-what-we-used)
6. [Environment variables (full list)](#6-environment-variables-full-list)
7. [Database migrations (every step)](#7-database-migrations-every-step)
8. [Running the app](#8-running-the-app)
9. [Our backend APIs (what this project exposes)](#9-our-backend-apis-what-this-project-exposes)
10. [AI agents explained](#10-ai-agents-explained)
11. [Frontend routes](#11-frontend-routes)
12. [Smoke tests](#12-smoke-tests)
13. [Clinical safety rules](#13-clinical-safety-rules)
14. [Further docs](#14-further-docs)

---

## 1. Project status

| Area | Status |
|------|--------|
| Auth (Supabase JWT) | Done |
| Patients / Doctors / Appointments / Records / Resources / Announcements | Done |
| **Intake Agent** | Done |
| **Diagnosis Agent** | Done |
| **Research Agent** | Done |
| **Prescription Agent** | Done |
| **Medical Report Agent** | Done |
| **AI Orchestrator** (centralized LLM routing/prompts/memory/cache/retries/logging) | Done |
| **AI Provider Orchestrator** (multi-provider fleet, automatic failover, health monitoring, load balancing) | Done |
| Scheduling / Emergency / Insurance / Resource Allocation / Digital Twin | Coming soon |

---

## 2. Architecture & frameworks

```text
┌─────────────────────────────────────────────────────────────┐
│  Frontend                                                   │
│  React 19 · Vite 6 · TypeScript · Tailwind 4                │
│  React Router 7 · TanStack Query 5 · Axios · Sonner         │
│  Supabase JS (session / auth persistence)                   │
└────────────────────────────┬────────────────────────────────┘
                             │ Authorization: Bearer <JWT>
┌────────────────────────────▼────────────────────────────────┐
│  Backend                                                    │
│  FastAPI · Uvicorn · Pydantic v2 · pydantic-settings        │
│  Routes → Services → Repositories → Supabase PostgREST      │
│                                                               │
│  Intake · Diagnosis · Research · Prescription · Med. Report │
│  agents each call ONE method:                                │
│      AIOrchestrator.run(agent=..., task=..., patient_id=...) │
│                          │                                    │
│                ┌─────────▼──────────┐                        │
│                │   AI Orchestrator   │  ← see section 3       │
│                │  (single LLM entry) │                        │
│                └─────────┬──────────┘                        │
│                          │                                    │
│                ┌─────────▼───────────┐                       │
│                │ Provider Orchestrator│ automatic failover    │
│                │  Router · LoadBalancer · HealthMonitor      │
│                └─────────┬───────────┘                       │
│                          │                                    │
│    Groq → Gemini → OpenRouter → HuggingFace  (failover chain)│
│    + OpenAI · Claude · Azure OpenAI · Ollama (configurable)  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  Supabase                                                   │
│  PostgreSQL · Auth · RLS · Storage (medical documents)      │
│  + ai_conversation_memory · ai_interaction_logs              │
│  + ai_provider_events                                        │
└─────────────────────────────────────────────────────────────┘
```

### Design patterns (every AI agent)

| Pattern | Why |
|---------|-----|
| **One agent = one workflow page** | Stages are internal steps, not separate routes |
| **Pipeline** | Runs stages in fixed order |
| **Strategy + Factory** | Every stage is a pluggable strategy; factories wire in the orchestrator-backed implementation by default |
| **Facade** | `AIOrchestrator` is the single facade every agent calls — no agent talks to an LLM provider directly |
| **Adapter** | Each `BaseAIProvider` adapts one vendor's API onto a single internal contract |
| **Chain of Responsibility** | Failover walks the provider chain until one succeeds |
| **Circuit Breaker** | `ProviderHealthMonitor` takes failing providers out of rotation for a cooldown |
| **Repository** | DB via Supabase REST with service role |
| **DI** | Services/pipelines/orchestrator subsystems are all constructor-injectable, for smoke tests and future swaps |

### Folder layout

```text
hospital-ai/
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   │   ├── orchestrator/       # AI Orchestrator — see section 3
│   │   │   │   ├── provider_orchestrator.py  # failover engine
│   │   │   │   ├── provider_router.py        # providers.yaml → BaseAIProvider
│   │   │   │   ├── provider_health_monitor.py# circuit breaker + reliability
│   │   │   │   ├── load_balancer.py          # priority/round-robin/latency/errors
│   │   │   │   ├── context_compressor.py     # token optimization
│   │   │   │   ├── request_queue.py          # concurrency/priority/cancel
│   │   │   │   ├── providers/      # groq, gemini, openrouter, huggingface,
│   │   │   │   │                   # openai, azure_openai, anthropic, ollama, stub
│   │   │   │   ├── prompts/        # markdown prompt templates, per agent/task
│   │   │   │   └── services/       # usage_stats_service (admin dashboard)
│   │   │   ├── intake/             # Agent pipelines — call the orchestrator,
│   │   │   ├── diagnosis/          # never an LLM provider directly
│   │   │   ├── research/
│   │   │   ├── prescription/
│   │   │   └── medical_report/
│   │   ├── api/                # Router aggregation
│   │   ├── auth/               # JWT dependencies
│   │   ├── config/             # Settings from .env
│   │   ├── repositories/       # Supabase REST access
│   │   ├── routes/             # HTTP endpoints
│   │   ├── schemas/            # Pydantic request/response
│   │   └── services/           # Business facades
│   ├── providers.yaml          # AI provider fleet (priority, models, limits)
│   ├── migrations/             # SQL — run in order in Supabase
│   └── scripts/                # Smoke tests + fleet diagnostics
├── frontend/
│   └── src/
│       ├── pages/AI/           # Agent UI pages + AIOrchestratorPage
│       ├── hooks/              # React Query hooks
│       ├── services/           # Axios clients
│       └── types/
└── docs/                       # Extra module guides
```

---

## 3. The AI Orchestrator

Every AI Agent (Intake's optional enrichment, Diagnosis, Research, Prescription, Medical Report) calls **exactly one method** instead of talking to an LLM provider directly:

```python
AIOrchestrator.run(
    agent="diagnosis",              # routes to a model via ModelRouter
    task="differential_diagnosis",  # loads prompts/diagnosis/differential_diagnosis.md
    patient_id=patient_id,          # ContextManager assembles patient context/KG/history
    response_model=SomeSchema,      # ResponseParser validates structured JSON output
)
```

An agent **never knows** which model or provider is used, where prompts live, or how retries, failover, and caching work. That is entirely the orchestrator's job:

| Subsystem | File | Responsibility |
|-----------|------|-----------------|
| `ModelRouter` | `orchestrator/router.py` | Maps (agent, provider) → model name, driven by `providers.yaml` |
| `PromptManager` | `orchestrator/prompt_manager.py` | Loads/caches/versions `.md` prompt templates, supports `{{variables}}` — provider-independent, no vendor-specific formatting |
| `ContextManager` | `orchestrator/context_manager.py` | Assembles patient context, KG, history, risk, entities, recent diagnosis/research |
| `ContextCompressor` | `orchestrator/context_compressor.py` | Token optimization — dedupes history, trims timelines, compresses the knowledge graph before every request |
| `ConversationManager` | `orchestrator/conversation_manager.py` | Per-patient AI memory, persisted in `ai_conversation_memory` |
| `RequestQueue` | `orchestrator/request_queue.py` | Bounded concurrency, priority admission, cancellation, timeouts, progress |
| `InMemoryTTLCache` | `orchestrator/cache_manager.py` | Provider-agnostic response cache with per-agent TTLs and manual invalidation |
| **`ProviderOrchestrator`** | `orchestrator/provider_orchestrator.py` | **Failover engine** — see [3.1](#31-provider-failover) |
| `ResponseParser` | `orchestrator/response_parser.py` | Extracts + validates strict JSON against the caller's Pydantic model |
| `AIInteractionLogger` | `orchestrator/logger.py` | Persists every call to `ai_interaction_logs` (tokens, duration, status, retries, cache hit, fallback reason, attempt timeline, cost) |
| `UsageStatsService` | `orchestrator/services/usage_stats_service.py` | Aggregates logs into dashboard stats for the AI Orchestrator page |

---

### 3.1 Provider failover

The system must never fail because one vendor runs out of quota. Below `AIOrchestrator` sits a **Provider Orchestrator** that treats providers as a *fleet* rather than a single configured backend:

```text
AI Agent → AI Orchestrator → ProviderOrchestrator
                                 ├── LoadBalancer          picks the candidate order
                                 ├── ProviderRouter        instantiates adapters from providers.yaml
                                 ├── ProviderHealthMonitor circuit breaker + reliability stats
                                 └── RetryHandler          exponential backoff, per candidate
                                       ↓
              Groq → Gemini → OpenRouter → HuggingFace
```

For each request the orchestrator walks the candidate list. A candidate is tried with retries; if it still fails, the next candidate is tried — **transparently, with no agent involvement**. Only when every candidate is exhausted does the caller see an error, and it is a clean HTTP 503 with a human-readable summary, never a raw vendor payload.

**Failure taxonomy** (`orchestrator/providers/errors.py`) decides what happens next. Every provider maps its HTTP errors into these types, so the policy is uniform across vendors:

| Failure | Example | Action |
|---------|---------|--------|
| Network failure, timeout, HTTP 500/502/503 | Provider having a bad minute | **Retry** with exponential backoff |
| Rate limit (HTTP 429, short `Retry-After`) | Per-minute request cap | **Retry** honoring `Retry-After` (capped at 60 s) |
| Quota exceeded (429 with long `Retry-After`, HTTP 402) | Daily/monthly token limit | **Failover** immediately + long cooldown |
| Invalid API key (401/403) | Missing/rotated key | **Failover** immediately |
| Model not found (404) | Model not on this account | **Failover** immediately |
| Request too large (HTTP 413, or 400 `context_length_exceeded`) | Prompt exceeds this provider's per-request budget | **Failover** to a roomier provider |
| Empty/invalid response | Provider returned no content | **Failover** immediately |
| Malformed request (400/422) | Our bug — every provider would reject it | **Fatal**, no retry, no failover |

Those last two rows are the subtle ones. Failing over on a genuinely malformed request would just burn every provider's quota reproducing the same bug. But "too large" only looks like a bad request — the prompt is fine, this particular provider just can't hold it, and Gemini's 1M-token window very much can. Classifying size as fatal would take the whole fleet down over one member's limit.

---

#### Token budgets (why `MAX_TOKENS` shrinks your prompt)

Providers meter **`prompt_tokens + max_tokens` against a single ceiling** — the completion reservation is charged whether or not the model uses it. On Groq's free tier that ceiling is about 5 800 tokens per request, so a default `MAX_TOKENS=4096` leaves only ~1 700 tokens for the prompt, and a long patient context returns HTTP 413 instead of being truncated.

Each provider declares its ceiling in `providers.yaml`:

```yaml
groq:
  limits:
    max_request_tokens: ${GROQ_MAX_REQUEST_TOKENS:-5800}
```

The orchestrator then does three things automatically, in this order:

1. **Sizes context compression to the fleet.** The `ContextCompressor` receives the prompt budget of the roomiest usable provider and trims to fit it. A Gemini-backed deployment keeps its full context; a Groq-only one trims rather than sending a doomed request.
2. **Shrinks the completion reservation.** `max_tokens` is reduced to whatever fits alongside the prompt, never below `min_completion_tokens` (700 by default) — a reply truncated mid-JSON is worse than a clean failover.
3. **Routes around providers that can't fit it.** If the prompt still doesn't fit, that provider is skipped *before* the request is sent and a roomier one gets it. Only if none can hold the prompt does the caller get an error, and it names the size problem specifically.

Set `max_request_tokens` to the tightest limit your account actually has. For free tiers that is usually tokens-per-minute, **not** the model's context window — Groq's models accept 128k context that a free key cannot pay for.

**Health monitoring.** `ProviderHealthMonitor` keeps a rolling window per provider — latency percentiles, success/failure counts, consecutive failures, last success, quota state. It exposes three states:

| State | Meaning |
|-------|---------|
| **Healthy** | In rotation |
| **Warning** | Rolling error rate above `AI_HEALTH_WARNING_ERROR_RATE` — still used, but de-prioritized |
| **Offline** | Consecutive failures hit `AI_HEALTH_FAILURE_THRESHOLD`, or quota exhausted — skipped until its cooldown expires (`AI_HEALTH_COOLDOWN_SECONDS`, or `AI_HEALTH_QUOTA_COOLDOWN_SECONDS` for quota) |

This is a circuit breaker: a provider that has run out of daily tokens is not re-probed on every request for the next 15 minutes. You can force an early retry from the dashboard ("Reset cooldown") or via `POST /ai/orchestrator/providers/{name}/reset`.

**Load balancing.** `AI_LOAD_BALANCER_STRATEGY` selects the ordering strategy; failover then walks the remaining candidates in that same order.

| Strategy | Behavior |
|----------|----------|
| `priority` *(default)* | Lowest `priority` in `providers.yaml` first — deterministic, matches the documented Groq → Gemini → OpenRouter → HuggingFace chain |
| `round_robin` | Spreads load across healthy providers to stretch several free tiers |
| `least_latency` | Fastest observed provider first |
| `least_errors` | Most reliable provider first |

Providers lacking a required capability (e.g. vision) or a model for the requesting agent are filtered out before ordering.

---

### 3.2 Configuring the fleet — `backend/providers.yaml`

The fleet is **declared, never hardcoded**. `backend/providers.yaml` is the only place providers, priorities, models, capabilities, and pricing live. It supports `${VAR}` and `${VAR:-fallback}` interpolation, so secrets stay in `.env` while the shape of the fleet stays reviewable in git:

```yaml
providers:
  groq:
    enabled: ${GROQ_ENABLED:-true}
    priority: 1
    api_key: ${GROQ_API_KEY}
    models:
      default: ${GROQ_MODEL:-llama-3.3-70b-versatile}
      diagnosis: ${DIAGNOSIS_MODEL:-llama-3.3-70b-versatile}
    capabilities: { streaming: true, vision: false, long_context: true }
    pricing: { input_per_1m: 0.59, output_per_1m: 0.79 }
```

A provider joins the chain only when it is `enabled: true` **and** its credential resolves to a non-empty value. A teammate with only a Groq key can therefore clone the repo and everything works — failover simply skips the providers they haven't configured.

| Provider | Priority | Key | Where to get one | Free tier |
|----------|----------|-----|------------------|-----------|
| **Groq** | 1 | `GROQ_API_KEY` | [console.groq.com/keys](https://console.groq.com/keys) | Yes — fastest inference |
| **Google Gemini** | 2 | `GEMINI_API_KEY` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Yes — large quota, 1M context |
| **OpenRouter** | 3 | `OPENROUTER_API_KEY` | [openrouter.ai/keys](https://openrouter.ai/keys) | Yes — `:free` model tier |
| **HuggingFace** | 4 | `HUGGINGFACE_API_KEY` | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) | Yes — monthly credits |
| OpenAI | 5 | `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | Paid — `OPENAI_ENABLED=true` |
| Anthropic Claude | 6 | `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/settings/keys) | Paid — `ANTHROPIC_ENABLED=true` |
| Azure OpenAI | 7 | `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` | [portal.azure.com](https://portal.azure.com) | Paid — `AZURE_OPENAI_ENABLED=true` |
| Ollama (local) | 8 | none | [ollama.com](https://ollama.com) | Free — `OLLAMA_ENABLED=true`, run `ollama serve` |
| Stub (offline dev) | 99 | none | — | Deterministic canned JSON; pin with `AI_PROVIDER=stub` |

**Setting up the recommended four** (all free, ~2 minutes each): create a key at each console above, then in `backend/.env`:

```dotenv
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
OPENROUTER_API_KEY=sk-or-v1-...
HUGGINGFACE_API_KEY=hf_...
```

Restart the backend and open `/ai/orchestrator` — the **Provider fleet** panel shows all four as healthy, with the active failover chain. Configuring even one is enough to run the system; each additional key is one more outage the system can absorb.

Verify what the backend actually resolved (keys are shown only as present/missing, never printed):

```bash
python scripts/check_provider_fleet.py
```

`AI_PROVIDER` is a **preference, not a lock**: it moves a provider to the front of the chain, but failover still protects you. The one exception is `AI_PROVIDER=stub`, which pins the offline fixture exclusively. Set `AI_FAILOVER_ENABLED=false` to force strict single-provider behavior.

---

### 3.3 Adding a new provider

Three steps, none of which touch an AI Agent:

1. **Implement the adapter** in `orchestrator/providers/<name>_provider.py`. If the vendor speaks the OpenAI Chat Completions protocol, subclass `OpenAICompatibleProvider` and declare only what differs (~15 lines — see `openrouter_provider.py`). Otherwise implement `BaseAIProvider` directly (see `gemini_provider.py`), mapping vendor errors onto the taxonomy in `errors.py`.
2. **Register a factory** — one line in `ProviderRouter._register_builtin_factories()`, or `ProviderRouter.register()` at runtime.
3. **Declare it in `providers.yaml`** with `enabled`, `priority`, `api_key: ${YOUR_KEY}`, models, capabilities, and pricing. Add the key to `.env.example`.

**Provider contract** (`orchestrator/interfaces/__init__.py`): `generate()`, `stream()`, `health_check()`, `is_available()`, `list_models()`, `estimate_tokens()`, `estimate_cost()`, `supports_streaming()`, `supports_vision()`, `supports_long_context()`, `validate_response()`. No AI Agent and no other orchestrator subsystem ever imports a concrete provider class — only `ProviderRouter` does.

---

### 3.4 Observability

**AI Infrastructure dashboard** (`/ai/orchestrator`) shows the live fleet: each provider's health state, priority, current model, latency, success/failure rate, quota status, request counts, and cooldown; the active failover chain and load-balancer strategy; the request queue (active/queued, cancellation); cache hit rate and invalidation controls; and a provider event history recording every outage, quota exhaustion, recovery, and failover.

**Developer Mode:** every agent report (`ai_debug: OrchestratorDebugInfo[]`) carries one entry per orchestrator call — provider used, primary provider, whether a fallback was used and **why**, the full per-provider **execution timeline** (outcome, model, duration, retries, reason), loaded prompt version, processing time, queue wait, prompt/completion tokens, cost estimate, context-compression savings, cache status, and raw response. Every AI Agent page renders this in a collapsible panel.

**Errors never leak.** Raw vendor payloads stay in the backend logs; the UI receives a summarized message ("All AI providers are currently unavailable…") plus the structured attempt timeline.

---

## 4. Step-by-step setup

### Prerequisites

- Node.js **20+** and npm  
- Python **3.11+**  
- Git  
- A Supabase project  
- Docker Desktop (optional)

### Step 1 — Clone

```bash
git clone <your-repo-url>
cd MultiAgent-AI-Hospital-Mangement-System/hospital-ai
```

### Step 2 — Create Supabase project & copy credentials

1. Go to [https://supabase.com](https://supabase.com) → **New project**
2. Open **Project Settings → API** and copy:
   - Project URL  
   - `anon` `public` key  
   - `service_role` `secret` key  
3. Open **JWT Secret** and copy it  
4. Full walkthrough: [`docs/supabase-setup.md`](./docs/supabase-setup.md)

### Step 3 — Backend env

```bash
cd backend
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Fill **at minimum** in `backend/.env`:

```env
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
```

The AI provider fleet is already declared in `backend/providers.yaml` — no keys are required to boot the app itself. Add one or more **free** provider keys (`GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `HUGGINGFACE_API_KEY`) for real AI Agent runs, or set `AI_PROVIDER=stub` for deterministic offline testing. See [section 3.2](#32-configuring-the-fleet--backendprovidersyaml) — each extra key is one more outage the system routes around automatically.

### Step 4 — Frontend env

```bash
cd ../frontend
cp .env.example .env
npm install
```

Fill **at minimum** in `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=Hospital AI
VITE_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

### Step 5 — Run SQL migrations

In Supabase → **SQL Editor**, run migrations **in order** (paste file contents only). See [section 7](#7-database-migrations-every-step).

### Step 6 — Create a staff user

Supabase → **Authentication → Users → Add user**. Optional metadata:

```json
{
  "full_name": "Dr. Ada Lovelace",
  "role": "Doctor"
}
```

Roles: `Admin` | `Doctor` | `Nurse` | `Receptionist`

### Step 7 — Start servers

See [section 8](#8-running-the-app).

---

## 5. External APIs — what you NEED vs what we USED

There are two different meanings of “API” in this project:

1. **External / third-party APIs** (Supabase, the AI provider fleet, PubMed, …) — keys in `.env`  
2. **Our FastAPI endpoints** — what the frontend calls — see [section 9](#9-our-backend-apis-what-this-project-exposes)

### 5.1 REQUIRED external APIs (you must configure these)

| Service | What we use it for | Keys / values | Where |
|---------|--------------------|---------------|-------|
| **Supabase Auth** | Login, logout, JWT sessions | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET` | Backend |
| **Supabase PostgREST** | All DB CRUD via REST | `SUPABASE_SERVICE_ROLE_KEY` (server) | Backend |
| **Supabase Auth (browser)** | Session persistence on frontend | `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` | Frontend |
| **Supabase Storage** | Uploaded medical documents (Intake) | Same Supabase project | Backend via service role |

**Without Supabase, the app cannot run.** No paid API is required for a full local demo — real LLM-backed AI Agent runs additionally need **at least one** free provider key from the fleet (`GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, or `HUGGINGFACE_API_KEY` — see [section 3.2](#32-configuring-the-fleet--backendprovidersyaml)), or you can set `AI_PROVIDER=stub` for deterministic offline testing.

---

### 5.2 What we ACTUALLY USE by default today

| Capability | What runs today | External API called? | Notes |
|------------|-----------------|----------------------|-------|
| Auth + DB | **Supabase** | Yes — required | Real cloud/project |
| Document storage | **Supabase Storage** | Yes — required for Intake uploads | Same project |
| Intake OCR | `OCR_PROVIDER=stub` | **No** | Deterministic stub text |
| Intake optional NER enrichment | AI Orchestrator → provider fleet | Only if a provider key is configured | Rule-based NER remains the source of truth; LLM enrichment is best-effort and never blocks Intake |
| Document PDF text | PyMuPDF / pdfplumber | **No cloud API** | Local libraries |
| Optional local OCR | Tesseract / PaddleOCR | **No cloud API** | Local binaries/packages |
| Diagnosis Agent | AI Orchestrator → provider fleet with failover | Only if a provider key is configured | See [section 3](#3-the-ai-orchestrator) |
| Research Agent | AI Orchestrator → provider fleet with failover | Only if a provider key is configured | LLM-generated evidence summaries — never invented as verified citations |
| Prescription Agent | AI Orchestrator → provider fleet with failover | Only if a provider key is configured | In-repo drug knowledge base remains as grounding/reference data in the prompt |
| Medical Report Agent | AI Orchestrator → provider fleet with failover | Only if a provider key is configured | |

**Summary for teammates:** for day-1 onboarding you only need **Supabase**. Every route/page/DB schema works even without an AI provider key — AI Agent runs simply return a clear HTTP 503 listing which providers are unconfigured, until you either add a free provider key (see [section 3.2](#32-configuring-the-fleet--backendprovidersyaml)) or set `AI_PROVIDER=stub` for deterministic offline testing.

---

### 5.3 OPTIONAL external APIs (wired in code, not required)

The **AI provider fleet** (Groq → Gemini → OpenRouter → HuggingFace, plus the paid/local adapters) is documented in [section 3.2](#32-configuring-the-fleet--backendprovidersyaml) — enabling any of them is a `providers.yaml` + `.env` change only, never an agent code change. Everything below is the *non-AI* optional surface.

| External API | Env vars | When it is used | Status in this repo |
|--------------|----------|-----------------|---------------------|
| **Google Cloud Vision** | `GOOGLE_VISION_API_KEY` | `OCR_PROVIDER=google_vision` | Adapter stub/wiring present |
| **Azure AI Vision / Read** | `AZURE_OCR_ENDPOINT`, `AZURE_OCR_KEY` | `OCR_PROVIDER=azure` | Adapter stub/wiring present |
| **Tesseract OCR** | (none — install binary) | `OCR_PROVIDER=tesseract` | Local |
| **PaddleOCR** | (none — pip install) | `OCR_PROVIDER=paddle` | Local |
| **PubMed / NCBI** | `PUBMED_API_KEY` | Future live Research | **Not live yet** — the Research Agent's LLM-backed providers don't call this yet |
| **ClinicalTrials.gov** | `CLINICAL_TRIALS_API_KEY` | Future live Research | **Not live yet** |
| Pharmacy DB (Lexicomp / RxNorm / etc.) | — | Future Prescription | **Not integrated** — in-repo drug KB used as prompt grounding data only |

---

### 5.4 Cheat sheet: “What keys do I need?”

| Goal | Keys needed |
|------|-------------|
| Run app + all agents (schema, UI, workflows) locally | **Supabase only** (URL, anon, service role, JWT + Vite mirrors) |
| Real AI Agent runs (Diagnosis, Research, Prescription, Medical Report) | Any **one** free key: `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, or `HUGGINGFACE_API_KEY` |
| Never being blocked by a quota limit | All **four** free keys — the fleet fails over automatically ([3.1](#31-provider-failover)) |
| Offline/CI testing of AI Agent pipelines without any API key | `AI_PROVIDER=stub` |
| Local/offline LLM | Install [Ollama](https://ollama.com), `ollama pull llama3.1:8b`, set `OLLAMA_ENABLED=true` |
| Paid providers (OpenAI / Claude / Azure OpenAI) | Matching key + `<PROVIDER>_ENABLED=true` in `.env` |
| Better OCR without cloud | Install Tesseract or PaddleOCR; set `OCR_PROVIDER=tesseract` or `paddle` |
| Cloud OCR | Google Vision **or** Azure keys + matching `OCR_PROVIDER` |
| Live PubMed / trials | Not available yet — the Research Agent's LLM-backed providers generate evidence summaries directly |

---

## 6. Environment variables (full list)

### Backend — `backend/.env` (from `.env.example`)

#### Application

| Variable | Default | Required? |
|----------|---------|-----------|
| `APP_NAME` | Hospital AI API | No |
| `APP_ENV` | development | No |
| `APP_DEBUG` | true | No |
| `APP_HOST` | 0.0.0.0 | No |
| `APP_PORT` | 8000 | No |
| `APP_VERSION` | 0.1.0 | No |
| `CORS_ORIGINS` | `http://localhost:5173,...` | No |
| `LOG_LEVEL` | INFO | No |

#### Supabase (required)

| Variable | Required? | Notes |
|----------|-----------|-------|
| `SUPABASE_URL` | **Yes** | Project URL |
| `SUPABASE_ANON_KEY` | **Yes** | Auth password grant |
| `SUPABASE_SERVICE_ROLE_KEY` | **Yes** | Backend DB/Storage — **never** put in frontend |
| `SUPABASE_JWT_SECRET` | **Yes** | Validates Bearer tokens — **never** put in frontend |
| `SUPABASE_SSL_VERIFY` | No | Set `false` only if corporate SSL breaks HTTPS |

#### Intake OCR provider (optional; unrelated to the AI Orchestrator)

| Variable | Default | Notes |
|----------|---------|-------|
| `OCR_PROVIDER` | `stub` | `stub` \| `tesseract` \| `paddle` \| `google_vision` \| `azure` |
| `GOOGLE_VISION_API_KEY` | — | If Google Vision OCR |
| `AZURE_OCR_ENDPOINT` / `AZURE_OCR_KEY` | — | If Azure OCR |

#### AI Orchestrator (single entry point for every AI Agent's LLM calls)

See [section 3](#3-the-ai-orchestrator) for the full architecture. All 5 AI Agents (Intake's optional enrichment, Diagnosis, Research, Prescription, Medical Report) route through these settings — nothing is hardcoded per agent in Python, and the provider *fleet* itself lives in `backend/providers.yaml`.

**Provider credentials** — set as many as you can; each one is an outage the fleet routes around.

| Variable | Default | Notes |
|----------|---------|-------|
| `AI_PROVIDER` | `groq` | *Preferred* primary, not a lock — failover still applies. `stub` is the exception and pins fully offline |
| `GROQ_API_KEY` | — | Priority 1. Free: [console.groq.com/keys](https://console.groq.com/keys) |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | Rarely needs changing |
| `GEMINI_API_KEY` | — | Priority 2. Free: [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `OPENROUTER_API_KEY` | — | Priority 3. Free: [openrouter.ai/keys](https://openrouter.ai/keys) |
| `HUGGINGFACE_API_KEY` | — | Priority 4. Free: [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |
| `OPENAI_API_KEY` | — | Paid. Also set `OPENAI_ENABLED=true` |
| `ANTHROPIC_API_KEY` | — | Paid. Also set `ANTHROPIC_ENABLED=true` |
| `AZURE_OPENAI_API_KEY` / `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_DEPLOYMENT` | — | Paid. Also set `AZURE_OPENAI_ENABLED=true` |
| `OLLAMA_URL` | `http://localhost:11434` | Local, no key. Also set `OLLAMA_ENABLED=true` and `ollama pull <model>` |

**Model routing** — which model each agent uses on the primary provider. Fallback providers use their own `models.default` from `providers.yaml`.

| Variable | Default | Notes |
|----------|---------|-------|
| `INTAKE_MODEL` | `llama-3.3-70b-versatile` | Intake's optional entity-enrichment task |
| `DIAGNOSIS_MODEL` | `llama-3.3-70b-versatile` | Diagnosis Agent |
| `RESEARCH_MODEL` | `llama-3.3-70b-versatile` | Research Agent |
| `PRESCRIPTION_MODEL` | `llama-3.3-70b-versatile` | Prescription Agent |
| `REPORT_MODEL` | `llama-3.3-70b-versatile` | Medical Report Agent |
| `TEMPERATURE` | `0.2` | Generation default, per-call overridable |
| `MAX_TOKENS` | `2048` | Completion reservation. Counts against the provider's per-request ceiling, so a high value shrinks the usable prompt — see [token budgets](#token-budgets-why-max_tokens-shrinks-your-prompt) |
| `TIMEOUT` | `120` | Per-request network timeout (seconds), every provider |
| `GROQ_MAX_REQUEST_TOKENS` | `5800` | Groq's per-request ceiling. Raise it if you upgrade tiers |
| `GEMINI_MAX_REQUEST_TOKENS` | `120000` | Gemini's per-request ceiling |
| `OPENROUTER_MAX_REQUEST_TOKENS` | `60000` | OpenRouter's per-request ceiling |
| `HUGGINGFACE_MAX_REQUEST_TOKENS` | `28000` | HuggingFace's per-request ceiling |

**Failover, health, and routing** — see [section 3.1](#31-provider-failover).

| Variable | Default | Notes |
|----------|---------|-------|
| `AI_FAILOVER_ENABLED` | `true` | Master switch. `false` forces strict single-provider behavior |
| `AI_LOAD_BALANCER_STRATEGY` | `priority` | `priority` \| `round_robin` \| `least_latency` \| `least_errors` |
| `AI_HEALTH_FAILURE_THRESHOLD` | `3` | Consecutive failures before a provider is taken out of rotation |
| `AI_HEALTH_COOLDOWN_SECONDS` | `120` | How long an offline provider is skipped |
| `AI_HEALTH_QUOTA_COOLDOWN_SECONDS` | `900` | Longer cooldown for daily/monthly quota exhaustion |
| `AI_MAX_RETRIES` | `3` | Retry Handler — exponential backoff on transient errors, per provider |
| `AI_RETRY_BASE_DELAY_MS` | `500` | Retry Handler — base delay before backoff multiplier |

**Cache, queue, and token optimization**

| Variable | Default | Notes |
|----------|---------|-------|
| `AI_CACHE_TTL_SECONDS` | `300` | Base TTL; per-agent multipliers apply (research longest, prescription shortest) |
| `AI_CONTEXT_COMPRESSION` | `true` | Compress patient context before each provider call |
| `AI_MEMORY_TURNS` | `5` | Recent conversation turns per patient/agent included in context |
| `AI_MAX_CONCURRENT_REQUESTS` | `4` | Request Queue — bounds simultaneous provider calls |
| `AI_QUEUE_WAIT_TIMEOUT_SECONDS` | `60` | How long a request waits for a queue slot before failing |

**Reserved**

| Variable | Default | Notes |
|----------|---------|-------|
| `PUBMED_API_KEY` | — | Reserved — Research Agent's LLM-backed providers don't call this yet |
| `CLINICAL_TRIALS_API_KEY` | — | Reserved — Research Agent's LLM-backed providers don't call this yet |

### Frontend — `frontend/.env`

| Variable | Required? | Notes |
|----------|-----------|-------|
| `VITE_API_BASE_URL` | Yes | Usually `http://localhost:8000` |
| `VITE_APP_NAME` | No | UI title |
| `VITE_SUPABASE_URL` | **Yes** | Same as backend URL |
| `VITE_SUPABASE_ANON_KEY` | **Yes** | Same as backend anon key |

### Security for teammates

1. Never commit `.env` files  
2. Never put service role or JWT secret in the frontend  
3. Share secrets via a team vault, not chat  

---

## 7. Database migrations (every step)

Run in Supabase **SQL Editor**, **in this order**. Paste **only** the SQL from each file (not chat text).

| Step | File | Creates / updates |
|------|------|-------------------|
| 1 | `001_create_users.sql` | Users, roles, RLS |
| 2 | `002_create_patients.sql` | Patients |
| 3 | `003_create_doctors.sql` | Doctors / departments |
| 4 | `004_create_appointments.sql` | Appointments / availability |
| 5 | `005_create_medical_records.sql` | Medical records / storage hooks |
| 6 | `006_create_resources_announcements.sql` | Resources + announcements |
| 7 | `007_create_intake_agent.sql` | Intake jobs / AI context |
| 8 | `008_create_patient_medical_history.sql` | Medical history |
| 9 | `009_create_ocr_results.sql` | OCR results |
| 10 | `010_ocr_extraction_metadata.sql` | OCR metadata columns |
| 11 | `011_ocr_clean_text_metadata.sql` | Clean-text metadata |
| 12 | `012_create_medical_entities.sql` | NER / entities |
| 13 | `013_create_patient_risk_profiles.sql` | Risk profiles |
| 14 | `014_create_patient_knowledge_graphs.sql` | Knowledge graphs |
| 15 | `015_create_diagnosis_research_agents.sql` | Diagnosis + Research tables |
| 16 | `016_create_prescription_medical_report_agents.sql` | Prescription + Medical Report (7 tables) |
| 17 | `017_create_ai_orchestrator_tables.sql` | `ai_conversation_memory` + `ai_interaction_logs` (AI Orchestrator) |
| 18 | `018_ai_provider_failover.sql` | Failover telemetry columns on `ai_interaction_logs` + `ai_provider_events` |

Path: `backend/migrations/`

If your team already applied these on a shared Supabase project, new teammates only need `.env` keys — **do not re-run** unless creating a fresh project.

---

## 8. Running the app

### Backend

```bash
cd hospital-ai/backend
# activate venv
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

| URL | Purpose |
|-----|---------|
| http://localhost:8000/health | Health check |
| http://localhost:8000/docs | Swagger UI (full interactive API list) |
| http://localhost:8000/ | Welcome JSON |

### Frontend

```bash
cd hospital-ai/frontend
npm run dev
```

App: http://localhost:5173 → `/login`

### Docker Compose (optional)

```bash
cd hospital-ai
docker compose up --build
```

---

## 9. Our backend APIs (what this project exposes)

Base URL: `http://localhost:8000`  
Auth: almost all routes need `Authorization: Bearer <access_token>` (from login).  
Interactive catalog: **/docs**

> Note: paths are **not** prefixed with `/api`. Frontend calls e.g. `/ai/diagnosis/start` directly against `VITE_API_BASE_URL`.

### 9.1 Health & auth

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness |
| `POST` | `/auth/login` | Email/password → tokens + profile |
| `POST` | `/auth/logout` | Invalidate session |
| `GET` | `/auth/me` | Current user + role |

### 9.2 Domain (hospital console)

| Prefix | Purpose |
|--------|---------|
| `/patients` | Patient CRUD / profile |
| `/doctors` | Doctor CRUD / profile |
| `/departments` | Departments |
| `/availability` | Doctor availability |
| `/appointments` | Appointments |
| `/medical-records` | Records + documents |
| `/resources` | Hospital resources |
| `/announcements` | Announcements |
| `/notifications` | Notifications |
| `/dashboard` | Dashboard metrics / search |

(Exact verbs/paths: open Swagger at `/docs`.)

### 9.3 Intake Agent — `/ai/intake`

| Method | Path | Stage |
|--------|------|-------|
| `POST` | `/ai/intake/register` | 1. Patient Registration (multipart upload) |
| `POST` | `/ai/intake/history/extract` | 2. Medical History Extraction |
| `GET` | `/ai/intake/history/{patient_id}` | Get / optionally extract history |
| `POST` | `/ai/intake/ocr/start` | Document OCR |
| `GET` | `/ai/intake/ocr/status/{job_id}` | OCR status |
| `GET` | `/ai/intake/ocr/result/{job_id}` | OCR result |
| `GET` | `/ai/intake/context/{patient_id}` | Patient context |
| `GET` | `/ai/intake/report/{document_id}` | OCR report |
| `POST` | `/ai/intake/ner/start` | Medical Entity Recognition |
| `GET` | `/ai/intake/ner/status/{job_id}` | NER status |
| `GET` | `/ai/intake/ner/result/{job_id}` | NER result |
| `GET` | `/ai/intake/ner/entities/{job_id}` | Entities list |
| `POST` | `/ai/intake/risk/start` | Risk profiling |
| `GET` | `/ai/intake/risk/status/{job_id}` | Risk status |
| `GET` | `/ai/intake/risk/result/{job_id}` | Risk result |
| `POST` | `/ai/intake/kg/start` | Knowledge Graph |
| `GET` | `/ai/intake/kg/status/{job_id}` | KG status |
| `GET` | `/ai/intake/kg/result/{job_id}` | KG result |
| `GET` | `/ai/intake/jobs` | List processing jobs |
| `GET` | `/ai/intake/jobs/{job_id}` | Job detail |

### 9.4 Diagnosis Agent — `/ai/diagnosis`

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/ai/diagnosis/start` | Run full Diagnosis pipeline |
| `GET` | `/ai/diagnosis/{patient_id}` | Latest result |
| `GET` | `/ai/diagnosis/{patient_id}/history` | Run history |

### 9.5 Research Agent — `/ai/research`

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/ai/research/start` | Run full Research pipeline |
| `GET` | `/ai/research/{patient_id}` | Latest result |
| `GET` | `/ai/research/{patient_id}/history` | Run history |

### 9.6 Prescription Agent — `/ai/prescription`

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/ai/prescription/start` | Run full Prescription pipeline |
| `GET` | `/ai/prescription/status/{patient_id}` | Lightweight status |
| `GET` | `/ai/prescription/{patient_id}` | Latest full result |
| `GET` | `/ai/prescription/{patient_id}/history` | Run history |

### 9.7 Medical Report Agent — `/ai/report`

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/ai/report/start` | Run full Medical Report pipeline |
| `GET` | `/ai/report/status/{patient_id}` | Lightweight status |
| `GET` | `/ai/report/{patient_id}` | Latest generated report |
| `GET` | `/ai/report/{patient_id}/history` | Version history |

### 9.8 AI Orchestrator — `/ai/orchestrator` and `/ai/health`

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/ai/orchestrator/status` | Active provider, per-agent model map, failover chain, load-balancer strategy, cache/retry config |
| `GET` | `/ai/orchestrator/stats` | Requests today, avg duration, cache-hit rate, retry rate, per-agent breakdown |
| `GET` | `/ai/orchestrator/logs?limit=` | Recent `ai_interaction_logs` rows, including fallback reason and attempt timeline |
| `GET` | `/ai/orchestrator/providers` | Full provider fleet — config, live health, latency, success/failure rate, quota state, event history |
| `POST` | `/ai/orchestrator/providers/{name}/reset` | Clear a provider's circuit-breaker cooldown and retry it now |
| `POST` | `/ai/orchestrator/providers/reload` | Re-read `providers.yaml` without restarting the backend |
| `GET` | `/ai/orchestrator/queue` | Active + queued requests, progress, wait times |
| `POST` | `/ai/orchestrator/queue/{request_id}/cancel` | Cancel a queued or running request |
| `GET` | `/ai/orchestrator/cache` | Cache hit rate, entry count, per-category TTLs, invalidations |
| `DELETE` | `/ai/orchestrator/cache` | Manual invalidation — all, by agent, or by patient |
| `GET` | `/ai/health` | Fleet-wide health — every provider's status, the failover chain, current models, avg latency (public, no auth — safe for uptime monitors) |

### 9.9 Recommended patient flow (which APIs to call)

```text
1. Domain setup: create Patient + Doctor + Appointment (domain APIs)
2. Intake:      POST /ai/intake/register → history → OCR → NER → risk → KG
3. Diagnosis:   POST /ai/diagnosis/start
4. Research:    POST /ai/research/start
5. Prescription: POST /ai/prescription/start
6. Med Report:  POST /ai/report/start
```

Or use the **AI Center UI** — it calls these for you.

---

## 10. AI agents explained

Recommended order:

```text
Intake → Diagnosis → Research → Prescription → Medical Report
```

### 10.1 Intake Agent (`/ai/intake`)

Builds Patient Context + Knowledge Graph from registration, history, and documents.

| Stage | Output |
|-------|--------|
| Registration | Processing job + uploaded document |
| Medical History | Structured history JSON |
| Context Builder | Aggregated patient context |
| OCR | Extracted text (no diagnosis) |
| NER | Symptoms, meds, allergies, labs, vitals, … |
| Risk Profiling | Scores, categories, alerts |
| Knowledge Graph | Nodes + relationships |

**External APIs used by default:** Supabase only (`OCR_PROVIDER=stub`). NER is rule-based/deterministic; an *optional* LLM entity-enrichment pass runs through the AI Orchestrator (`agent="intake"`, `task="entity_enrichment"`) when the configured provider (Groq by default) is reachable, but never blocks Intake if it isn't.

---

### 10.2 Diagnosis Agent (`/ai/diagnosis`)

Clinical decision support. **Does not prescribe.**

| Stage | Output |
|-------|--------|
| Symptom Analysis | Body-system clusters |
| Differential Diagnosis | Ranked conditions + evidence |
| Probability Scoring | % scores |
| Severity Prediction | Very Low → Critical |
| Treatment Path | Specialists / tests / imaging only |
| Clinical Decision Support | Clinician report + disclaimer |

**Engine:** every stage is now an LLM call through the **AI Orchestrator** (`agent="diagnosis"`, model = `DIAGNOSIS_MODEL`, default `llama-3.3-70b-versatile` via Groq). The in-repo `ConditionKnowledgeBase` is no longer the decision-maker — it's injected into the prompt as grounding/reference data to reduce hallucination. See [section 3](#3-the-ai-orchestrator).

---

### 10.3 Research Agent (`/ai/research`)

Evidence enrichment for Diagnosis. Evidence summaries are now LLM-generated (not literal live PubMed/ClinicalTrials API calls) — they are clearly framed as AI-generated syntheses, not verified citations, until real PubMed/ClinicalTrials integration lands.

| Stage | Output |
|-------|--------|
| PubMed Search | Literature items (LLM-generated) |
| Clinical Trials | Trial items (LLM-generated) |
| Guidelines | Guideline items (LLM-generated) |
| Drug Efficacy | Evidence summaries (LLM-generated) |
| Evidence Ranking | High / Medium / Low |
| Recommendations | Per-condition synthesis |

**Engine:** LLM calls through the **AI Orchestrator** (`agent="research"`, model = `RESEARCH_MODEL`, default `llama-3.3-70b-versatile` via Groq). To keep latency reasonable, one orchestrator call per condition returns literature + trials + guidelines + drug-evidence together, then the pipeline fans that out into the existing per-item response models. Live PubMed / ClinicalTrials keys remain reserved for a future direct-integration provider.

---

### 10.4 Prescription Agent (`/ai/prescription`)

Physician-review **recommendations**. **Never a final prescription.**

| Stage | Output |
|-------|--------|
| Medication Selection | Name, class, purpose, evidence, confidence, alternatives |
| Drug Interaction Check | Minor → Critical + explanations |
| Allergy Verification | Safe / Warning / Contraindicated |
| Dosage Optimization | Starting / maintenance / max **ranges** |
| Treatment Plan | Lifestyle, monitoring, labs, follow-up |
| Validation | Confidence, approval status, warnings |

**Engine:** LLM calls through the **AI Orchestrator** (`agent="prescription"`, model = `PRESCRIPTION_MODEL`, default `llama-3.3-70b-versatile` via Groq). The in-repo drug knowledge base / interaction table stays wired in as prompt grounding data **and** as a deterministic safety cross-check run alongside the LLM output before validation — drug-safety data is high-value to keep deterministic where it exists.

---

### 10.5 Medical Report Agent (`/ai/medical-report` UI · `/ai/report` API)

Documentation from all prior agents.

| Stage | Output |
|-------|--------|
| Clinical Summary | Overview, complaint, history, findings |
| Doctor Notes (SOAP) | S / O / A / P + reasoning |
| Discharge Summary | Course, meds, follow-up |
| Referral Letter | Specialist letter |
| Insurance Documentation | Illustrative codes + medical necessity |
| Patient Report | Plain language + FAQ |

**Engine:** LLM calls through the **AI Orchestrator** (`agent="medical_report"`, model = `REPORT_MODEL`, default `llama-3.3-70b-versatile` via Groq). UI: Preview, Print, Download PDF (browser Save as PDF), Download DOCX, version history.

---

### 10.6 The AI Orchestrator (`/ai/orchestrator`)

Not a clinical agent itself — the shared infrastructure every agent above delegates to. See [section 3](#3-the-ai-orchestrator) for the full breakdown. The page shows the live provider fleet (health, priority, latency, success rate, quota state, cooldowns), the active failover chain and load-balancer strategy, the request queue, cache statistics with manual invalidation, per-agent model routing, usage stats, and recent interaction logs including which runs failed over and why. `GET /ai/health` exposes the same fleet summary for external monitoring.

---

### 10.7 Coming soon

Scheduling · Resource Allocation · Emergency · Insurance · Digital Twin

---

## 11. Frontend routes

| Path | Page |
|------|------|
| `/login` | Staff login |
| `/dashboard` | Dashboard |
| `/patients`, `/doctors`, `/appointments`, `/medical-records`, … | Domain modules |
| `/ai` | AI Center |
| `/ai/intake` | Intake Agent |
| `/ai/diagnosis` | Diagnosis Agent |
| `/ai/research` | Research Agent |
| `/ai/prescription` | Prescription Agent |
| `/ai/medical-report` | Medical Report Agent |
| `/ai/orchestrator` | AI Infrastructure — provider fleet health, failover history, queue, cache, usage stats, logs |

---

## 12. Smoke tests

No Supabase and no provider API access required — the smoke tests force `AI_PROVIDER=stub` and stub out conversation memory/logging, so pipelines run fully in-memory and offline against deterministic canned LLM responses:

```bash
cd hospital-ai/backend
# activate venv
python scripts/smoke_test_diagnosis_research.py
python scripts/smoke_test_prescription_report.py
python scripts/smoke_test_failover.py
```

Expect `SMOKE TEST PASSED`. The first two exercise the full orchestrator path (prompt render → parse → Pydantic validation) without a real provider connection. `smoke_test_failover.py` drives the `ProviderOrchestrator` against mock providers to verify each branch of [3.1](#31-provider-failover): quota exhaustion fails over, transient errors retry in place, invalid keys fail over without retrying, malformed requests are fatal, oversized requests fail over to a roomier provider, the completion reservation shrinks to fit a provider's budget, the circuit breaker skips a provider in cooldown, and a whole-fleet outage produces one clean aggregated error.

To inspect what the fleet resolves to with your actual `.env` (keys reported as present/missing, never printed):

```bash
python scripts/check_provider_fleet.py
```

---

## 13. Clinical safety rules

- Assists clinicians — **never replaces** physician judgment  
- Prescription Agent = recommendations only — **not** a final Rx  
- Diagnosis never claims certainty  
- Show confidence + evidence where available  
- Insurance codes are **illustrative** — coder must verify  
- Generated reports need clinician sign-off before official use  
- LLM-generated research evidence is a synthesis aid, not a verified citation database — cross-check before clinical use

---

## 14. Further docs

| Doc | Content |
|-----|---------|
| [`docs/supabase-setup.md`](./docs/supabase-setup.md) | Supabase project + auth |
| [`docs/intake-agent.md`](./docs/intake-agent.md) | Intake details |
| [`docs/architecture.md`](./docs/architecture.md) | Early scaffold notes (partially historical) |
| Other files under `docs/` | Patients, doctors, appointments, records |

Swagger (live): http://localhost:8000/docs

---

## License

Proprietary — all rights reserved unless otherwise specified by the project owner.
