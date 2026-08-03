# Multi-Agent AI Hospital Management System

Production-oriented **Clinical Decision Support** platform for hospital staff. Specialized AI agents run as sequential workflows (similar to CI pipelines). They **assist clinicians** — they never replace physician judgment, never autonomously prescribe, and never claim certainty.

The runnable app lives under [`hospital-ai/`](./hospital-ai/).

---

## Table of contents

1. [Project status](#project-status)
2. [Architecture & frameworks](#architecture--frameworks)
3. [AI agents explained](#ai-agents-explained)
4. [API keys & environment variables](#api-keys--environment-variables)
5. [Setup for teammates](#setup-for-teammates)
6. [Database migrations](#database-migrations)
7. [Running locally](#running-locally)
8. [Key API endpoints](#key-api-endpoints)
9. [Frontend routes](#frontend-routes)
10. [Smoke tests](#smoke-tests)
11. [Clinical safety rules](#clinical-safety-rules)
12. [Further docs](#further-docs)

---

## Project status

| Area | Status |
|------|--------|
| Auth (Supabase JWT) | Done |
| Patients / Doctors / Appointments / Records / Resources | Done |
| **Intake Agent** | Done |
| **Diagnosis Agent** | Done |
| **Research Agent** | Done |
| **Prescription Agent** | Done |
| **Medical Report Agent** | Done |
| Scheduling / Emergency / Insurance / Resource Allocation / Digital Twin | Coming soon |

---

## Architecture & frameworks

```text
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React + Vite + TypeScript + Tailwind)            │
│  React Router · TanStack Query · Axios · Supabase JS        │
└────────────────────────────┬────────────────────────────────┘
                             │ Bearer JWT
┌────────────────────────────▼────────────────────────────────┐
│  Backend (FastAPI + Uvicorn + Pydantic)                     │
│  Routes → Services → Repositories → Supabase PostgREST      │
│  AI packages: Strategy + Factory + Pipeline + DI            │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  Supabase (PostgreSQL + Auth + RLS + Storage)               │
└─────────────────────────────────────────────────────────────┘
```

### Backend patterns (every AI agent)

| Pattern | Purpose |
|---------|---------|
| **Pipeline** | Orchestrates stages in order (one agent = one workflow) |
| **Strategy + Factory** | Swap engines (`rule_based`, `stub`, future `llm`) via settings without changing routes |
| **Repository** | All DB access via Supabase REST (service role); no ORM required |
| **Dependency Injection** | Services/pipelines take optional deps for tests and smoke scripts |
| **Pydantic schemas** | Request/response contracts for FastAPI |

### Frontend conventions

- Pages: `frontend/src/pages/`
- Hooks (React Query): `frontend/src/hooks/`
- API clients: `frontend/src/services/`
- Types: `frontend/src/types/`
- AI Center: `/ai` — each agent is **one page** with internal stages (not a separate page per stage)

### Tech stack summary

| Layer | Stack |
|-------|--------|
| Frontend | React 19, Vite 6, TypeScript, Tailwind 4, React Router 7, TanStack Query 5, Axios, Sonner |
| Backend | FastAPI, Uvicorn, Pydantic v2, pydantic-settings, httpx, PyJWT |
| Data / Auth | Supabase (Postgres, Auth, RLS, Storage) |
| OCR (optional) | PyMuPDF, pdfplumber, Pillow, Tesseract, optional PaddleOCR / Google Vision / Azure |
| LLM (optional) | OpenAI / Gemini / Anthropic / Ollama adapters (default = `stub`) |
| Containers | Docker + Docker Compose |

---

## AI agents explained

Each agent is **one intelligent workflow**. Stages are internal steps on a single UI page.

Recommended run order for a patient:

```text
Intake → Diagnosis → Research → Prescription → Medical Report
```

### 1. Intake Agent (`/ai/intake`)

**Purpose:** Build the Patient Context and Knowledge Graph from registration, history, and documents.

| Stage | What it does |
|-------|----------------|
| Patient Registration | Create / link patient |
| Medical History Extraction | Structured history from notes / prior data |
| Patient Context Builder | Aggregate clinical context JSON |
| Document Processing & OCR | Extract text from uploaded documents |
| Medical Entity Recognition (NER) | Symptoms, meds, allergies, labs, vitals, etc. |
| Patient Risk Profiling | Risk categories, scores, alerts |
| Knowledge Graph | Nodes/relationships for downstream agents |

**Outputs consumed by:** Diagnosis, Research, Prescription, Medical Report.

**Providers:** `OCR_PROVIDER`, `LLM_PROVIDER` (defaults `stub` — works with **no** external API keys).

---

### 2. Diagnosis Agent (`/ai/diagnosis`)

**Purpose:** Clinical decision support — differential diagnoses, probabilities, severity, referral pathways. **Does not prescribe.**

| Stage | What it does |
|-------|----------------|
| Symptom Analysis | Cluster symptoms by body system |
| Differential Diagnosis | Rank candidate conditions with evidence for/against |
| Disease Probability Scoring | Calibrated % scores |
| Severity Prediction | Very Low → Critical |
| Treatment Path Recommendation | Specialists, tests, imaging (no meds) |
| Clinical Decision Support | Clinician-facing summary + disclaimer |

**Engine:** `DIAGNOSIS_ENGINE=rule_based` (no API key required).

**APIs:** `POST /api/ai/diagnosis/start`, `GET /api/ai/diagnosis/{patientId}`

---

### 3. Research Agent (`/ai/research`)

**Purpose:** Enrich Diagnosis output with literature, trials, guidelines, and drug evidence. **Never invents facts; never prescribes.**

| Stage | What it does |
|-------|----------------|
| PubMed Search | Literature items |
| Clinical Trial Search | Trials |
| Treatment Guideline Retrieval | WHO / CDC / society-style guidelines |
| Drug Efficacy Analysis | Published evidence only |
| Evidence Ranking | High / Medium / Low |
| Recommendation Generation | Per-condition evidence synthesis |

**Provider:** `RESEARCH_PROVIDER=mock` by default (no keys). Optional live keys: `PUBMED_API_KEY`, `CLINICAL_TRIALS_API_KEY`.

**APIs:** `POST /api/ai/research/start`, `GET /api/ai/research/{patientId}`

---

### 4. Prescription Agent (`/ai/prescription`)

**Purpose:** Physician-review treatment **recommendations**. **Never a final prescription.**

| Stage | What it does |
|-------|----------------|
| Medication Selection | Name, class, purpose, evidence, confidence, alternatives |
| Drug Interaction Check | Minor → Critical + explanations |
| Allergy Verification | Safe / Warning / Contraindicated |
| Dosage Optimization | Starting / maintenance / max **ranges only** |
| Treatment Plan Creation | Meds, lifestyle, monitoring, labs, follow-up |
| Prescription Validation | Duplicates, contraindications, confidence, approval status |

**Engine:** `PRESCRIPTION_ENGINE=rule_based` (in-repo drug knowledge base — no pharmacy API key required).

**APIs:** `POST /api/ai/prescription/start`, `GET /api/ai/prescription/status/{patientId}`

---

### 5. Medical Report Agent (`/ai/medical-report`)

**Purpose:** Generate hospital documentation from all prior agent outputs.

| Stage | What it does |
|-------|----------------|
| Clinical Summary | Overview, complaint, history, findings |
| Doctor Notes (SOAP) | Subjective / Objective / Assessment / Plan |
| Discharge Summary | Course, meds, follow-up, emergency instructions |
| Referral Letter | Specialist letter body |
| Insurance Documentation | Illustrative ICD/CPT-style codes + medical necessity |
| Patient Report | Plain-language report + FAQ |

**Engine:** `MEDICAL_REPORT_ENGINE=template_based` (no API key required).

**APIs:** `POST /api/ai/report/start`, `GET /api/ai/report/status/{patientId}`

UI also supports Preview, Print, Download PDF (browser Save as PDF), Download DOCX, and version history.

---

### Coming soon

- Scheduling Agent  
- Resource Allocation Agent  
- Emergency Agent  
- Insurance Agent  
- Digital Twin  

---

## API keys & environment variables

### What you MUST set (required for local run)

These are **required**. Without them, login and DB calls fail.

| Variable | Where | Where to get it | Notes |
|----------|-------|-----------------|-------|
| `SUPABASE_URL` | Backend | Supabase → Project Settings → API → Project URL | Same project for FE + BE |
| `SUPABASE_ANON_KEY` | Backend | API → `anon` `public` | Used for Auth password grant |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend **only** | API → `service_role` `secret` | **Never** put in frontend |
| `SUPABASE_JWT_SECRET` | Backend **only** | API → JWT Secret | Validates Bearer tokens |
| `VITE_SUPABASE_URL` | Frontend | Same Project URL | Public |
| `VITE_SUPABASE_ANON_KEY` | Frontend | Same `anon` key | Public |
| `VITE_API_BASE_URL` | Frontend | Usually `http://localhost:8000` | Points at FastAPI |

Copy from examples:

```bash
# Backend
cp hospital-ai/backend/.env.example hospital-ai/backend/.env

# Frontend
cp hospital-ai/frontend/.env.example hospital-ai/frontend/.env
```

Full Supabase walkthrough: [`hospital-ai/docs/supabase-setup.md`](./hospital-ai/docs/supabase-setup.md)

---

### Optional AI / OCR / LLM keys (defaults work without them)

| Variable | Used by | Required? | Default / notes |
|----------|---------|-----------|-----------------|
| `OCR_PROVIDER` | Intake OCR | No | `stub` |
| `LLM_PROVIDER` | Intake LLM stages | No | `stub` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | LLM adapter | Only if `LLM_PROVIDER=openai` | e.g. `gpt-4o-mini` |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | LLM adapter | Only if `LLM_PROVIDER=gemini` | |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | LLM adapter | Only if `LLM_PROVIDER=anthropic` | |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | Local LLM | Only if `LLM_PROVIDER=ollama` | Default `http://127.0.0.1:11434` |
| `GOOGLE_VISION_API_KEY` | OCR | Only if `OCR_PROVIDER=google_vision` | |
| `AZURE_OCR_ENDPOINT` / `AZURE_OCR_KEY` | OCR | Only if `OCR_PROVIDER=azure` | |
| `DIAGNOSIS_ENGINE` | Diagnosis | No | `rule_based` |
| `RESEARCH_PROVIDER` | Research | No | `mock` |
| `PUBMED_API_KEY` | Research (live) | No | Optional when not using mock |
| `CLINICAL_TRIALS_API_KEY` | Research (live) | No | Optional when not using mock |
| `PRESCRIPTION_ENGINE` | Prescription | No | `rule_based` |
| `MEDICAL_REPORT_ENGINE` | Medical Report | No | `template_based` |
| `SUPABASE_SSL_VERIFY` | Backend HTTP | No | `true`; set `false` only if corporate SSL inspection breaks HTTPS |

### Backend app settings (usually leave as-is)

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_NAME` | Hospital AI API | Display name |
| `APP_ENV` | development | Environment |
| `APP_DEBUG` | true | Debug mode |
| `APP_HOST` / `APP_PORT` | `0.0.0.0` / `8000` | Uvicorn bind |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed frontend origins |
| `LOG_LEVEL` | INFO | Logging |

### Frontend-only

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_APP_NAME` | Hospital AI | UI product name |

### Security rules for teammates

1. **Never commit** `.env` files (they are gitignored).
2. **Never** put `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_JWT_SECRET` in the frontend.
3. Share secrets via a private channel (1Password / team vault), not chat logs.
4. For demos, `stub` / `mock` / `rule_based` agents need **only** Supabase keys.

---

## Setup for teammates

### Prerequisites

- Node.js **20+** and npm  
- Python **3.11+**  
- Git  
- A Supabase project (shared team project or your own)  
- Docker Desktop (optional)

### 1. Clone

```bash
git clone <your-repo-url>
cd MultiAgent-AI-Hospital-Mangement-System
```

### 2. Backend

```bash
cd hospital-ai/backend
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Fill required Supabase values (see table above)
```

### 3. Frontend

```bash
cd ../frontend
cp .env.example .env
# Fill VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_API_BASE_URL
npm install
```

### 4. Create a staff login user

In Supabase → **Authentication → Users → Add user**, then ensure a row exists in `public.users` (migration `001` auto-creates profile on signup when metadata includes `full_name` / `role`).

Roles: `Admin` | `Doctor` | `Nurse` | `Receptionist`

---

## Database migrations

Run SQL files **in order** in the Supabase **SQL Editor**. Paste **only the SQL file contents** (not chat prompts).

| # | File | Purpose |
|---|------|---------|
| 001 | `001_create_users.sql` | Users + roles + RLS |
| 002 | `002_create_patients.sql` | Patients |
| 003 | `003_create_doctors.sql` | Doctors / departments |
| 004 | `004_create_appointments.sql` | Appointments / availability |
| 005 | `005_create_medical_records.sql` | Medical records / storage |
| 006 | `006_create_resources_announcements.sql` | Resources + announcements |
| 007–014 | Intake agent migrations | History, OCR, NER, risk, knowledge graph, … |
| 015 | `015_create_diagnosis_research_agents.sql` | `diagnosis_results`, `research_results`, `clinical_evidence` |
| 016 | `016_create_prescription_medical_report_agents.sql` | Prescription + Medical Report tables (7 tables) |

Path: `hospital-ai/backend/migrations/`

If a new teammate joins after schema is already applied on the shared Supabase project, they only need env keys — **do not re-run migrations** unless creating a fresh project.

---

## Running locally

### Backend

```bash
cd hospital-ai/backend
# activate venv first
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: [http://localhost:8000/health](http://localhost:8000/health)  
- Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)

### Frontend

```bash
cd hospital-ai/frontend
npm run dev
```

App: [http://localhost:5173](http://localhost:5173)

### Docker Compose (optional)

```bash
cd hospital-ai
docker compose up --build
```

---

## Key API endpoints

All AI routes (except health) require `Authorization: Bearer <access_token>`.

| Agent | Start | Status / latest |
|-------|-------|-----------------|
| Diagnosis | `POST /api/ai/diagnosis/start` | `GET /api/ai/diagnosis/{patientId}` |
| Research | `POST /api/ai/research/start` | `GET /api/ai/research/{patientId}` |
| Prescription | `POST /api/ai/prescription/start` | `GET /api/ai/prescription/status/{patientId}` |
| Medical Report | `POST /api/ai/report/start` | `GET /api/ai/report/status/{patientId}` |

Auth:

| Method | Path |
|--------|------|
| `POST` | `/api/auth/login` |
| `POST` | `/api/auth/logout` |
| `GET` | `/api/auth/me` |

Full interactive catalog: `/docs` when the backend is running.

---

## Frontend routes

| Path | Page |
|------|------|
| `/login` | Staff login |
| `/dashboard` | Dashboard |
| `/patients`, `/doctors`, `/appointments`, … | Domain modules |
| `/ai` | AI Center |
| `/ai/intake` | Intake Agent |
| `/ai/diagnosis` | Diagnosis Agent |
| `/ai/research` | Research Agent |
| `/ai/prescription` | Prescription Agent |
| `/ai/medical-report` | Medical Report Agent |

---

## Smoke tests

No Supabase required — in-memory pipelines:

```bash
cd hospital-ai/backend
# activate venv
python scripts/smoke_test_diagnosis_research.py
python scripts/smoke_test_prescription_report.py
```

Expect `SMOKE TEST PASSED` at the end of each.

---

## Clinical safety rules

This system is a **Clinical Decision Support System (CDSS)**:

- Assists clinicians — **never replaces** physician judgment  
- Prescription Agent outputs **recommendations only** — not a final Rx  
- Diagnosis never claims certainty  
- Always show confidence scores and evidence where available  
- Insurance codes are **illustrative** — a certified coder must verify before claims  
- Generated reports must be reviewed and signed off before official record use  

---

## Further docs

| Doc | Content |
|-----|---------|
| [`hospital-ai/docs/supabase-setup.md`](./hospital-ai/docs/supabase-setup.md) | Supabase project + auth setup |
| [`hospital-ai/docs/intake-agent.md`](./hospital-ai/docs/intake-agent.md) | Intake Agent details |
| [`hospital-ai/docs/architecture.md`](./hospital-ai/docs/architecture.md) | Early scaffold notes (partially historical) |
| Module docs under `hospital-ai/docs/` | Patients, doctors, appointments, records |

---

