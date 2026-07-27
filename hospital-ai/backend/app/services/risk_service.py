"""
Patient Risk Profiling Pipeline — Intake Agent Stage 5.

Estimates risk from NER entities + history. Decision-support only.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.ner.extractor import (
    ExtractedMedicalEntities,
    LabValueEntity,
    MedicationEntity,
    MedicalEntityRecognizer,
    VitalEntity,
    medical_entity_recognizer,
)
from app.ai.risk.profiler import RiskProfiler, risk_profiler
from app.core.logging import get_logger
from app.repositories.intake_repositories import (
    PatientAIContextRepository,
    PatientMedicalHistoryRepository,
)
from app.repositories.ner_repository import MedicalEntityResultRepository
from app.repositories.risk_repository import (
    PatientRiskProfileRepository,
    RiskContextUpdater,
    RiskStatusUpdater,
)
from app.schemas.registration import ProcessingJobOut
from app.schemas.risk import (
    CategoryRiskOut,
    RiskAlertOut,
    RiskProfileOut,
    RiskStartRequest,
    RiskStartResponse,
    RiskStatusResponse,
)

logger = get_logger("hospital_ai.intake.risk")

STAGE_RISK = "Patient Risk Profiling"
STAGE_KG = "Patient Knowledge Graph"
STAGE_NER = "Medical Entity Recognition"


class RiskPipeline:
    """Load NER + history → assess risk → persist → update context → KG marker."""

    def __init__(
        self,
        *,
        status_updater: Optional[RiskStatusUpdater] = None,
        context_updater: Optional[RiskContextUpdater] = None,
        risk_repo: Optional[PatientRiskProfileRepository] = None,
        ner_results: Optional[MedicalEntityResultRepository] = None,
        profiler: Optional[RiskProfiler] = None,
        recognizer: Optional[MedicalEntityRecognizer] = None,
    ) -> None:
        self._status = status_updater or RiskStatusUpdater()
        self._context = context_updater or RiskContextUpdater()
        self._risk_repo = risk_repo or PatientRiskProfileRepository()
        self._ner_results = ner_results or MedicalEntityResultRepository()
        self._profiler = profiler or risk_profiler
        self._recognizer = recognizer or medical_entity_recognizer
        self._histories = PatientMedicalHistoryRepository()
        self._contexts = PatientAIContextRepository()

    def _entities_from_context(
        self, patient_id: UUID, job_id: UUID
    ) -> ExtractedMedicalEntities:
        ner = self._ner_results.get_by_job(job_id)
        if ner and ner.get("entities_json"):
            return self._entities_from_ner_row(ner)

        ctx_row = self._contexts.get_by_patient(patient_id)
        if ctx_row and isinstance(ctx_row.get("patient_context_json"), dict):
            ctx = ctx_row["patient_context_json"]
            ner_payload = ctx.get("ner_result") or {}
            if ner_payload.get("entities") or ner_payload.get("summary"):
                return self._entities_from_payload(ner_payload)
            # Rebuild from recognized_* convenience keys
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
                "No recognized medical entities available. "
                "Complete Medical Entity Recognition before Risk Profiling."
            ),
        )

    def _entities_from_ner_row(self, ner: Dict[str, Any]) -> ExtractedMedicalEntities:
        summary = ner.get("summary_json") or {}
        entities = ner.get("entities_json") or []
        return self._entities_from_payload(
            {"summary": summary, "entities": entities, "statistics": ner.get("statistics_json")}
        )

    def _entities_from_payload(self, payload: Dict[str, Any]) -> ExtractedMedicalEntities:
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

        # Enrich from flat entity list if summary sparse
        if not diseases or not medications:
            for e in flat:
                if not isinstance(e, dict):
                    continue
                et = str(e.get("type") or "")
                val = str(e.get("value") or "")
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
                        MedicationEntity(
                            name=val,
                            dosage=meta.get("dosage"),
                            frequency=None,
                        )
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
                    lab_tests.append(val)

        labs: List[LabValueEntity] = []
        # Parse lab values from flat entities
        for e in flat:
            if isinstance(e, dict) and e.get("type") == "Lab Value":
                meta = e.get("metadata") or {}
                labs.append(
                    LabValueEntity(
                        name=str(meta.get("name") or e.get("value") or ""),
                        value=str(meta.get("value") or ""),
                        unit=meta.get("unit"),
                    )
                )

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
            entities=[],
            confidence=float((payload.get("confidence") or 0.7)),
            source="ner_context",
        )

    def _age_years(self, history: Optional[Dict[str, Any]]) -> Optional[int]:
        if not history:
            return None
        patient = history.get("patient") or {}
        dob = patient.get("date_of_birth")
        if not dob:
            return None
        try:
            if isinstance(dob, str):
                y, m, d = [int(x) for x in dob[:10].split("-")]
                born = date(y, m, d)
            else:
                return None
            today = date.today()
            return today.year - born.year - (
                (today.month, today.day) < (born.month, born.day)
            )
        except (ValueError, TypeError):
            return None

    def run(self, job_id: UUID) -> RiskStartResponse:
        job = self._status.get_job(job_id)
        patient_id = UUID(str(job["patient_id"]))
        stage = str(job.get("current_stage") or "")

        allowed = {STAGE_RISK, STAGE_KG, STAGE_NER}
        # NER advances to Risk; allow retry from Risk or KG
        if stage in {
            "Patient Registration",
            "Medical History Extraction",
            "OCR",
        }:
            raise HTTPException(
                status_code=400,
                detail="Complete Medical Entity Recognition before Risk Profiling",
            )
        if stage == STAGE_NER:
            # Job still at NER marker — entities should exist; allow run
            pass
        elif stage not in allowed and stage != STAGE_RISK:
            # Also allow if already at Risk
            if stage != STAGE_RISK:
                pass

        self._status.mark_risk_running(job_id)
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
            if ctx_row and isinstance(ctx_row.get("patient_context_json"), dict):
                ctx = ctx_row["patient_context_json"]
                if not timeline:
                    timeline = ctx.get("timeline") or []
                if not history_json:
                    history_json = ctx.get("medical_history")

            age = self._age_years(
                history_json if isinstance(history_json, dict) else None
            )
            allergies = None
            if isinstance(history_json, dict):
                allergies = history_json.get("allergies")

            assessment = self._profiler.assess(
                entities,
                allergies=allergies,
                age_years=age,
                medical_history=history_json
                if isinstance(history_json, dict)
                else None,
                timeline=timeline if isinstance(timeline, list) else None,
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            payload = assessment.to_dict()

            row = self._risk_repo.upsert_for_job(
                job_id,
                {
                    "patient_id": str(patient_id),
                    "overall_level": assessment.overall_level,
                    "overall_score": assessment.overall_score,
                    "overall_confidence": assessment.overall_confidence,
                    "categories_json": [c.to_dict() for c in assessment.categories],
                    "top_risk_factors_json": assessment.top_risk_factors,
                    "important_findings_json": assessment.important_findings,
                    "alerts_json": [a.model_dump() for a in assessment.alerts],
                    "distribution_json": assessment.distribution,
                    "timeline_json": assessment.timeline,
                    "disclaimer": assessment.disclaimer,
                    "processing_time_ms": elapsed_ms,
                    "status": "Completed",
                    "error_message": None,
                },
            )

            context_row = self._context.append_risk(
                patient_id=patient_id,
                processing_job_id=job_id,
                risk_payload=payload,
                overall_level=assessment.overall_level,
                overall_score=assessment.overall_score,
                confidence=assessment.overall_confidence,
            )

            self._status.mark_risk_complete(job_id)
            job_out = self._status.get_job(job_id)

            warnings: List[str] = []
            if assessment.overall_level in {"High", "Critical"}:
                warnings.append(
                    f"Overall risk is {assessment.overall_level}. "
                    "This is decision-support only — clinician review required."
                )

            logger.info(
                "Risk profiling complete job=%s level=%s score=%.1f",
                job_id,
                assessment.overall_level,
                assessment.overall_score,
            )

            return RiskStartResponse(
                job_id=job_id,
                patient_id=patient_id,
                status=str(job_out.get("status") or "Processing"),
                current_stage=STAGE_KG,
                next_stage=STAGE_KG,
                overall_level=assessment.overall_level,
                overall_score=assessment.overall_score,
                overall_confidence=assessment.overall_confidence,
                processing_time_ms=elapsed_ms,
                categories=[
                    CategoryRiskOut.model_validate(c.to_dict())
                    for c in assessment.categories
                ],
                top_risk_factors=assessment.top_risk_factors,
                important_findings=assessment.important_findings,
                alerts=[
                    RiskAlertOut.model_validate(a.model_dump())
                    for a in assessment.alerts
                ],
                distribution=assessment.distribution,
                timeline=assessment.timeline,
                disclaimer=assessment.disclaimer,
                warnings=warnings,
                risk_profile=RiskProfileOut.model_validate(row),
                processing_job=ProcessingJobOut.model_validate(job_out),
                patient_context_version=int(context_row.get("context_version") or 1),
            )
        except HTTPException as exc:
            self._status.mark_risk_failed(job_id, str(exc.detail))
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Risk pipeline failed job=%s", job_id)
            self._status.mark_risk_failed(job_id, str(exc))
            raise HTTPException(
                status_code=500, detail=f"Patient Risk Profiling failed: {exc}"
            ) from exc


class RiskService:
    """Facade for Stage 5 — Dependency Injection entrypoint."""

    def __init__(self, pipeline: Optional[RiskPipeline] = None) -> None:
        self._pipeline = pipeline or RiskPipeline()
        self._risk_repo = PatientRiskProfileRepository()
        self._status = RiskStatusUpdater()

    def start(self, request: RiskStartRequest) -> RiskStartResponse:
        return self._pipeline.run(request.job_id)

    def status(self, job_id: UUID) -> RiskStatusResponse:
        job = self._status.get_job(job_id)
        result = self._risk_repo.get_by_job(job_id)
        stage = str(job.get("current_stage") or "")
        progress = 80
        if stage == STAGE_RISK:
            progress = 88
        elif stage == STAGE_KG or (result and result.get("status") == "Completed"):
            progress = 95
        elif job.get("status") == "Failed":
            progress = 100

        return RiskStatusResponse(
            job_id=job_id,
            status=str(job.get("status")),
            current_stage=stage,
            next_stage=STAGE_KG,
            progress_pct=progress,
            risk_completed=bool(result),
            overall_level=(result or {}).get("overall_level"),
            overall_score=float(result["overall_score"])
            if result and result.get("overall_score") is not None
            else None,
            error_message=job.get("error_message"),
            processing_job=ProcessingJobOut.model_validate(job),
        )

    def result(self, job_id: UUID) -> RiskProfileOut:
        row = self._risk_repo.get_by_job(job_id)
        if not row:
            raise HTTPException(
                status_code=404, detail="Risk profile not found for this job"
            )
        return RiskProfileOut.model_validate(row)


def get_intake_risk_service() -> RiskService:
    return RiskService()
