"""Intake Agent pipelines — Document Upload → OCR → NER → Risk → KG → Context."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.ai.intake.patient_context import PatientContext, PatientIdentity
from app.ai.knowledge_graph import PatientKnowledgeGraph, knowledge_graph_builder
from app.ai.ner.extractor import ExtractedMedicalEntities, medical_entity_recognizer
from app.ai.orchestrator import AIOrchestratorError, get_orchestrator
from app.ai.ocr.providers import OCRResult, get_ocr_provider
from app.ai.risk.profiler import PatientRiskProfile, risk_profiler
from app.core.logging import get_logger

logger = get_logger("hospital_ai.intake.pipelines")


class DocumentUploadPipeline:
    """Validate patient / appointment / doctor and record upload metadata intent."""

    def validate_registration(
        self,
        *,
        patient_exists: bool,
        appointment_exists: bool,
        doctor_exists: bool,
        require_appointment: bool = False,
        require_doctor: bool = False,
    ) -> None:
        if not patient_exists:
            raise ValueError("Patient does not exist")
        if require_appointment and not appointment_exists:
            raise ValueError("Appointment does not exist")
        if require_doctor and not doctor_exists:
            raise ValueError("Doctor does not exist")
        # Soft warnings when optional FKs missing
        if not appointment_exists:
            logger.info("Intake upload without appointment linkage")
        if not doctor_exists:
            logger.info("Intake upload without doctor linkage")


class OCRPipeline:
    """Only Intake Agent may invoke document text extraction on raw uploads."""

    def run(
        self,
        *,
        file_bytes: bytes,
        content_type: str,
        file_name: str,
    ):
        from app.ai.ocr.base import Provenance, now_iso

        # Default provider (stub) delegates to DocumentProcessingService —
        # embedded PDF text or Tesseract OCR; never raw PDF bytes.
        provider = get_ocr_provider()
        logger.info("Document extract via provider=%s file=%s", provider.name, file_name)
        provenance = Provenance(
            source_document=file_name,
            file_name=file_name,
            document_type=content_type,
            page_number=1,
            ocr_provider=provider.name,
            extraction_time=now_iso(),
            confidence_score=0.0,
            processing_job_id="legacy",
        )
        result = provider.run(
            file_bytes=file_bytes,
            content_type=content_type,
            file_name=file_name,
            provenance=provenance,
        )
        result.text = result.raw_text  # type: ignore[attr-defined]
        return result



class EntityExtractionPipeline:
    def run(self, ocr_text: str) -> ExtractedMedicalEntities:
        entities = medical_entity_recognizer.extract(ocr_text)
        # Optional LLM enrichment (non-authoritative; rule NER remains source
        # of truth). Routed entirely through the AI Orchestrator — this
        # pipeline never talks to Groq/Ollama/etc. directly, and a failure
        # here (e.g. the provider being unreachable) never blocks Intake.
        try:
            get_orchestrator().run(
                agent="intake",
                task="entity_enrichment",
                patient_id=None,
                use_cache=True,
                use_memory=False,
                extra_vars={
                    "recognized_entities": entities.model_dump(mode="json"),
                    "source_text": ocr_text[:4000],
                },
            )
        except AIOrchestratorError as exc:
            logger.warning("LLM enrichment skipped (AI Orchestrator unavailable): %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM enrichment skipped: %s", exc)
        return entities


class RiskProfilingPipeline:
    def run(
        self,
        entities: ExtractedMedicalEntities,
        *,
        allergies: Optional[List[str]] = None,
        age_years: Optional[int] = None,
    ) -> PatientRiskProfile:
        return risk_profiler.profile(
            entities, allergies=allergies, age_years=age_years
        )


class KnowledgeGraphBuilderPipeline:
    def run(
        self,
        *,
        patient_id: str,
        patient_label: str,
        entities: ExtractedMedicalEntities,
        risk: PatientRiskProfile,
        doctor_ids: Optional[List[str]] = None,
        appointment_ids: Optional[List[str]] = None,
        medical_record_ids: Optional[List[str]] = None,
    ) -> PatientKnowledgeGraph:
        return knowledge_graph_builder.build(
            patient_id=patient_id,
            patient_label=patient_label,
            entities=entities,
            risk=risk,
            doctor_ids=doctor_ids,
            appointment_ids=appointment_ids,
            medical_record_ids=medical_record_ids,
        )


class PatientContextBuilderPipeline:
    """Assemble the sole Patient Context JSON for downstream agents."""

    def build(
        self,
        *,
        patient: Dict[str, Any],
        history_text: str,
        entities: ExtractedMedicalEntities,
        risk: PatientRiskProfile,
        graph: PatientKnowledgeGraph,
        source_document_ids: List[str],
        source_job_ids: List[str],
        graph_db_id: Optional[str] = None,
    ) -> PatientContext:
        allergies = sorted(
            set(
                (patient.get("allergies") or "").replace(";", ",").split(",")
                if isinstance(patient.get("allergies"), str)
                else []
            )
            | set(entities.allergies)
        )
        allergies = [a.strip() for a in allergies if a and a.strip()]

        confidence = round(
            (entities.confidence * 0.6)
            + (0.2 if history_text else 0)
            + (0.2 if graph.nodes else 0),
            4,
        )
        confidence = min(0.99, confidence)

        return PatientContext(
            patient=PatientIdentity(
                id=str(patient["id"]),
                patient_number=patient.get("patient_number"),
                full_name=f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                date_of_birth=str(patient.get("date_of_birth") or "") or None,
                gender=patient.get("gender"),
                blood_group=patient.get("blood_group"),
            ),
            medical_history=history_text,
            current_symptoms=entities.symptoms,
            conditions=entities.diseases,
            medications=entities.medications,
            allergies=allergies,
            lab_results=entities.lab_values,
            vitals=entities.vitals,
            procedures=entities.procedures,
            medical_codes=entities.medical_codes,
            risk_profile=risk,
            knowledge_graph_references={
                "graph_id": graph_db_id,
                "node_count": len(graph.nodes),
                "edge_count": len(graph.edges),
                "summary": graph.summary,
            },
            source_document_ids=source_document_ids,
            source_job_ids=source_job_ids,
            confidence_score=confidence,
            entities=entities,
        )


def compute_age_years(dob: Optional[str]) -> Optional[int]:
    if not dob:
        return None
    try:
        born = date.fromisoformat(str(dob)[:10])
        today = date.today()
        return today.year - born.year - (
            (today.month, today.day) < (born.month, born.day)
        )
    except ValueError:
        return None


document_upload_pipeline = DocumentUploadPipeline()
ocr_pipeline = OCRPipeline()
entity_extraction_pipeline = EntityExtractionPipeline()
risk_profiling_pipeline = RiskProfilingPipeline()
knowledge_graph_builder_pipeline = KnowledgeGraphBuilderPipeline()
patient_context_builder_pipeline = PatientContextBuilderPipeline()
