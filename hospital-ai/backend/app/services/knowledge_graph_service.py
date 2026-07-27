"""
Patient Knowledge Graph Pipeline — Intake Agent Stage 6 (final).

Builds the portable knowledge graph consumed by downstream AI agents.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.knowledge_graph.builder import KnowledgeGraphBuilder, knowledge_graph_builder
from app.ai.ner.extractor import (
    ExtractedMedicalEntities,
    LabValueEntity,
    MedicationEntity,
    VitalEntity,
)
from app.core.logging import get_logger
from app.repositories.intake_repositories import (
    PatientAIContextRepository,
    PatientMedicalHistoryRepository,
)
from app.repositories.knowledge_graph_repository import (
    KnowledgeGraphContextUpdater,
    KnowledgeGraphStatusUpdater,
    PatientKnowledgeGraphRepository,
)
from app.repositories.ner_repository import MedicalEntityResultRepository
from app.repositories.risk_repository import PatientRiskProfileRepository
from app.schemas.knowledge_graph import (
    GraphNodeOut,
    GraphRelationshipOut,
    KnowledgeGraphOut,
    KnowledgeGraphStartRequest,
    KnowledgeGraphStartResponse,
    KnowledgeGraphStatusResponse,
)
from app.schemas.registration import ProcessingJobOut

logger = get_logger("hospital_ai.intake.kg")

STAGE_KG = "Patient Knowledge Graph"
STAGE_COMPLETED = "Completed"
STAGE_RISK = "Patient Risk Profiling"


class KnowledgeGraphPipeline:
    """Assemble context → build graph → persist → mark Intake complete."""

    def __init__(
        self,
        *,
        status_updater: Optional[KnowledgeGraphStatusUpdater] = None,
        context_updater: Optional[KnowledgeGraphContextUpdater] = None,
        graph_repo: Optional[PatientKnowledgeGraphRepository] = None,
        ner_results: Optional[MedicalEntityResultRepository] = None,
        risk_repo: Optional[PatientRiskProfileRepository] = None,
        builder: Optional[KnowledgeGraphBuilder] = None,
    ) -> None:
        self._status = status_updater or KnowledgeGraphStatusUpdater()
        self._context = context_updater or KnowledgeGraphContextUpdater()
        self._graphs = graph_repo or PatientKnowledgeGraphRepository()
        self._ner_results = ner_results or MedicalEntityResultRepository()
        self._risk_repo = risk_repo or PatientRiskProfileRepository()
        self._builder = builder or knowledge_graph_builder
        self._histories = PatientMedicalHistoryRepository()
        self._contexts = PatientAIContextRepository()

    def _entities_from_context(
        self, patient_id: UUID, job_id: UUID
    ) -> ExtractedMedicalEntities:
        ner = self._ner_results.get_by_job(job_id)
        if ner:
            summary = ner.get("summary_json") or {}
            flat = ner.get("entities_json") or []
            return self._from_payload(
                {"summary": summary, "entities": flat, "confidence": ner.get("confidence")}
            )

        ctx_row = self._contexts.get_by_patient(patient_id)
        if ctx_row and isinstance(ctx_row.get("patient_context_json"), dict):
            ctx = ctx_row["patient_context_json"]
            if ctx.get("ner_result"):
                return self._from_payload(ctx["ner_result"])
            return ExtractedMedicalEntities(
                diseases=list(ctx.get("recognized_diseases") or []),
                symptoms=list(ctx.get("recognized_symptoms") or []),
                allergies=list(ctx.get("recognized_allergies") or []),
                medications=[
                    MedicationEntity(
                        name=str(m.get("name") if isinstance(m, dict) else m),
                        dosage=(m.get("dosage") if isinstance(m, dict) else None),
                        frequency=(m.get("frequency") if isinstance(m, dict) else None),
                    )
                    for m in (ctx.get("recognized_medications") or [])
                ],
                vitals=[
                    VitalEntity(
                        name=str(v.get("name") if isinstance(v, dict) else "Vital"),
                        value=str(v.get("value") if isinstance(v, dict) else v),
                        unit=(v.get("unit") if isinstance(v, dict) else None),
                    )
                    for v in (ctx.get("recognized_vitals") or [])
                ],
                procedures=list(ctx.get("recognized_procedures") or []),
                lab_tests=list(ctx.get("recognized_tests") or []),
            )

        raise HTTPException(
            status_code=422,
            detail=(
                "No recognized entities available. "
                "Complete Medical Entity Recognition before Knowledge Graph."
            ),
        )

    def _from_payload(self, payload: Dict[str, Any]) -> ExtractedMedicalEntities:
        summary = payload.get("summary") or {}
        flat = payload.get("entities") or []
        diseases = list(summary.get("conditions") or [])
        symptoms = list(summary.get("symptoms") or [])
        allergies = list(summary.get("allergies") or [])
        procedures = list(summary.get("recent_procedures") or [])
        lab_tests = list(summary.get("recent_tests") or [])
        doctors = list(summary.get("doctors") or [])
        hospitals = list(summary.get("hospitals") or [])
        follow_ups = list(summary.get("follow_up") or [])
        medications = [
            MedicationEntity(
                name=str(m.get("name") or ""),
                dosage=m.get("dosage"),
                frequency=m.get("frequency"),
            )
            for m in (summary.get("current_medications") or [])
            if isinstance(m, dict) and m.get("name")
        ]
        vitals = [
            VitalEntity(
                name=str(v.get("name") or "Vital"),
                value=str(v.get("value") or ""),
                unit=v.get("unit"),
            )
            for v in (summary.get("vitals") or [])
            if isinstance(v, dict)
        ]
        labs: List[LabValueEntity] = []
        for e in flat:
            if not isinstance(e, dict):
                continue
            et, val = str(e.get("type") or ""), str(e.get("value") or "")
            if not val:
                continue
            if et == "Disease" and val not in diseases:
                diseases.append(val)
            elif et == "Symptom" and val not in symptoms:
                symptoms.append(val)
            elif et == "Allergy" and val not in allergies:
                allergies.append(val)
            elif et == "Medication" and not any(
                m.name.lower() == val.lower() for m in medications
            ):
                meta = e.get("metadata") or {}
                medications.append(
                    MedicationEntity(name=val, dosage=meta.get("dosage"))
                )
            elif et == "Vital":
                meta = e.get("metadata") or {}
                vitals.append(
                    VitalEntity(
                        name=str(meta.get("name") or val.split(":")[0]),
                        value=str(meta.get("value") or val),
                        unit=meta.get("unit"),
                    )
                )
            elif et == "Lab Value":
                meta = e.get("metadata") or {}
                labs.append(
                    LabValueEntity(
                        name=str(meta.get("name") or val),
                        value=str(meta.get("value") or ""),
                        unit=meta.get("unit"),
                    )
                )
            elif et == "Doctor" and val not in doctors:
                doctors.append(val)
            elif et == "Hospital" and val not in hospitals:
                hospitals.append(val)

        return ExtractedMedicalEntities(
            diseases=diseases,
            symptoms=symptoms,
            medications=medications,
            allergies=allergies,
            vitals=vitals,
            lab_values=labs,
            lab_tests=lab_tests,
            procedures=procedures,
            doctor_names=doctors,
            hospital_names=hospitals,
            follow_up_dates=follow_ups,
            confidence=float(payload.get("confidence") or 0.7),
            source="ner_context",
        )

    def _age_years(self, history: Optional[Dict[str, Any]]) -> Optional[int]:
        if not history:
            return None
        patient = history.get("patient") or {}
        dob = patient.get("date_of_birth")
        if not dob or not isinstance(dob, str):
            return None
        try:
            y, m, d = [int(x) for x in dob[:10].split("-")]
            born = date(y, m, d)
            today = date.today()
            return today.year - born.year - (
                (today.month, today.day) < (born.month, born.day)
            )
        except (ValueError, TypeError):
            return None

    def run(self, job_id: UUID) -> KnowledgeGraphStartResponse:
        job = self._status.get_job(job_id)
        patient_id = UUID(str(job["patient_id"]))
        stage = str(job.get("current_stage") or "")

        if stage in {
            "Patient Registration",
            "Medical History Extraction",
            "OCR",
            "Medical Entity Recognition",
        }:
            raise HTTPException(
                status_code=400,
                detail="Complete Patient Risk Profiling before Knowledge Graph",
            )

        self._status.mark_kg_running(job_id)
        started = time.perf_counter()

        try:
            entities = self._entities_from_context(patient_id, job_id)
            history_row = self._histories.get_by_patient(patient_id)
            history_json = (
                (history_row or {}).get("medical_history_json")
                if history_row
                else None
            )
            timeline = (history_row or {}).get("timeline_json") if history_row else []

            ctx_row = self._contexts.get_by_patient(patient_id)
            ctx: Dict[str, Any] = {}
            if ctx_row and isinstance(ctx_row.get("patient_context_json"), dict):
                ctx = ctx_row["patient_context_json"]
                if not history_json:
                    history_json = ctx.get("medical_history")
                if not timeline:
                    timeline = ctx.get("timeline") or []

            risk_row = self._risk_repo.get_by_job(job_id)
            risk_payload: Dict[str, Any] = {}
            if risk_row:
                risk_payload = {
                    "overall_level": risk_row.get("overall_level"),
                    "overall_score": risk_row.get("overall_score"),
                    "top_risk_factors": risk_row.get("top_risk_factors_json") or [],
                }
            elif ctx.get("risk_profile"):
                risk_payload = ctx["risk_profile"]
            elif ctx.get("overall_risk"):
                risk_payload = {
                    **ctx["overall_risk"],
                    "top_risk_factors": ctx.get("risk_factors") or [],
                }

            patient_label = "Patient"
            if isinstance(history_json, dict):
                p = history_json.get("patient") or {}
                patient_label = (
                    p.get("full_name")
                    or " ".join(
                        filter(None, [p.get("first_name"), p.get("last_name")])
                    )
                    or patient_label
                )

            existing = self._graphs.get_by_job(job_id) or self._graphs.get_latest_for_patient(
                patient_id
            )
            next_version = int((existing or {}).get("graph_version") or 0) + 1

            graph = self._builder.build(
                patient_id=str(patient_id),
                patient_label=patient_label,
                entities=entities,
                risk=risk_payload,
                medical_history=history_json
                if isinstance(history_json, dict)
                else None,
                timeline=timeline if isinstance(timeline, list) else None,
                appointment_ids=[str(job.get("appointment_id"))]
                if job.get("appointment_id")
                else None,
                document_name=str(job.get("document_name") or "") or None,
                graph_version=next_version,
                age_years=self._age_years(
                    history_json if isinstance(history_json, dict) else None
                ),
            )

            elapsed_ms = int((time.perf_counter() - started) * 1000)
            stored = self._builder.serialize(graph)
            stats = stored.get("statistics") or {}
            node_count = len(graph.nodes)
            rel_count = len(graph.edges)

            row = self._graphs.upsert_for_job(
                job_id,
                {
                    "patient_id": str(patient_id),
                    "nodes_json": stored.get("nodes") or [],
                    "relationships_json": stored.get("relationships") or [],
                    "statistics_json": stats,
                    "patient_summary_json": stored.get("patient_summary") or {},
                    "summary": graph.summary,
                    "graph_version": graph.graph_version,
                    "node_count": node_count,
                    "relationship_count": rel_count,
                    "builder_logs_json": stored.get("builder_logs") or [],
                    "validation_json": stored.get("validation") or {},
                    "status": "Completed",
                    "error_message": None,
                    "processing_time_ms": elapsed_ms,
                },
            )

            context_row = self._context.append_graph(
                patient_id=patient_id,
                processing_job_id=job_id,
                graph_payload=stored,
                node_count=node_count,
                relationship_count=rel_count,
                graph_version=graph.graph_version,
            )

            self._status.mark_intake_complete(job_id)
            job_out = self._status.get_job(job_id)

            warnings: List[str] = []
            validation = graph.validation or {}
            if validation.get("warnings"):
                warnings.extend([str(w) for w in validation["warnings"][:5]])
            if not validation.get("valid"):
                warnings.append("Graph validation reported issues — review in Developer Mode.")

            logger.info(
                "Knowledge graph complete job=%s nodes=%s rels=%s version=%s",
                job_id,
                node_count,
                rel_count,
                graph.graph_version,
            )

            return KnowledgeGraphStartResponse(
                job_id=job_id,
                patient_id=patient_id,
                status=str(job_out.get("status") or "Completed"),
                current_stage=STAGE_COMPLETED,
                next_stage=STAGE_COMPLETED,
                intake_completed=True,
                node_count=node_count,
                relationship_count=rel_count,
                graph_version=graph.graph_version,
                processing_time_ms=elapsed_ms,
                summary=graph.summary or "",
                statistics=stats,
                patient_summary=stored.get("patient_summary") or {},
                nodes=[GraphNodeOut.model_validate(n.model_dump()) for n in graph.nodes],
                relationships=[
                    GraphRelationshipOut.model_validate(e.model_dump())
                    for e in graph.edges
                ],
                warnings=warnings,
                knowledge_graph=KnowledgeGraphOut.model_validate(row),
                processing_job=ProcessingJobOut.model_validate(job_out),
                patient_context_version=int(context_row.get("context_version") or 1),
            )
        except HTTPException as exc:
            self._status.mark_kg_failed(job_id, str(exc.detail))
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Knowledge graph pipeline failed job=%s", job_id)
            self._status.mark_kg_failed(job_id, str(exc))
            raise HTTPException(
                status_code=500, detail=f"Knowledge Graph creation failed: {exc}"
            ) from exc


class KnowledgeGraphService:
    """Facade for Stage 6 — Dependency Injection entrypoint."""

    def __init__(self, pipeline: Optional[KnowledgeGraphPipeline] = None) -> None:
        self._pipeline = pipeline or KnowledgeGraphPipeline()
        self._graphs = PatientKnowledgeGraphRepository()
        self._status = KnowledgeGraphStatusUpdater()

    def start(self, request: KnowledgeGraphStartRequest) -> KnowledgeGraphStartResponse:
        return self._pipeline.run(request.job_id)

    def status(self, job_id: UUID) -> KnowledgeGraphStatusResponse:
        job = self._status.get_job(job_id)
        result = self._graphs.get_by_job(job_id)
        stage = str(job.get("current_stage") or "")
        completed = bool(result) or stage == STAGE_COMPLETED or job.get("status") == "Completed"
        progress = 95
        if stage == STAGE_KG:
            progress = 97
        if completed:
            progress = 100

        return KnowledgeGraphStatusResponse(
            job_id=job_id,
            status=str(job.get("status")),
            current_stage=stage,
            next_stage=STAGE_COMPLETED if not completed else STAGE_COMPLETED,
            progress_pct=progress,
            kg_completed=bool(result),
            intake_completed=completed,
            node_count=(result or {}).get("node_count"),
            relationship_count=(result or {}).get("relationship_count"),
            error_message=job.get("error_message"),
            processing_job=ProcessingJobOut.model_validate(job),
        )

    def result(self, job_id: UUID) -> KnowledgeGraphOut:
        row = self._graphs.get_by_job(job_id)
        if not row:
            raise HTTPException(
                status_code=404, detail="Knowledge graph not found for this job"
            )
        return KnowledgeGraphOut.model_validate(row)

    def result_for_patient(self, patient_id: UUID) -> KnowledgeGraphOut:
        row = self._graphs.get_latest_for_patient(patient_id)
        if not row:
            raise HTTPException(
                status_code=404, detail="Knowledge graph not found for this patient"
            )
        return KnowledgeGraphOut.model_validate(row)


def get_intake_knowledge_graph_service() -> KnowledgeGraphService:
    return KnowledgeGraphService()
