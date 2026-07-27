"""OCR repository + processing/context updaters for Intake Stage 3."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException

from app.repositories.intake_repositories import (
    DocumentProcessingJobRepository,
    PatientAIContextRepository,
    PatientMedicalHistoryRepository,
    SupabaseRestRepository,
)


class OCRRepository(SupabaseRestRepository):
    def __init__(self) -> None:
        super().__init__("ocr_results")

    def create(self, body: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self.insert(body)
        except HTTPException as exc:
            # Migrations 010/011 may not be applied yet — retry without new columns
            detail = str(exc.detail).lower()
            if "column" in detail or "pgrst" in detail or "schema cache" in detail:
                optional = {
                    "extraction_method",
                    "processing_method",
                    "document_type",
                    "library_used",
                    "fallback_used",
                    "document_status",
                    "processing_logs",
                    "ocr_provider",
                    "clean_text",
                    "character_count",
                    "word_count",
                    "status",
                }
                slim = {k: v for k, v in body.items() if k not in optional}
                return self.insert(slim)
            raise

    def get_by_job(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        rows = self.select(
            [
                ("select", "*"),
                ("processing_job_id", f"eq.{job_id}"),
                ("order", "created_at.desc"),
                ("limit", "1"),
            ]
        )
        return rows[0] if rows else None

    def list_for_patient(self, patient_id: UUID, limit: int = 20) -> List[Dict[str, Any]]:
        return self.select(
            [
                ("select", "*"),
                ("patient_id", f"eq.{patient_id}"),
                ("order", "created_at.desc"),
                ("limit", str(limit)),
            ]
        )


class ProcessingStatusUpdater:
    """Updates document_processing_jobs stage/status during Intake."""

    STAGE_OCR = "OCR"
    STAGE_NER = "Medical Entity Recognition"

    def __init__(self, jobs: Optional[DocumentProcessingJobRepository] = None) -> None:
        self._jobs = jobs or DocumentProcessingJobRepository()

    def mark_ocr_running(self, job_id: UUID) -> Dict[str, Any]:
        return self._jobs.update(
            job_id,
            {
                "status": "Processing",
                "current_stage": self.STAGE_OCR,
                "error_message": None,
                "processing_started_at": datetime.utcnow().isoformat() + "Z",
            },
        )

    def mark_ocr_failed(self, job_id: UUID, error: str) -> Dict[str, Any]:
        return self._jobs.update(
            job_id,
            {
                "status": "Failed",
                "current_stage": self.STAGE_OCR,
                "error_message": error[:2000],
            },
        )

    def mark_ocr_complete(self, job_id: UUID) -> Dict[str, Any]:
        """OCR done → advance stage marker to Medical Entity Recognition (not run)."""
        return self._jobs.update(
            job_id,
            {
                "status": "Processing",
                "current_stage": self.STAGE_NER,
                "error_message": None,
            },
        )

    def get_job(self, job_id: UUID) -> Dict[str, Any]:
        row = self._jobs.get_by_id(job_id)
        if not row:
            raise HTTPException(status_code=404, detail="Processing job not found")
        return row


class PatientContextUpdater:
    """
    Append OCR output into patient_ai_context.patient_context_json.

    Never overwrites medical history — only enriches with OCR sections.
    """

    def __init__(
        self,
        *,
        contexts: Optional[PatientAIContextRepository] = None,
        histories: Optional[PatientMedicalHistoryRepository] = None,
    ) -> None:
        self._contexts = contexts or PatientAIContextRepository()
        self._histories = histories or PatientMedicalHistoryRepository()

    def load_or_init(self, patient_id: UUID) -> Dict[str, Any]:
        ctx = self._contexts.get_by_patient(patient_id)
        history = self._histories.get_by_patient(patient_id)
        base: Dict[str, Any] = {}
        if ctx and isinstance(ctx.get("patient_context_json"), dict):
            base = dict(ctx["patient_context_json"])
        if history and history.get("medical_history_json") and "medical_history" not in base:
            base["medical_history"] = history["medical_history_json"]
            base["timeline"] = history.get("timeline_json") or []
        if "metadata" not in base:
            base["metadata"] = {
                "version": 1,
                "history_confidence": 0.7,
                "ocr_confidence": None,
                "overall_confidence": 0.7,
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "data_sources": [],
            }
        return {"row": ctx, "context": base}

    def append_ocr(
        self,
        *,
        patient_id: UUID,
        processing_job_id: UUID,
        ocr_payload: Dict[str, Any],
        provider: str,
        confidence: float,
    ) -> Dict[str, Any]:
        loaded = self.load_or_init(patient_id)
        context = loaded["context"]
        meta = dict(context.get("metadata") or {})
        version = int(meta.get("version") or 1) + 1
        history_conf = float(meta.get("history_confidence") or 0.7)
        overall = round((history_conf + confidence) / 2.0, 4)

        sources = list(meta.get("data_sources") or [])
        sources.append(
            {
                "type": "ocr",
                "provider": provider,
                "processing_job_id": str(processing_job_id),
                "at": datetime.utcnow().isoformat() + "Z",
            }
        )

        # Append OCR — do not delete history keys
        ocr_docs = list(context.get("ocr_documents") or [])
        ocr_docs.append(ocr_payload)

        extraction_date = datetime.utcnow().isoformat() + "Z"
        clean_text = (
            ocr_payload.get("clean_text")
            or ocr_payload.get("extracted_report")
            or ocr_payload.get("raw_text")
            or ""
        )
        processing_method = ocr_payload.get("processing_method") or ocr_payload.get(
            "extraction_method"
        )

        context["ocr_metadata"] = {
            "provider": provider,
            "ocr_provider": ocr_payload.get("ocr_provider") or provider,
            "processing_method": processing_method,
            "confidence": confidence,
            "completed": True,
            "extraction_date": extraction_date,
            "timestamp": extraction_date,
            "processing_job_id": str(processing_job_id),
            "character_count": ocr_payload.get("character_count"),
            "word_count": ocr_payload.get("word_count"),
            "page_count": ocr_payload.get("page_count"),
        }
        context["ocr_documents"] = ocr_docs
        # NER and downstream stages MUST consume cleaned text only
        context["extracted_report"] = clean_text
        context["clean_ocr_text"] = clean_text
        context["raw_ocr_text"] = ocr_payload.get("raw_text")
        context["extracted_tables"] = ocr_payload.get("tables")
        context["image_references"] = ocr_payload.get("images")
        context["document_metadata"] = {
            **(ocr_payload.get("document_metadata") or {}),
            "processing_method": processing_method,
            "document_type": ocr_payload.get("document_type"),
            "confidence": confidence,
            "extraction_date": extraction_date,
        }
        context["metadata"] = {
            **meta,
            "version": version,
            "history_confidence": history_conf,
            "ocr_confidence": confidence,
            "overall_confidence": overall,
            "last_updated": extraction_date,
            "data_sources": sources,
        }

        payload = {
            "processing_job_id": str(processing_job_id),
            "status": "Pending",
            "ocr_completed": True,
            "ocr_provider": provider,
            "ocr_confidence": confidence,
            "ocr_timestamp": extraction_date,
            "patient_context_json": context,
            "context_version": version,
            "current_summary": (
                (loaded["row"] or {}).get("current_summary")
                or "Patient context enriched with cleaned report text."
            ),
        }

        if loaded["row"]:
            return self._contexts.update(UUID(str(loaded["row"]["id"])), payload)
        return self._contexts.create({"patient_id": str(patient_id), **payload})

    def get_context(self, patient_id: UUID) -> Dict[str, Any]:
        row = self._contexts.get_by_patient(patient_id)
        if not row:
            raise HTTPException(status_code=404, detail="Patient AI context not found")
        return row
