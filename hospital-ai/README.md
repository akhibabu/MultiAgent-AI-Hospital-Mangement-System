# Hospital AI

Runnable monorepo for the **Multi-Agent AI Hospital Management System**.

For the full teammate guide (agents, frameworks, API keys, migrations, smoke tests), see the **root README**:

**[../README.md](../README.md)**

---

## Quick start

### 1. Environment

```bash
# Backend
cp backend/.env.example backend/.env
# Fill: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET

# Frontend
cp frontend/.env.example frontend/.env
# Fill: VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_API_BASE_URL
```

Supabase walkthrough: [`docs/supabase-setup.md`](./docs/supabase-setup.md)

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: http://localhost:8000/health  
- Swagger: http://localhost:8000/docs  

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

### 4. Docker (optional)

```bash
docker compose up --build
```

---

## Layout

```text
hospital-ai/
├── backend/          # FastAPI + AI agent pipelines
│   ├── app/
│   ├── migrations/   # Run in order in Supabase SQL Editor
│   └── scripts/      # Smoke tests
├── frontend/         # React + Vite + TypeScript
└── docs/             # Module & setup guides
```

---

## AI Center

| Agent | Route | Default engine (no paid keys) |
|-------|-------|-------------------------------|
| Intake | `/ai/intake` | `OCR_PROVIDER=stub`, `LLM_PROVIDER=stub` |
| Diagnosis | `/ai/diagnosis` | `DIAGNOSIS_ENGINE=rule_based` |
| Research | `/ai/research` | `RESEARCH_PROVIDER=mock` |
| Prescription | `/ai/prescription` | `PRESCRIPTION_ENGINE=rule_based` |
| Medical Report | `/ai/medical-report` | `MEDICAL_REPORT_ENGINE=template_based` |

Required for any local run: **Supabase URL + anon key + service role + JWT secret** (backend) and matching Vite Supabase vars (frontend). All other AI keys are optional.

---

## License

Proprietary — all rights reserved unless otherwise specified by the project owner.
