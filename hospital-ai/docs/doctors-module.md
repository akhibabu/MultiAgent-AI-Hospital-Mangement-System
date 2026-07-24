# Doctors Module

## Database

Run in Supabase SQL Editor:

`backend/migrations/003_create_doctors.sql`

Creates:

- `departments`
- `doctors` (auto `DOC-000001`, AI placeholder columns)
- `doctor_availability` (weekly slots for Scheduling Agent)
- Storage bucket `doctor-photos` + RLS policies

## API

| Method | Path |
|--------|------|
| GET/POST | `/doctors` |
| GET/PUT/DELETE | `/doctors/{id}` |
| GET/POST | `/doctors/{id}/availability` |
| PUT/DELETE | `/availability/{id}` |
| GET/POST | `/departments` |
| GET/PUT/DELETE | `/departments/{id}` |

## Frontend

- `/doctors` — list, search, filters, CRUD
- `/doctors/:doctorId` — profile + slots + AI placeholders
- `/departments` — list, details, stats
- `/availability` — weekly schedule manager

## Storage

Profile photos upload via `storageService.uploadDoctorPhoto()` → bucket `doctor-photos`.
