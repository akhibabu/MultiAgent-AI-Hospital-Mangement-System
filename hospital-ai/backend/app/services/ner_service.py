"""
Medical Entity Recognition Pipeline — Intake Agent Stage 4.

Consumes cleaned OCR text only. Recognizes entities — never diagnoses.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.ner.extractor import MedicalEntityRecognizer, medical_entity_recognizer
from app.core.logging import get_logger
from app.repositories.ner_repository import (
    MedicalEntityRepository,
    MedicalEntityResultRepository,
    NERContextUpdater,
    NERStatusUpdater,
)
from app.repositories.ocr_repository import OCRRepository
from app.schemas.ner import (
    EntityStatistics,
    MedicalEntityOut,
    NERResultOut,
    NERStartRequest,
    NERStartResponse,
    NERStatusResponse,
    PatientEntitySummary,
)
from app.schemas.registration import ProcessingJobOut

logger = get_logger("hospital_ai.intake.ner")

STAGE_NER = "Medical Entity Recognition"
STAGE_RISK = "Patient Risk Profiling"


class NERPipeline:
    """
    Load cleaned text → NER → persist entities → update patient context → mark Risk stage.
    """

    def __init__(
        self,
        *,
        status_updater: Optional[NERStatusUpdater] = None,
        context_updater: Optional[NERContextUpdater] = None,
        entity_repo: Optional[MedicalEntityRepository] = None,
        result_repo: Optional[MedicalEntityResultRepository] = None,
        ocr_repo: Optional[OCRRepository] = None,
        recognizer: Optional[MedicalEntityRecognizer] = None,
    ) -> None:
        self._status = status_updater or NERStatusUpdater()
        self._context = context_updater or NERContextUpdater()
        self._entities = entity_repo or MedicalEntityRepository()
        self._results = result_repo or MedicalEntityResultRepository()
        self._ocr = ocr_repo or OCRRepository()
        self._recognizer = recognizer or medical_entity_recognizer

    def _resolve_clean_text(
        self, job: Dict[str, Any], patient_id: UUID
    ) -> tuple[str, Optional[str], Optional[str]]:
        """Return (clean_text, ocr_result_id, source_document_name)."""
        ocr = self._ocr.get_by_job(UUID(str(job["id"])))
        if ocr:
            text = str(ocr.get("clean_text") or ocr.get("raw_text") or "").strip()
            # Reject PDF binary leftovers
            if text.startswith("%PDF") or "endobj" in text[:500]:
                text = ""
            return (
                text,
                str(ocr.get("id")) if ocr.get("id") else None,
                str(job.get("document_name") or "document"),
            )

        # Fallback: patient context cleaned text
        from app.repositories.intake_repositories import PatientAIContextRepository

        ctx_row = PatientAIContextRepository().get_by_patient(patient_id)
        if ctx_row and isinstance(ctx_row.get("patient_context_json"), dict):
            ctx = ctx_row["patient_context_json"]
            text = str(
                ctx.get("clean_ocr_text")
                or ctx.get("extracted_report")
                or ctx.get("raw_ocr_text")
                or ""
            ).strip()
            if text.startswith("%PDF"):
                text = ""
            return text, None, str(job.get("document_name") or "document")

        return "", None, str(job.get("document_name") or "document")

    def run(self, job_id: UUID) -> NERStartResponse:
        job = self._status.get_job(job_id)
        patient_id = UUID(str(job["patient_id"]))
        stage = str(job.get("current_stage") or "")

        # NER runs after OCR sets current_stage to Medical Entity Recognition
        # Allow retry when already at Risk Profiling
        if stage in {"Patient Registration", "Medical History Extraction", "OCR"}:
            raise HTTPException(
                status_code=400,
                detail="Complete Document Processing (OCR) before Medical Entity Recognition",
            )

        if not job.get("status") or job.get("status") == "Failed":
            # Allow retry from failed NER
            pass

        self._status.mark_ner_running(job_id)
        started = time.perf_counter()

        try:
            clean_text, ocr_result_id, source_name = self._resolve_clean_text(
                job, patient_id
            )
            if not clean_text:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "No cleaned document text available for entity recognition. "
                        "Re-run Document Processing on a digital PDF first."
                    ),
                )

            extracted = self._recognizer.extract(
                clean_text,
                source_document=source_name,
                page=1,
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            stats = extracted.statistics()
            summary = extracted.summary()
            entity_dicts = [e.to_dict() for e in extracted.entities]

            # Replace prior NER rows for this job (re-run safe)
            self._entities.delete_for_job(job_id)
            rows_to_insert: List[Dict[str, Any]] = []
            for ent in extracted.entities:
                rows_to_insert.append(
                    {
                        "patient_id": str(patient_id),
                        "processing_job_id": str(job_id),
                        "document_id": None,
                        "ocr_result_id": ocr_result_id,
                        "entity_type": ent.type,
                        "entity_value": ent.value,
                        "confidence": ent.confidence,
                        "page_number": ent.page,
                        "sentence": ent.sentence,
                        "char_start": ent.char_start,
                        "char_end": ent.char_end,
                        "source_document": ent.source_document,
                        "extraction_time": ent.extraction_time,
                        "metadata_json": ent.metadata or {},
                    }
                )
            inserted = self._entities.create_many(rows_to_insert)

            # Attach DB ids when available
            entities_out: List[MedicalEntityOut] = []
            for i, ent in enumerate(extracted.entities):
                data = ent.to_dict()
                if i < len(inserted) and inserted[i].get("id"):
                    data["id"] = inserted[i]["id"]
                entities_out.append(MedicalEntityOut.model_validate(data))

            result_row = self._results.upsert_for_job(
                job_id,
                {
                    "patient_id": str(patient_id),
                    "ocr_result_id": ocr_result_id,
                    "entity_count": len(extracted.entities),
                    "statistics_json": stats,
                    "summary_json": summary,
                    "entities_json": entity_dicts,
                    "source_text_preview": clean_text[:2000],
                    "confidence": extracted.confidence,
                    "processing_time_ms": elapsed_ms,
                    "status": "Completed",
                    "error_message": None,
                },
            )

            ner_payload = {
                "entities": entity_dicts,
                "statistics": stats,
                "summary": summary,
                "confidence": extracted.confidence,
                "source": extracted.source,
                "ocr_result_id": ocr_result_id,
                "source_document": source_name,
            }
            context_row = self._context.append_entities(
                patient_id=patient_id,
                processing_job_id=job_id,
                entities_payload=ner_payload,
                confidence=extracted.confidence,
                entity_count=len(extracted.entities),
            )

            self._status.mark_ner_complete(job_id)
            job_out = self._status.get_job(job_id)

            warnings: List[str] = []
            if extracted.confidence < 0.5:
                warnings.append(
                    "Entity recognition confidence is low. Review highlighted entities carefully."
                )
            if not extracted.entities:
                warnings.append(
                    "No medical entities were recognized in the cleaned text."
                )

            logger.info(
                "NER complete job=%s entities=%s confidence=%.3f",
                job_id,
                len(extracted.entities),
                extracted.confidence,
            )

            return NERStartResponse(
                job_id=job_id,
                patient_id=patient_id,
                status=str(job_out.get("status") or "Processing"),
                current_stage=STAGE_RISK,
                next_stage=STAGE_RISK,
                entity_count=len(extracted.entities),
                confidence=extracted.confidence,
                processing_time_ms=elapsed_ms,
                statistics=EntityStatistics.model_validate(stats),
                summary=PatientEntitySummary.model_validate(summary),
                entities=entities_out,
                source_text=clean_text,
                warnings=warnings,
                ner_result=NERResultOut.model_validate(result_row),
                processing_job=ProcessingJobOut.model_validate(job_out),
                patient_context_version=int(context_row.get("context_version") or 1),
            )
        except HTTPException as exc:
            self._status.mark_ner_failed(job_id, str(exc.detail))
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("NER pipeline failed job=%s", job_id)
            self._status.mark_ner_failed(job_id, str(exc))
            raise HTTPException(
                status_code=500, detail=f"Medical Entity Recognition failed: {exc}"
            ) from exc


class NERService:
    """Facade for Stage 4 — Dependency Injection entrypoint."""

    def __init__(self, pipeline: Optional[NERPipeline] = None) -> None:
        self._pipeline = pipeline or NERPipeline()
        self._results = MedicalEntityResultRepository()
        self._entities = MedicalEntityRepository()
        self._status = NERStatusUpdater()

    def start(self, request: NERStartRequest) -> NERStartResponse:
        return self._pipeline.run(request.job_id)

    def status(self, job_id: UUID) -> NERStatusResponse:
        job = self._status.get_job(job_id)
        result = self._results.get_by_job(job_id)
        stage = str(job.get("current_stage") or "")
        progress = 70
        if stage == STAGE_NER:
            progress = 80
        elif stage == STAGE_RISK or (result and result.get("status") == "Completed"):
            progress = 90
        elif job.get("status") == "Failed":
            progress = 100

        return NERStatusResponse(
            job_id=job_id,
            status=str(job.get("status")),
            current_stage=stage,
            next_stage=STAGE_RISK,
            progress_pct=progress,
            ner_completed=bool(result),
            entity_count=(result or {}).get("entity_count"),
            confidence=float(result["confidence"])
            if result and result.get("confidence") is not None
            else None,
            error_message=job.get("error_message"),
            processing_job=ProcessingJobOut.model_validate(job),
        )

    def result(self, job_id: UUID) -> NERResultOut:
        row = self._results.get_by_job(job_id)
        if not row:
            raise HTTPException(
                status_code=404, detail="NER result not found for this job"
            )
        return NERResultOut.model_validate(row)

    def entities(self, job_id: UUID) -> List[MedicalEntityOut]:
        rows = self._entities.list_for_job(job_id)
        if rows:
            return [
                MedicalEntityOut(
                    id=UUID(str(r["id"])) if r.get("id") else None,
                    type=str(r.get("entity_type") or ""),
                    value=str(r.get("entity_value") or ""),
                    confidence=float(r.get("confidence") or 0),
                    source_document=r.get("source_document"),
                    page=int(r.get("page_number") or 1),
                    sentence=r.get("sentence"),
                    char_start=r.get("char_start"),
                    char_end=r.get("char_end"),
                    extraction_time=str(r.get("extraction_time") or ""),
                    metadata=r.get("metadata_json") or {},
                )
                for r in rows
            ]
        # Fallback to summary JSON
        result = self._results.get_by_job(job_id)
        if not result:
            raise HTTPException(status_code=404, detail="No entities found for this job")
        return [
            MedicalEntityOut.model_validate(e)
            for e in (result.get("entities_json") or [])
        ]


def get_intake_ner_service() -> NERService:
    return NERService()
