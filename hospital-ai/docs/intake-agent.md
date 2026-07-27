# Intake Agent — Unified Workflow

The Intake Agent is **one** workflow with sequential stages — not separate modules.

| Stage | Status |
| --- | --- |
| 1 Patient Registration | ✓ |
| 2 Medical History Extraction | ✓ |
| Patient Context Builder | ✓ (with history) |
| 3 OCR on Reports | ✓ (this release) |
| 4 Medical Entity Recognition | ○ next |
| 5 Risk Profiling | ○ |
| 6 Knowledge Graph | ○ |

## Stage 3 — OCR

Converts the registered upload into machine-readable text/tables/images.

**Does not** identify diseases, medications, symptoms, or diagnose.

### Migration

Run `009_create_ocr_results.sql` after 008.

- Table `ocr_results`
- Columns on `patient_ai_context`: `ocr_completed`, `ocr_provider`, `ocr_confidence`, `ocr_timestamp`, `patient_context_json`, `context_version`

### Architecture

- `OCRProvider` interface — Strategy
- `OCRProviderFactory` — Factory (pluggable)
- Adapters: **Stub** (complete), Tesseract, Paddle, Google Vision, Azure
- `OCRPipeline` / `OCRService` / `OCRRepository`
- `ProcessingStatusUpdater` / `PatientContextUpdater`

Default: `OCR_PROVIDER=stub`

### API

| Method | Path |
| --- | --- |
| POST | `/ai/intake/ocr/start` `{ job_id }` |
| GET | `/ai/intake/ocr/status/{jobId}` |
| GET | `/ai/intake/ocr/result/{jobId}` |
| GET | `/ai/intake/context/{patientId}` |

On success: job `current_stage = Medical Entity Recognition` (NER not executed).

### UI

Single page: `/ai/intake`

Pipeline visualization · job/stage/progress · registration · history · OCR details · context JSON · statistics
