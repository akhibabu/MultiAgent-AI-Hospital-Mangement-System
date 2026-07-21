# Supabase Setup Guide

This guide walks through creating a Supabase project and wiring it into Hospital AI authentication.

## 1. Create a Supabase project

1. Go to [https://supabase.com](https://supabase.com) and sign in.
2. Click **New project**.
3. Choose an organization, name (e.g. `hospital-ai`), set a strong database password, and pick a region close to you.
4. Wait until the project finishes provisioning.

## 2. Collect API credentials

Open **Project Settings → API**:

| Value | Where it is used |
|-------|------------------|
| Project URL | `SUPABASE_URL` / `VITE_SUPABASE_URL` |
| `anon` `public` key | `SUPABASE_ANON_KEY` / `VITE_SUPABASE_ANON_KEY` |
| `service_role` `secret` key | `SUPABASE_SERVICE_ROLE_KEY` (**backend only**) |

Open **Project Settings → API → JWT Settings** (or **JWT Secret**):

| Value | Where it is used |
|-------|------------------|
| JWT Secret | `SUPABASE_JWT_SECRET` (**backend only**) |

> Never put the service role key or JWT secret in the frontend `.env`.

## 3. Configure environment files

### Backend — `hospital-ai/backend/.env`

```env
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
```

### Frontend — `hospital-ai/frontend/.env`

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=Hospital AI
VITE_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

## 4. Run the Users migration

1. In Supabase, open **SQL Editor → New query**.
2. Paste the contents of:

   `hospital-ai/backend/migrations/001_create_users.sql`

3. Click **Run**.

This creates:

- `public.user_role` enum (`Admin`, `Doctor`, `Nurse`, `Receptionist`)
- `public.users` table (UUID PK linked to `auth.users`)
- `updated_at` trigger
- Auto-profile trigger on new Auth users
- Row Level Security policies (users can read/update their own row)

## 5. Create a test staff user

### Option A — Dashboard (simplest)

1. Open **Authentication → Users → Add user → Create new user**.
2. Enter email + password.
3. Under **User Metadata (JSON)**, optionally set:

```json
{
  "full_name": "Dr. Ada Lovelace",
  "role": "Doctor"
}
```

Valid roles: `Admin`, `Doctor`, `Nurse`, `Receptionist`.

4. Confirm a matching row appears under **Table Editor → users**.

If the user already existed before the migration, insert a profile manually:

```sql
INSERT INTO public.users (id, full_name, email, role)
VALUES (
  '<auth-user-uuid>',
  'Admin User',
  'admin@hospital.local',
  'Admin'
);
```

### Option B — Auth API (later admin tooling)

Use the service role from the backend only; do not expose it in the browser.

## 6. Auth URL settings (local)

In **Authentication → URL Configuration**:

- Site URL: `http://localhost:5173`
- Redirect URLs: `http://localhost:5173/**`

## 7. Verify the integration

```bash
# Backend
cd hospital-ai/backend
uvicorn app.main:app --reload --port 8000

# Frontend
cd hospital-ai/frontend
npm run dev
```

Then:

1. Open `http://localhost:5173/login`
2. Sign in with the test user
3. Confirm redirect to `/dashboard`
4. Confirm Navbar shows **name**, **role**, and **Logout**
5. Call `GET http://localhost:8000/auth/me` with `Authorization: Bearer <access_token>`

## Architecture notes

| Concern | Implementation |
|---------|----------------|
| Login | `POST /auth/login` → Supabase password grant → returns JWT + profile |
| Session | Frontend persists session via `@supabase/supabase-js` |
| API calls | Axios attaches `Authorization: Bearer <access_token>` |
| Protection | FastAPI `SupabaseJWTMiddleware` + `Depends(get_current_user)` |
| Role | Stored in `public.users.role`, returned by `/auth/me` |
