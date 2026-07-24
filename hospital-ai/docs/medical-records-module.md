# Medical Records Module

Run migration `backend/migrations/005_create_medical_records.sql` in the Supabase SQL Editor after `004_create_appointments.sql`.

## Features

- Medical record CRUD linked to patient (optional doctor / appointment)
- Multi-file uploads (PDF, PNG, JPEG, JPG, WEBP · max 20 MB)
- Private `medical-records` storage bucket with signed URLs
- Path convention: `medical-records/{patient_id}/{appointment_id|general}/{uuid}_{filename}`
- Document viewer (PDF iframe, image zoom / fullscreen, download)
- Patient profile Medical History (records, reports, prescriptions, labs, imaging, timeline)
- Audit log (`Created`, `Updated`, `Deleted`, `Uploaded File`, `Deleted File`)
- AI / RAG placeholders (columns + stub services) — not implemented

## API

| Method | Path | Notes |
|--------|------|-------|
| GET | `/medical-records` | Pagination, search, filters |
| POST | `/medical-records` | Create record |
| GET | `/medical-records/{id}` | Detail + documents + signed URLs |
| PUT | `/medical-records/{id}` | Update |
| DELETE | `/medical-records/{id}` | Delete record + storage objects |
| POST | `/medical-records/upload` | Multipart: `medical_record_id`, `file` |
| POST | `/medical-records/upload-many` | Multipart: `medical_record_id`, `files` |
| GET | `/medical-records/files/{id}` | Document metadata + signed URL |
| DELETE | `/medical-records/files/{id}` | Delete document |
| GET | `/medical-records/{id}/audit` | Audit trail |

JWT required on all routes.

## Frontend routes

- `/medical-records` — list / filters / create
- `/medical-records/:recordId` — detail, upload, audit, AI placeholders
- `/medical-records/files/:documentId` — standalone document viewer

## RAG preparation (stubs)

Backend DI points in `app/services/ai_placeholders.py`:

- `OCRService`
- `EmbeddingService`
- `VectorIndexService`
- `MedicalSummaryService`

Upload path calls OCR enqueue + embedding hooks (no-ops today).
