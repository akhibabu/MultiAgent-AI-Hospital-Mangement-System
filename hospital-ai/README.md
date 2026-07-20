# Hospital AI — Multi-Agent Hospital Management System

Production-oriented scaffold for a multi-agent AI hospital management platform.
This repository currently contains **Week 1 · Step 1**: project initialization and scalable architecture only.

> No domain CRUD, database models, Supabase wiring, or authentication logic is implemented yet.

---

## Project Overview

**Hospital AI** is designed to coordinate clinical and operational workflows through specialized AI agents, while providing staff with a modern web console for patients, doctors, appointments, records, departments, and resources.

Week 1 Step 1 establishes:

- A monorepo under `hospital-ai/`
- A React + Vite + TypeScript frontend with routing, theming, and layout chrome
- A FastAPI backend with CORS, logging, environment configuration, and health checks
- Docker packaging for local and containerized development

---

## Tech Stack

| Area | Technology |
|------|------------|
| Frontend | React, Vite, TypeScript, Tailwind CSS |
| Routing / data | React Router DOM, TanStack React Query, Axios |
| Backend | FastAPI, Uvicorn, Pydantic, pydantic-settings |
| Database (planned) | Supabase (PostgreSQL) |
| Auth (planned) | Supabase Auth |
| Storage (planned) | Supabase Storage |
| Containers | Docker, Docker Compose |
| Package manager | npm (frontend), pip (backend) |

---

## Folder Structure

```text
hospital-ai/
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── common/          # ProtectedRoute, PagePlaceholder
│   │   │   ├── layout/          # Sidebar, Navbar
│   │   │   └── ui/              # Loading, ErrorState
│   │   ├── pages/
│   │   │   ├── Dashboard/
│   │   │   ├── Patients/
│   │   │   ├── Doctors/
│   │   │   ├── Appointments/
│   │   │   ├── MedicalRecords/
│   │   │   ├── Departments/
│   │   │   ├── Resources/
│   │   │   ├── Profile/
│   │   │   └── Login/
│   │   ├── layouts/
│   │   ├── hooks/
│   │   ├── context/
│   │   ├── services/
│   │   ├── types/
│   │   ├── utils/
│   │   ├── routes/
│   │   └── styles/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── config/
│   │   ├── core/
│   │   ├── database/
│   │   ├── middleware/
│   │   ├── models/
│   │   ├── routes/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   └── main.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── docs/
│   └── architecture.md
├── docker-compose.yml
└── README.md
```

---

## Setup Instructions

### Prerequisites

- Node.js 20+ and npm
- Python 3.11+
- Git
- Docker Desktop (optional, for containerized runs)

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd MultiAgent-AI-Hospital-Mangement-System/hospital-ai
```

### 2. Frontend setup

```bash
cd frontend
cp .env.example .env
npm install
```

### 3. Backend setup

```bash
cd ../backend
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

---

## Running the Project

### Frontend (Vite)

```bash
cd hospital-ai/frontend
npm run dev
```

App: [http://localhost:5173](http://localhost:5173)

### Backend (Uvicorn)

```bash
cd hospital-ai/backend
# ensure virtualenv is active
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API root: [http://localhost:8000](http://localhost:8000)
- Health: [http://localhost:8000/health](http://localhost:8000/health)
- Swagger docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Docker Compose

From `hospital-ai/`:

```bash
docker compose up --build
```

- Frontend (nginx): [http://localhost:3000](http://localhost:3000)
- Backend API: [http://localhost:8000](http://localhost:8000)

---

## What is included in this step

- Sidebar layout, navbar, global theme (light/dark)
- Protected route scaffold (auth deferred)
- Loading, error, and 404 UI components
- Placeholder pages for all primary modules
- FastAPI app factory with CORS, logging middleware, env settings
- `/health` endpoint
- Frontend & backend Dockerfiles + Compose stack

## What is intentionally not included

- CRUD APIs
- Database tables / ORM models
- Supabase connection
- Authentication implementation
- AI agent logic

---

## Next steps (roadmap)

1. Connect Supabase project and define database schema
2. Implement authentication with Supabase Auth
3. Add domain models, schemas, and CRUD APIs
4. Introduce multi-agent orchestration services
5. Wire React Query hooks to live endpoints

---

## License

Proprietary — all rights reserved unless otherwise specified by the project owner.
