"""
OCR Pipeline + Service — Intake Agent Stage 3.

Converts uploaded reports into machine-readable text/tables/images.
Does NOT perform medical understanding (NER / diagnosis / summarization).
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.ai.document_processing import DocumentProcessorFactory
from app.ai.ocr.base import Provenance, now_iso
from app.config import get_settings
from app.core.logging import get_logger
from app.database.http import get_http_client
from app.repositories.ocr_repository import (
    OCRRepository,
    PatientContextUpdater,
    ProcessingStatusUpdater,
)
from app.schemas.ocr import (
    OCRResultOut,
    OCRReportOut,
    OCRStartRequest,
    OCRStartResponse,
    OCRStatusResponse,
    PatientContextResponse,
)
from app.schemas.registration import ProcessingJobOut
from app.services.medical_storage_service import (
    ALLOWED_EXT,
    MAX_BYTES,
    BUCKET,
    medical_storage_service,
)

logger = get_logger("hospital_ai.intake.ocr")

STAGE_OCR = "OCR"
STAGE_NER = "Medical Entity Recognition"
LOW_CONFIDENCE_THRESHOLD = 0.70
OCR_TIMEOUT_SECONDS = 120


class OCRPipeline:
    """
    Stage 3 processing pipeline.

    Receive Job → Load Context → Load Document → Validate → OCR → Store → Update Context → NER stage marker
    """

    def __init__(
        self,
        *,
        status_updater: Optional[ProcessingStatusUpdater] = None,
        context_updater: Optional[PatientContextUpdater] = None,
        ocr_repo: Optional[OCRRepository] = None,
        document_processor=None,
    ) -> None:
        self._status = status_updater or ProcessingStatusUpdater()
        self._context = context_updater or PatientContextUpdater()
        self._ocr_repo = ocr_repo or OCRRepository()
        self._documents = document_processor or DocumentProcessorFactory.create()

    def _download(self, storage_path: str) -> bytes:
        settings = get_settings()
        url = (
            f"{settings.supabase_url.rstrip('/')}/storage/v1/object/"
            f"{BUCKET}/{storage_path}"
        )
        try:
            response = get_http_client().get(
                url,
                headers={
                    "apikey": settings.supabase_service_role_key,
                    "Authorization": f"Bearer {settings.supabase_service_role_key}",
                },
                timeout=OCR_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504, detail="OCR timeout downloading document") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Unable to download document") from exc

        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to download document ({response.status_code})",
            )
        return response.content

    def _validate_document(self, job: Dict[str, Any], file_bytes: bytes) -> None:
        name = job.get("document_name") or "document"
        content_type = job.get("document_type") or "application/octet-stream"
        size = len(file_bytes)

        if size <= 0:
            raise HTTPException(status_code=400, detail="Corrupted or empty file")
        if size > MAX_BYTES:
            raise HTTPException(status_code=400, detail="Large files over 20MB are not supported")

        # Encrypted PDF heuristic
        if b"/Encrypt" in file_bytes[:8000]:
            raise HTTPException(
                status_code=400,
                detail="Encrypted PDFs are not supported. Upload an unlocked PDF.",
            )

        try:
            medical_storage_service.validate_file(
                filename=name,
                content_type=content_type,
                size=size,
            )
        except HTTPException:
            ext = (name.rsplit(".", 1)[-1] if "." in name else "").lower()
            if ext not in ALLOWED_EXT:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file type for OCR",
                )
            raise

    def run(self, job_id: UUID) -> OCRStartResponse:
        job = self._status.get_job(job_id)
        patient_id = UUID(str(job["patient_id"]))

        stage = str(job.get("current_stage") or "")
        # OCR runs after history extraction sets current_stage=OCR.
        # Allow retry when already at NER or Failed.
        if stage == "Patient Registration":
            raise HTTPException(
                status_code=400,
                detail="Complete Medical History Extraction before OCR",
            )

        self._status.mark_ocr_running(job_id)
        started = time.perf_counter()

        try:
            # Load patient context (history preserved)
            self._context.load_or_init(patient_id)

            storage_path = job.get("storage_path")
            if not storage_path:
                raise HTTPException(
                    status_code=400,
                    detail="Processing job has no storage_path for the uploaded document",
                )

            file_bytes = self._download(str(storage_path))
            self._validate_document(job, file_bytes)

            file_name = str(job.get("document_name") or "document")
            content_type = str(job.get("document_type") or "application/octet-stream")

            try:
                processed = self._documents.process(
                    file_bytes=file_bytes,
                    content_type=content_type,
                    file_name=file_name,
                )
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(
                    status_code=502, detail=f"Document processing failed: {exc}"
                ) from exc

            if processed.status == "Failed" or not (processed.clean_text or "").strip():
                detail = (
                    processed.error_message
                    or ("; ".join(processed.errors) if processed.errors else None)
                    or "No readable text could be extracted from this document"
                )
                raise HTTPException(status_code=422, detail=detail)

            elapsed_ms = int((time.perf_counter() - started) * 1000)
            if processed.processing_time_ms <= 0:
                processed.processing_time_ms = elapsed_ms

            warnings = list(processed.warnings or [])
            if processed.confidence < LOW_CONFIDENCE_THRESHOLD:
                msg = (
                    f"Low extraction confidence ({processed.confidence:.2f}). "
                    "Review the text before Medical Entity Recognition."
                )
                if msg not in warnings:
                    warnings.append(msg)

            provider_label = (
                processed.ocr_provider
                or processed.library_used
                or processed.processing_method
            )

            provenance = Provenance(
                source_document=str(storage_path),
                file_name=file_name,
                document_type=content_type,
                page_number=1,
                ocr_provider=provider_label,
                extraction_time=now_iso(),
                confidence_score=processed.confidence,
                processing_job_id=str(job_id),
            ).to_dict()
            provenance.update(
                {
                    "processing_method": processed.processing_method,
                    "extraction_method": processed.processing_method,
                    "document_type_class": processed.document_type,
                    "library_used": processed.library_used,
                    "ocr_provider": processed.ocr_provider,
                    "fallback_used": processed.fallback_used,
                    "document_status": processed.status,
                    "character_count": processed.character_count,
                    "word_count": processed.word_count,
                    "logs": processed.logs[-40:],
                }
            )

            ocr_row = self._ocr_repo.create(
                {
                    "processing_job_id": str(job_id),
                    "patient_id": str(patient_id),
                    "document_id": None,
                    "provider": provider_label,
                    "raw_text": processed.raw_extracted_text or processed.clean_text,
                    "clean_text": processed.clean_text,
                    "tables_json": processed.tables,
                    "images_json": processed.images_meta,
                    "detected_language": processed.language,
                    "page_count": processed.page_count,
                    "processing_time_ms": processed.processing_time_ms,
                    "confidence": processed.confidence,
                    "provenance_json": provenance,
                    "extraction_method": processed.processing_method,
                    "processing_method": processed.processing_method,
                    "document_type": processed.document_type,
                    "ocr_provider": processed.ocr_provider,
                    "library_used": processed.library_used,
                    "fallback_used": processed.fallback_used,
                    "document_status": processed.status,
                    "status": processed.status,
                    "character_count": processed.character_count,
                    "word_count": processed.word_count,
                    "processing_logs": processed.logs[-80:],
                    "error_message": processed.error_message,
                }
            )

            ocr_payload = {
                "raw_text": processed.raw_extracted_text or processed.clean_text,
                "clean_text": processed.clean_text,
                "extracted_report": processed.clean_text,
                "tables": processed.tables,
                "images": processed.images_meta,
                "detected_language": processed.language,
                "confidence": processed.confidence,
                "provider": provider_label,
                "ocr_provider": processed.ocr_provider,
                "page_count": processed.page_count,
                "processing_time_ms": processed.processing_time_ms,
                "processing_method": processed.processing_method,
                "extraction_method": processed.processing_method,
                "document_type": processed.document_type,
                "character_count": processed.character_count,
                "word_count": processed.word_count,
                "document_metadata": {
                    "file_name": job.get("document_name"),
                    "document_type": job.get("document_type"),
                    "file_size": job.get("file_size"),
                    "classified_as": processed.document_type,
                },
                "ocr_result_id": str(ocr_row.get("id")),
                "provenance": provenance,
            }

            context_row = self._context.append_ocr(
                patient_id=patient_id,
                processing_job_id=job_id,
                ocr_payload=ocr_payload,
                provider=provider_label,
                confidence=processed.confidence,
            )

            self._status.mark_ocr_complete(job_id)
            job_out = self._status.get_job(job_id)

            logger.info(
                "Document processing complete job=%s method=%s provider=%s confidence=%.3f pages=%s",
                job_id,
                processed.processing_method,
                provider_label,
                processed.confidence,
                processed.page_count,
            )

            return OCRStartResponse(
                job_id=job_id,
                patient_id=patient_id,
                status=str(job_out.get("status") or "Processing"),
                current_stage=STAGE_NER,
                next_stage=STAGE_NER,
                provider=provider_label,
                confidence=processed.confidence,
                page_count=processed.page_count,
                processing_time_ms=processed.processing_time_ms,
                detected_language=processed.language,
                extraction_method=processed.processing_method,
                processing_method=processed.processing_method,
                document_type=processed.document_type,
                ocr_provider=processed.ocr_provider,
                library_used=processed.library_used,
                fallback_used=processed.fallback_used,
                document_status=processed.status,
                character_count=processed.character_count,
                word_count=processed.word_count,
                warnings=warnings,
                ocr_result=OCRResultOut.model_validate(ocr_row),
                processing_job=ProcessingJobOut.model_validate(job_out),
                patient_context_version=int(context_row.get("context_version") or 1),
            )
        except HTTPException as exc:
            self._status.mark_ocr_failed(job_id, str(exc.detail))
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("OCR pipeline failed job=%s", job_id)
            self._status.mark_ocr_failed(job_id, str(exc))
            raise HTTPException(status_code=500, detail=f"OCR failed: {exc}") from exc


class OCRService:
    """Facade for OCR Stage 3 — Dependency Injection entrypoint."""

    def __init__(self, pipeline: Optional[OCRPipeline] = None) -> None:
        self._pipeline = pipeline or OCRPipeline()
        self._ocr_repo = OCRRepository()
        self._status = ProcessingStatusUpdater()
        self._context = PatientContextUpdater()

    def start(self, request: OCRStartRequest) -> OCRStartResponse:
        return self._pipeline.run(request.job_id)

    def status(self, job_id: UUID) -> OCRStatusResponse:
        job = self._status.get_job(job_id)
        ocr = self._ocr_repo.get_by_job(job_id)
        stage = str(job.get("current_stage") or "")
        progress = 0
        if stage == "Patient Registration":
            progress = 15
        elif stage == "Medical History Extraction":
            progress = 35
        elif stage == STAGE_OCR:
            progress = 55
        elif stage == STAGE_NER:
            progress = 70
        elif job.get("status") == "Completed":
            progress = 100
        elif job.get("status") == "Failed":
            progress = 100

        return OCRStatusResponse(
            job_id=job_id,
            status=str(job.get("status")),
            current_stage=stage,
            next_stage=STAGE_NER if stage == STAGE_OCR else STAGE_NER,
            progress_pct=progress,
            provider=(ocr or {}).get("provider"),
            confidence=float(ocr["confidence"]) if ocr and ocr.get("confidence") is not None else None,
            processing_time_ms=(ocr or {}).get("processing_time_ms"),
            error_message=job.get("error_message"),
            ocr_completed=bool(ocr),
            processing_job=ProcessingJobOut.model_validate(job),
        )

    def result(self, job_id: UUID) -> OCRResultOut:
        row = self._ocr_repo.get_by_job(job_id)
        if not row:
            raise HTTPException(status_code=404, detail="OCR result not found for this job")
        return OCRResultOut.model_validate(row)

    def get_report(self, document_id: UUID) -> OCRReportOut:
        """
        Staff-facing report view.

        `document_id` may be an OCR result id or a processing job id.
        """
        row = self._ocr_repo.get_by_id(document_id)
        job = None
        if not row:
            # Treat as processing job id
            try:
                job = self._status.get_job(document_id)
            except HTTPException:
                raise HTTPException(status_code=404, detail="Report not found") from None
            row = self._ocr_repo.get_by_job(document_id)
            if not row:
                # Job exists but OCR not done — return pending shell
                return OCRReportOut(
                    report_id=str(document_id),
                    file_name=str(job.get("document_name") or "Document"),
                    document_type=str(job.get("document_type") or "Document"),
                    upload_date=job.get("created_at"),
                    language=None,
                    pages=1,
                    confidence=None,
                    processing_time_ms=None,
                    status="Pending OCR",
                    text_preview="OCR has not been run on this document yet.",
                    full_text="",
                )
        else:
            try:
                job = self._status.get_job(UUID(str(row["processing_job_id"])))
            except HTTPException:
                job = {}

        text = str(
            row.get("clean_text")
            or row.get("raw_text")
            or ""
        )
        from app.ai.document_processing.cleaner import DocumentCleaner

        cleaner = DocumentCleaner()
        if cleaner.looks_like_pdf_binary(text):
            text = ""
        else:
            text = cleaner.clean(text)

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        preview = "\n\n".join(paragraphs[:3]) if paragraphs else text[:600]

        method = (
            row.get("processing_method")
            or row.get("extraction_method")
            or (row.get("provenance_json") or {}).get("processing_method")
            or (row.get("provenance_json") or {}).get("extraction_method")
        )
        doc_class = row.get("document_type") or (row.get("provenance_json") or {}).get(
            "document_type_class"
        )
        mime = str((job or {}).get("document_type") or "")
        nice_type = (
            "Digital PDF"
            if doc_class == "digital_pdf"
            else "Scanned PDF"
            if doc_class == "scanned_pdf"
            else "Image"
            if doc_class == "image" or mime.startswith("image/")
            else ("PDF" if "pdf" in mime.lower() else (mime or "Document"))
        )

        return OCRReportOut(
            report_id=str(row.get("id") or document_id),
            file_name=str((job or {}).get("document_name") or "Document"),
            document_type=nice_type,
            processing_method=method,
            extraction_method=method,
            ocr_provider=row.get("ocr_provider") or row.get("provider"),
            upload_date=(job or {}).get("created_at") or row.get("created_at"),
            language=row.get("detected_language"),
            pages=int(row.get("page_count") or 1),
            confidence=float(row["confidence"]) if row.get("confidence") is not None else None,
            processing_time_ms=row.get("processing_time_ms"),
            status=str(row.get("status") or row.get("document_status") or "Completed"),
            character_count=row.get("character_count"),
            word_count=row.get("word_count"),
            text_preview=preview or "No readable text was extracted from this document.",
            full_text=text,
        )

    def get_patient_context(self, patient_id: UUID) -> PatientContextResponse:
        row = self._context.get_context(patient_id)
        ctx = row.get("patient_context_json") or {}
        meta = ctx.get("metadata") or {}
        return PatientContextResponse(
            patient_id=patient_id,
            status=str(row.get("status")),
            current_summary=row.get("current_summary"),
            ocr_completed=bool(row.get("ocr_completed")),
            ocr_provider=row.get("ocr_provider"),
            ocr_confidence=float(row["ocr_confidence"])
            if row.get("ocr_confidence") is not None
            else None,
            ocr_timestamp=row.get("ocr_timestamp"),
            context_version=int(row.get("context_version") or meta.get("version") or 1),
            patient_context_json=ctx if isinstance(ctx, dict) else {},
            metadata=meta if isinstance(meta, dict) else {},
        )


def get_intake_ocr_service() -> OCRService:
    return OCRService()
