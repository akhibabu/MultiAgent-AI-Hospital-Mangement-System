# Architecture Overview

This document describes the Week 1 Step 1 project scaffold for the
Multi-Agent AI Hospital Management System.

## Goals (this step)

- Establish a scalable monorepo layout under `hospital-ai/`
- Bootstrap React + Vite + TypeScript frontend with Tailwind, Router, Query, Axios
- Bootstrap FastAPI backend with CORS, logging, env config, and `/health`
- Provide Docker packaging for both services
- Leave domain CRUD, database models, Supabase, and auth for later steps

## Layers

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Presentation | `frontend/src/pages`, `components` | UI shells and routing |
| Client services | `frontend/src/services` | HTTP client (Axios) |
| API surface | `backend/app/routes`, `api` | HTTP endpoints |
| Application services | `backend/app/services` | Business logic (future) |
| Domain models | `backend/app/models`, `schemas` | Persistence & contracts (future) |
| Infrastructure | `backend/app/database`, `auth` | Supabase / Auth (future) |

## Frontend conventions

- Feature pages live under `src/pages/<Feature>/`
- Shared layout chrome lives in `src/components/layout` and `src/layouts`
- Reusable primitives live in `src/components/ui`
- Route definitions live in `src/routes/AppRoutes.tsx`
- Theme state is provided via `src/context/ThemeContext.tsx`

## Backend conventions

- Application factory: `app/main.py` → `create_app()`
- Settings via pydantic-settings: `app/config/settings.py`
- Routers aggregated in `app/api`
- Middleware for cross-cutting concerns (request logging, future auth)

## Out of scope (Week 1 Step 1)

- CRUD APIs
- Database tables / ORM models
- Supabase connection
- Authentication implementation
- AI agent orchestration
