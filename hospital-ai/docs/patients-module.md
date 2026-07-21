# Patients Module

## Database

Run in Supabase SQL Editor:

`backend/migrations/002_create_patients.sql`

This creates `public.patients` with auto `patient_number` (`PAT-000001`), RLS for authenticated staff, and nullable AI extension columns.

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/patients` | List (search, filters, pagination, sort) |
| GET | `/patients/{id}` | Profile |
| POST | `/patients` | Create |
| PUT | `/patients/{id}` | Update |
| DELETE | `/patients/{id}` | Delete |

All require Bearer JWT.

Query params for list: `page`, `page_size`, `search`, `gender`, `blood_group`, `sort_by`, `sort_order`.

## Frontend

- `/patients` — dashboard (table, search, filters, CRUD modals, CSV export)
- `/patients/:patientId` — profile with AI placeholders

## AI extension points (unused)

- `ai_context`
- `latest_diagnosis`
- `latest_report`
- `prediction_history`
