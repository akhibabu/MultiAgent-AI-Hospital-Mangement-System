# Hospital AI — Multi-Agent Hospital Management System

Production-oriented **Clinical Decision Support** platform for hospital staff. Specialized AI agents run as sequential workflows (like a CI pipeline). They **assist clinicians** — they never replace physician judgment, never autonomously prescribe, and never claim certainty.

This is the **main README** for teammates. Everything you need to clone, configure keys, run migrations, and understand agents lives here.

---

## Table of contents

1. [Project status](#1-project-status)
2. [Architecture & frameworks](#2-architecture--frameworks)
3. [Step-by-step setup](#3-step-by-step-setup)
4. [External APIs — what you NEED vs what we USED](#4-external-apis--what-you-need-vs-what-we-used)
5. [Environment variables (full list)](#5-environment-variables-full-list)
6. [Database migrations (every step)](#6-database-migrations-every-step)
7. [Running the app](#7-running-the-app)
8. [Our backend APIs (what this project exposes)](#8-our-backend-apis-what-this-project-exposes)
9. [AI agents explained](#9-ai-agents-explained)
10. [Frontend routes](#10-frontend-routes)
11. [Smoke tests](#11-smoke-tests)
12. [Clinical safety rules](#12-clinical-safety-rules)
13. [Further docs](#13-further-docs)

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
│  AI: Strategy + Factory + Pipeline + Dependency Injection   │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  Supabase                                                   │
│  PostgreSQL · Auth · RLS · Storage (medical documents)      │
└─────────────────────────────────────────────────────────────┘
```

### Design patterns (every AI agent)

| Pattern | Why |
|---------|-----|
| **One agent = one workflow page** | Stages are internal steps, not separate routes |
| **Pipeline** | Runs stages in fixed order |
| **Strategy + Factory** | Swap engines via env (`stub`, `rule_based`, `mock`, future `llm`) without changing routes |
| **Repository** | DB via Supabase REST with service role |
| **DI** | Services/pipelines injectable for smoke tests |

### Folder layout

```text
hospital-ai/
├── backend/
│   ├── app/
│   │   ├── ai/                 # Agent pipelines (intake, diagnosis, research, prescription, medical_report)
│   │   ├── api/                # Router aggregation
│   │   ├── auth/               # JWT dependencies
│   │   ├── config/             # Settings from .env
│   │   ├── repositories/       # Supabase REST access
│   │   ├── routes/             # HTTP endpoints
│   │   ├── schemas/            # Pydantic request/response
│   │   └── services/           # Business facades
│   ├── migrations/             # SQL — run in order in Supabase
│   └── scripts/                # Smoke tests
├── frontend/
│   └── src/
│       ├── pages/AI/           # Agent UI pages
│       ├── hooks/              # React Query hooks
│       ├── services/           # Axios clients
│       └── types/
└── docs/                       # Extra module guides
```

---

## 3. Step-by-step setup

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

In Supabase → **SQL Editor**, run migrations **in order** (paste file contents only). See [section 6](#6-database-migrations-every-step).

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

See [section 7](#7-running-the-app).

---

## 4. External APIs — what you NEED vs what we USED

There are two different meanings of “API” in this project:

1. **External / third-party APIs** (Supabase, OpenAI, PubMed, …) — keys in `.env`  
2. **Our FastAPI endpoints** — what the frontend calls — see [section 8](#8-our-backend-apis-what-this-project-exposes)

### 4.1 REQUIRED external APIs (you must configure these)

| Service | What we use it for | Keys / values | Where |
|---------|--------------------|---------------|-------|
| **Supabase Auth** | Login, logout, JWT sessions | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET` | Backend |
| **Supabase PostgREST** | All DB CRUD via REST | `SUPABASE_SERVICE_ROLE_KEY` (server) | Backend |
| **Supabase Auth (browser)** | Session persistence on frontend | `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` | Frontend |
| **Supabase Storage** | Uploaded medical documents (Intake) | Same Supabase project | Backend via service role |

**Without Supabase, the app cannot run.** No other paid API is required for a full local demo.

---

### 4.2 What we ACTUALLY USE by default today

| Capability | What runs today | External API called? | Notes |
|------------|-----------------|----------------------|-------|
| Auth + DB | **Supabase** | Yes — required | Real cloud/project |
| Document storage | **Supabase Storage** | Yes — required for Intake uploads | Same project |
| Intake OCR | `OCR_PROVIDER=stub` | **No** | Deterministic stub text |
| Intake LLM | `LLM_PROVIDER=stub` | **No** | Local stub completions |
| Document PDF text | PyMuPDF / pdfplumber | **No cloud API** | Local libraries |
| Optional local OCR | Tesseract / PaddleOCR | **No cloud API** | Local binaries/packages |
| Diagnosis Agent | `DIAGNOSIS_ENGINE=rule_based` | **No** | In-repo condition knowledge base |
| Research Agent | `RESEARCH_PROVIDER=mock` | **No** | Synthetic labeled evidence |
| Prescription Agent | `PRESCRIPTION_ENGINE=rule_based` | **No** | In-repo drug knowledge base |
| Medical Report Agent | `MEDICAL_REPORT_ENGINE=template_based` | **No** | Template generators |

**Summary for teammates:** for day-1 onboarding you only need **Supabase**. All five AI agents work without OpenAI / Gemini / PubMed / Azure keys.

---

### 4.3 OPTIONAL external APIs (wired in code, not required)

These adapters exist so you can switch engines later. Default env leaves them unused.

| External API | Env vars | When it is used | Status in this repo |
|--------------|----------|-----------------|---------------------|
| **OpenAI** Chat Completions | `OPENAI_API_KEY`, `OPENAI_MODEL` | `LLM_PROVIDER=openai` | Adapter implemented |
| **Google Gemini** | `GEMINI_API_KEY`, `GEMINI_MODEL` | `LLM_PROVIDER=gemini` | Adapter implemented |
| **Anthropic Claude** | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | `LLM_PROVIDER=anthropic` | Adapter implemented |
| **Ollama** (local) | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | `LLM_PROVIDER=ollama` | Adapter implemented (no cloud key) |
| **Google Cloud Vision** | `GOOGLE_VISION_API_KEY` | `OCR_PROVIDER=google_vision` | Adapter stub/wiring present |
| **Azure AI Vision / Read** | `AZURE_OCR_ENDPOINT`, `AZURE_OCR_KEY` | `OCR_PROVIDER=azure` | Adapter stub/wiring present |
| **Tesseract OCR** | (none — install binary) | `OCR_PROVIDER=tesseract` | Local |
| **PaddleOCR** | (none — pip install) | `OCR_PROVIDER=paddle` | Local |
| **PubMed / NCBI** | `PUBMED_API_KEY` | Future live Research | **Not live yet** — mock only |
| **ClinicalTrials.gov** | `CLINICAL_TRIALS_API_KEY` | Future live Research | **Not live yet** — mock only |
| Pharmacy DB (Lexicomp / RxNorm / etc.) | — | Future Prescription | **Not integrated** — rule_based KB only |

---

### 4.4 Cheat sheet: “What keys do I need?”

| Goal | Keys needed |
|------|-------------|
| Run app + all agents locally | **Supabase only** (URL, anon, service role, JWT + Vite mirrors) |
| Better OCR without cloud | Install Tesseract or PaddleOCR; set `OCR_PROVIDER=tesseract` or `paddle` |
| Real LLM for Intake text tasks | One of OpenAI / Gemini / Anthropic / Ollama + matching `LLM_PROVIDER` |
| Cloud OCR | Google Vision **or** Azure keys + matching `OCR_PROVIDER` |
| Live PubMed / trials | Not available yet — keep `RESEARCH_PROVIDER=mock` |

---

## 5. Environment variables (full list)

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

#### Intake providers (optional)

| Variable | Default | Notes |
|----------|---------|-------|
| `OCR_PROVIDER` | `stub` | `stub` \| `tesseract` \| `paddle` \| `google_vision` \| `azure` |
| `LLM_PROVIDER` | `stub` | `stub` \| `openai` \| `gemini` \| `anthropic` \| `ollama` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | — / `gpt-4o-mini` | If OpenAI |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | — / `gemini-1.5-flash` | If Gemini |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | — / `claude-3-5-haiku-latest` | If Anthropic |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | `http://127.0.0.1:11434` / `llama3.2` | If Ollama |
| `GOOGLE_VISION_API_KEY` | — | If Google Vision OCR |
| `AZURE_OCR_ENDPOINT` / `AZURE_OCR_KEY` | — | If Azure OCR |

#### Downstream agents (optional; defaults work offline)

| Variable | Default |
|----------|---------|
| `DIAGNOSIS_ENGINE` | `rule_based` |
| `RESEARCH_PROVIDER` | `mock` |
| `PUBMED_API_KEY` | (unused until live provider exists) |
| `CLINICAL_TRIALS_API_KEY` | (unused until live provider exists) |
| `PRESCRIPTION_ENGINE` | `rule_based` |
| `MEDICAL_REPORT_ENGINE` | `template_based` |

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

## 6. Database migrations (every step)

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

Path: `backend/migrations/`

If your team already applied these on a shared Supabase project, new teammates only need `.env` keys — **do not re-run** unless creating a fresh project.

---

## 7. Running the app

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

## 8. Our backend APIs (what this project exposes)

Base URL: `http://localhost:8000`  
Auth: almost all routes need `Authorization: Bearer <access_token>` (from login).  
Interactive catalog: **/docs**

> Note: paths are **not** prefixed with `/api`. Frontend calls e.g. `/ai/diagnosis/start` directly against `VITE_API_BASE_URL`.

### 8.1 Health & auth

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness |
| `POST` | `/auth/login` | Email/password → tokens + profile |
| `POST` | `/auth/logout` | Invalidate session |
| `GET` | `/auth/me` | Current user + role |

### 8.2 Domain (hospital console)

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

### 8.3 Intake Agent — `/ai/intake`

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

### 8.4 Diagnosis Agent — `/ai/diagnosis`

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/ai/diagnosis/start` | Run full Diagnosis pipeline |
| `GET` | `/ai/diagnosis/{patient_id}` | Latest result |
| `GET` | `/ai/diagnosis/{patient_id}/history` | Run history |

### 8.5 Research Agent — `/ai/research`

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/ai/research/start` | Run full Research pipeline |
| `GET` | `/ai/research/{patient_id}` | Latest result |
| `GET` | `/ai/research/{patient_id}/history` | Run history |

### 8.6 Prescription Agent — `/ai/prescription`

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/ai/prescription/start` | Run full Prescription pipeline |
| `GET` | `/ai/prescription/status/{patient_id}` | Lightweight status |
| `GET` | `/ai/prescription/{patient_id}` | Latest full result |
| `GET` | `/ai/prescription/{patient_id}/history` | Run history |

### 8.7 Medical Report Agent — `/ai/report`

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/ai/report/start` | Run full Medical Report pipeline |
| `GET` | `/ai/report/status/{patient_id}` | Lightweight status |
| `GET` | `/ai/report/{patient_id}` | Latest generated report |
| `GET` | `/ai/report/{patient_id}/history` | Version history |

### 8.8 Recommended patient flow (which APIs to call)

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

## 9. AI agents explained

Recommended order:

```text
Intake → Diagnosis → Research → Prescription → Medical Report
```

### 9.1 Intake Agent (`/ai/intake`)

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

**External APIs used by default:** Supabase only (`OCR_PROVIDER=stub`, `LLM_PROVIDER=stub`).

---

### 9.2 Diagnosis Agent (`/ai/diagnosis`)

Clinical decision support. **Does not prescribe.**

| Stage | Output |
|-------|--------|
| Symptom Analysis | Body-system clusters |
| Differential Diagnosis | Ranked conditions + evidence |
| Probability Scoring | % scores |
| Severity Prediction | Very Low → Critical |
| Treatment Path | Specialists / tests / imaging only |
| Clinical Decision Support | Clinician report + disclaimer |

**Engine:** `rule_based` — no external medical API.

---

### 9.3 Research Agent (`/ai/research`)

Evidence enrichment for Diagnosis. **Never invents live literature by default** — mock provider returns clearly synthetic evidence shaped like PubMed/trials/guidelines.

| Stage | Output |
|-------|--------|
| PubMed Search | Literature items (mock) |
| Clinical Trials | Trial items (mock) |
| Guidelines | Guideline items (mock) |
| Drug Efficacy | Evidence summaries (mock) |
| Evidence Ranking | High / Medium / Low |
| Recommendations | Per-condition synthesis |

**Provider:** `mock`. Live PubMed / ClinicalTrials keys are reserved for a future `live` provider.

---

### 9.4 Prescription Agent (`/ai/prescription`)

Physician-review **recommendations**. **Never a final prescription.**

| Stage | Output |
|-------|--------|
| Medication Selection | Name, class, purpose, evidence, confidence, alternatives |
| Drug Interaction Check | Minor → Critical + explanations |
| Allergy Verification | Safe / Warning / Contraindicated |
| Dosage Optimization | Starting / maintenance / max **ranges** |
| Treatment Plan | Lifestyle, monitoring, labs, follow-up |
| Validation | Confidence, approval status, warnings |

**Engine:** `rule_based` in-repo drug KB — no Lexicomp/RxNorm API yet.

---

### 9.5 Medical Report Agent (`/ai/medical-report` UI · `/ai/report` API)

Documentation from all prior agents.

| Stage | Output |
|-------|--------|
| Clinical Summary | Overview, complaint, history, findings |
| Doctor Notes (SOAP) | S / O / A / P + reasoning |
| Discharge Summary | Course, meds, follow-up |
| Referral Letter | Specialist letter |
| Insurance Documentation | Illustrative codes + medical necessity |
| Patient Report | Plain language + FAQ |

**Engine:** `template_based`. UI: Preview, Print, Download PDF (browser Save as PDF), Download DOCX, version history.

---

### 9.6 Coming soon

Scheduling · Resource Allocation · Emergency · Insurance · Digital Twin

---

## 10. Frontend routes

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

---

## 11. Smoke tests

No Supabase required — in-memory pipelines:

```bash
cd hospital-ai/backend
# activate venv
python scripts/smoke_test_diagnosis_research.py
python scripts/smoke_test_prescription_report.py
```

Expect `SMOKE TEST PASSED`.

---

## 12. Clinical safety rules

- Assists clinicians — **never replaces** physician judgment  
- Prescription Agent = recommendations only — **not** a final Rx  
- Diagnosis never claims certainty  
- Show confidence + evidence where available  
- Insurance codes are **illustrative** — coder must verify  
- Generated reports need clinician sign-off before official use  

---

## 13. Further docs

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
