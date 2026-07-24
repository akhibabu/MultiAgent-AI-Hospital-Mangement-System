# Appointments Module

Run migration `backend/migrations/004_create_appointments.sql` in the Supabase SQL Editor after `003_create_doctors.sql`.

## Features

- Book / reschedule / cancel / complete / no-show appointments
- Double-booking prevention (doctor + date overlap on active statuses)
- Doctor availability validation (Emergency may book outside windows)
- Appointment numbers via DB trigger (`APT-######`)
- Dashboard, list, calendar (day/week/month), timeline
- Doctor schedule page (`/appointments/schedule?doctorId=…`)
- Patient appointment history on patient profile
- Placeholder notification service (log-only)
- AI extension columns/interfaces (unused): `predicted_wait_time`, `priority_score`, `recommended_slot`, `ai_notes`, `doctor.schedule_score`

## API

| Method | Path | Notes |
|--------|------|-------|
| GET | `/appointments` | Pagination, search, filters (doctor, patient, department, status, visit_type, date range) |
| GET | `/appointments/slots?doctor_id=&appointment_date=` | Available days + open slots |
| GET | `/appointments/{id}` | Detail with patient/doctor/department briefs |
| POST | `/appointments` | Create (201) |
| PUT | `/appointments/{id}` | Partial update |
| POST | `/appointments/{id}/reschedule` | New date/time → status Rescheduled |
| POST | `/appointments/{id}/status` | Status transitions |
| DELETE | `/appointments/{id}` | Hard delete |

All routes require Supabase JWT.

## Frontend routes

- `/appointments` — dashboard / list / calendar / timeline
- `/appointments/schedule` — doctor schedule
- `/appointments/:appointmentId` — details + actions

## Booking prerequisites

1. At least one patient and one doctor
2. Doctor availability windows configured (`/availability`) for non-emergency bookings
3. Migration applied so `appointments` table exists
