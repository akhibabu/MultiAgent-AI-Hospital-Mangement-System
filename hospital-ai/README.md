# Hospital AI — Multi-Agent Hospital Management System

Production-oriented multi-agent AI hospital management platform.

Current status: **Week 1 · Auth** — project scaffold + Supabase authentication.

> Hospital domain CRUD (patients, doctors, appointments, etc.) is not implemented yet.

---

## Project Overview

**Hospital AI** coordinates clinical and operational workflows through specialized AI agents, with a modern staff console for patients, doctors, appointments, records, departments, and resources.

This step delivers:

- Scalable React + FastAPI monorepo under `hospital-ai/`
- Supabase Auth (email/password) with JWT validation
- `public.users` table + Row Level Security
- Login / logout / session persistence / protected routes
- Navbar user name, role, and logout

---

## Tech Stack

| Area | Technology |
|------|------------|
| Frontend | React, Vite, TypeScript, Tailwind CSS |
| Routing / data | React Router DOM, TanStack React Query, Axios |
| Backend | FastAPI, Uvicorn, Pydantic, pydantic-settings |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth + JWT middleware |
| Storage (planned) | Supabase Storage |
| Containers | Docker, Docker Compose |
| Package manager | npm (frontend), pip (backend) |

---

## Supabase setup (required)

Follow the full walkthrough:

**[`docs/supabase-setup.md`](./docs/supabase-setup.md)**

Quick checklist:

1. Create a Supabase project
2. Copy API URL, anon key, service role key, and JWT secret into `.env` files
3. Run `backend/migrations/001_create_users.sql` in the SQL Editor
4. Create a test Auth user with metadata `full_name` + `role`
5. Start frontend + backend and sign in at `/login`

---

## Setup Instructions

### Prerequisites

- Node.js 20+ and npm
- Python 3.11+
- Git
- A Supabase project
- Docker Desktop (optional)

### 1. Clone

```bash
git clone <your-repo-url>
cd MultiAgent-AI-Hospital-Mangement-System/hospital-ai
```

### 2. Frontend

```bash
cd frontend
cp .env.example .env
# fill VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
npm install
```

### 3. Backend

```bash
cd ../backend
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# fill SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET
```

---

## Running the Project

### Frontend

```bash
cd hospital-ai/frontend
npm run dev
```

App: [http://localhost:5173](http://localhost:5173) → redirects to `/login` when signed out.

### Backend

```bash
cd hospital-ai/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `POST /auth/login` | Email/password login |
| `POST /auth/logout` | Invalidate session (Bearer required) |
| `GET /auth/me` | Current user profile + role (Bearer required) |
| `/docs` | Swagger UI |

### Docker Compose

```bash
cd hospital-ai
docker compose up --build
```

---

## Auth architecture

```text
Login Page
   │  POST /auth/login
   ▼
FastAPI AuthService ──► Supabase Auth (password grant)
   │
   ├── returns access_token + refresh_token + users profile
   ▼
Frontend AuthContext
   ├── supabase.auth.setSession(...)   (persistence / refresh)
   ├── React Query caches /auth/me
   └── Axios attaches Authorization: Bearer <token>
   ▼
Protected routes + Navbar (name, role, logout)
   ▼
SupabaseJWTMiddleware + Depends(get_current_user)
```

Roles: `Admin` | `Doctor` | `Nurse` | `Receptionist`

---

## What is included

- Supabase client (frontend + backend)
- Users table migration with RLS
- Login page (validation, loading, errors, remember me)
- Logout + session persistence
- Protected / public route guards
- User context + role retrieval
- JWT verification middleware + DI dependencies

## What is intentionally not included

- Patients / Doctors / Appointments / Medical Records CRUD
- AI agent orchestration
- Password reset flow (UI button only)
- Supabase Storage

---

## License

Proprietary — all rights reserved unless otherwise specified by the project owner.
