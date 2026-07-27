"""
Medical History Extraction — Intake Agent stage 2.

Collects and consolidates existing HMS data for a patient.
Does NOT analyze the newly uploaded document or run OCR.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from fastapi import HTTPException

from app.core.logging import get_logger
from app.repositories.intake_repositories import (
    AppointmentRepository,
    DepartmentRepository,
    DoctorRepository,
    DocumentProcessingJobRepository,
    MedicalDocumentRepository,
    MedicalRecordRepository,
    PatientAIContextRepository,
    PatientMedicalHistoryRepository,
    PatientRepository,
)
from app.schemas.medical_history import (
    MedicalHistoryResponse,
    PatientMedicalHistoryRecord,
    TimelineEvent,
    UnifiedMedicalHistory,
)
from app.schemas.registration import ProcessingJobOut

logger = get_logger("hospital_ai.intake.history")

STAGE_HISTORY = "Medical History Extraction"
STAGE_OCR = "OCR"
JOB_STATUS_PROCESSING = "Processing"

RECORD_TYPE_TO_EVENT = {
    "Consultation": "Diagnosis",
    "Prescription": "Prescription",
    "Lab Report": "Lab Report",
    "X-Ray": "Imaging",
    "MRI": "Imaging",
    "CT Scan": "Imaging",
    "Ultrasound": "Imaging",
    "Discharge Summary": "Discharge",
    "Vaccination": "Vaccination",
    "Other": "Procedure",
}


def _split_list(raw: Optional[str]) -> List[str]:
    if not raw or not str(raw).strip():
        return []
    text = str(raw).replace(";", ",").replace("\n", ",")
    return [p.strip() for p in text.split(",") if p.strip()]


def _norm_key(value: str) -> str:
    return " ".join(value.lower().split())


def _doctor_label(doctor: Optional[Dict[str, Any]]) -> Optional[str]:
    if not doctor:
        return None
    name = f"Dr. {doctor.get('first_name', '')} {doctor.get('last_name', '')}".strip()
    spec = doctor.get("specialization")
    if spec:
        return f"{name} ({spec})"
    return name or None


class MedicalHistoryExtractionService:
    """Intake Stage 2 — consolidate historical HMS data only."""

    def __init__(
        self,
        *,
        patients: Optional[PatientRepository] = None,
        appointments: Optional[AppointmentRepository] = None,
        records: Optional[MedicalRecordRepository] = None,
        documents: Optional[MedicalDocumentRepository] = None,
        doctors: Optional[DoctorRepository] = None,
        departments: Optional[DepartmentRepository] = None,
        contexts: Optional[PatientAIContextRepository] = None,
        jobs: Optional[DocumentProcessingJobRepository] = None,
        histories: Optional[PatientMedicalHistoryRepository] = None,
    ) -> None:
        self._patients = patients or PatientRepository()
        self._appointments = appointments or AppointmentRepository()
        self._records = records or MedicalRecordRepository()
        self._documents = documents or MedicalDocumentRepository()
        self._doctors = doctors or DoctorRepository()
        self._departments = departments or DepartmentRepository()
        self._contexts = contexts or PatientAIContextRepository()
        self._jobs = jobs or DocumentProcessingJobRepository()
        self._histories = histories or PatientMedicalHistoryRepository()

    # ------------------------------------------------------------------
    # Fetchers
    # ------------------------------------------------------------------

    def fetch_patient(self, patient_id: UUID) -> Dict[str, Any]:
        patient = self._patients.get_full(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        return patient

    def fetch_appointments(self, patient_id: UUID) -> List[Dict[str, Any]]:
        try:
            return self._appointments.list_for_patient(patient_id)
        except HTTPException:
            logger.warning("Failed to fetch appointments for patient=%s", patient_id)
            return []

    def fetch_medical_records(self, patient_id: UUID) -> List[Dict[str, Any]]:
        try:
            return self._records.list_for_patient(patient_id)
        except HTTPException:
            logger.warning("Failed to fetch medical records for patient=%s", patient_id)
            return []

    def fetch_doctors(self, doctor_ids: List[UUID]) -> List[Dict[str, Any]]:
        try:
            return self._doctors.get_many(doctor_ids)
        except HTTPException:
            logger.warning("Failed to fetch doctors ids=%s", doctor_ids)
            return []

    def fetch_departments(self, department_ids: List[UUID]) -> List[Dict[str, Any]]:
        try:
            return self._departments.get_many(department_ids)
        except HTTPException:
            logger.warning("Failed to fetch departments ids=%s", department_ids)
            return []

    def fetch_uploaded_documents(
        self, record_ids: List[UUID]
    ) -> List[Dict[str, Any]]:
        try:
            return self._documents.list_for_record_ids(record_ids)
        except HTTPException:
            logger.warning("Failed to fetch documents for records=%s", record_ids)
            return []

    def fetch_previous_ai_context(self, patient_id: UUID) -> Optional[Dict[str, Any]]:
        try:
            return self._contexts.get_by_patient(patient_id)
        except HTTPException:
            logger.warning("Failed to fetch AI context for patient=%s", patient_id)
            return None

    # ------------------------------------------------------------------
    # Transform helpers
    # ------------------------------------------------------------------

    def remove_duplicates(self, values: List[str]) -> List[str]:
        seen: Set[str] = set()
        out: List[str] = []
        for value in values:
            if not value or not str(value).strip():
                continue
            key = _norm_key(str(value))
            if key in seen:
                continue
            seen.add(key)
            out.append(str(value).strip())
        return out

    def sort_timeline(self, events: List[TimelineEvent]) -> List[TimelineEvent]:
        def sort_key(event: TimelineEvent) -> str:
            return event.date or ""

        # Chronological ascending (oldest → newest)
        return sorted(events, key=sort_key)

    def merge_medical_history(
        self,
        *,
        patient: Dict[str, Any],
        appointments: List[Dict[str, Any]],
        records: List[Dict[str, Any]],
        documents: List[Dict[str, Any]],
        doctors: List[Dict[str, Any]],
        departments: List[Dict[str, Any]],
        previous_ai_context: Optional[Dict[str, Any]],
        warnings: List[str],
    ) -> UnifiedMedicalHistory:
        doctor_map = {str(d["id"]): d for d in doctors if d.get("id")}
        dept_map = {str(d["id"]): d for d in departments if d.get("id")}

        allergies = self.remove_duplicates(_split_list(patient.get("allergies")))
        medications = self.remove_duplicates(
            _split_list(patient.get("current_medications"))
        )
        conditions: List[str] = []
        if patient.get("latest_diagnosis"):
            conditions.extend(_split_list(str(patient["latest_diagnosis"])))
        if patient.get("medical_history"):
            # Keep free-text history as a condition/note source
            conditions.append(str(patient["medical_history"]).strip())

        previous_diagnoses: List[str] = []
        previous_treatments: List[str] = []
        surgeries: List[str] = []
        lab_reports: List[Dict[str, Any]] = []
        timeline: List[TimelineEvent] = []
        seen_events: Set[str] = set()

        for appt in appointments:
            doctor = doctor_map.get(str(appt.get("doctor_id") or ""))
            dept = dept_map.get(str(appt.get("department_id") or ""))
            if not dept and doctor and doctor.get("department_id"):
                dept = dept_map.get(str(doctor["department_id"]))
            summary = (
                appt.get("reason_for_visit")
                or f"{appt.get('visit_type') or 'Visit'} — {appt.get('status')}"
            )
            ref = str(appt.get("id"))
            key = f"Appointment:{ref}"
            if key not in seen_events:
                seen_events.add(key)
                timeline.append(
                    TimelineEvent(
                        date=str(appt.get("appointment_date") or appt.get("created_at") or ""),
                        event_type="Appointment",
                        doctor=_doctor_label(doctor),
                        department=(dept or {}).get("name") if dept else None,
                        summary=str(summary),
                        reference_id=ref,
                    )
                )

        for record in records:
            doctor = doctor_map.get(str(record.get("doctor_id") or ""))
            dept_name = None
            if doctor and doctor.get("department_id"):
                dept = dept_map.get(str(doctor["department_id"]))
                dept_name = (dept or {}).get("name") if dept else None

            if record.get("diagnosis"):
                previous_diagnoses.extend(_split_list(str(record["diagnosis"])))
                conditions.append(str(record["diagnosis"]).strip())
            if record.get("treatment"):
                previous_treatments.extend(_split_list(str(record["treatment"])))
                # Heuristic: surgery-like treatments
                tx = str(record["treatment"]).lower()
                if any(w in tx for w in ("surgery", "surgical", "operation", "resection")):
                    surgeries.append(str(record["treatment"]).strip())

            record_type = str(record.get("record_type") or "Other")
            event_type = RECORD_TYPE_TO_EVENT.get(record_type, "Procedure")
            summary_parts = [
                record.get("title") or record_type,
                f"Dx: {record['diagnosis']}" if record.get("diagnosis") else None,
                f"Tx: {record['treatment']}" if record.get("treatment") else None,
            ]
            summary = " | ".join(p for p in summary_parts if p)

            ref = str(record.get("id"))
            key = f"{event_type}:{ref}"
            if key not in seen_events:
                seen_events.add(key)
                timeline.append(
                    TimelineEvent(
                        date=str(record.get("created_at") or "")[:10],
                        event_type=event_type,
                        doctor=_doctor_label(doctor),
                        department=dept_name,
                        summary=summary,
                        reference_id=ref,
                    )
                )

            if record_type == "Lab Report":
                lab_reports.append(
                    {
                        "id": ref,
                        "title": record.get("title"),
                        "diagnosis": record.get("diagnosis"),
                        "created_at": record.get("created_at"),
                        "doctor": _doctor_label(doctor),
                    }
                )

        reports = [
            {
                "id": str(d.get("id")),
                "medical_record_id": str(d.get("medical_record_id")),
                "file_name": d.get("file_name"),
                "file_type": d.get("file_type"),
                "file_size": d.get("file_size"),
                "file_url": d.get("file_url"),
                "created_at": d.get("created_at"),
            }
            for d in documents
        ]

        # Intake job uploads are historical context only (metadata), not OCR text
        # (current job file is metadata already on the job; EMR docs listed above)

        conditions = self.remove_duplicates(conditions)
        previous_diagnoses = self.remove_duplicates(previous_diagnoses)
        previous_treatments = self.remove_duplicates(previous_treatments)
        surgeries = self.remove_duplicates(surgeries)
        timeline = self.sort_timeline(timeline)

        appt_out = [
            {
                "id": str(a.get("id")),
                "appointment_number": a.get("appointment_number"),
                "date": a.get("appointment_date"),
                "status": a.get("status"),
                "visit_type": a.get("visit_type"),
                "reason": a.get("reason_for_visit"),
                "doctor_id": str(a.get("doctor_id")) if a.get("doctor_id") else None,
                "department_id": str(a.get("department_id"))
                if a.get("department_id")
                else None,
            }
            for a in appointments
        ]

        doctor_out = [
            {
                "id": str(d.get("id")),
                "doctor_number": d.get("doctor_number"),
                "name": f"{d.get('first_name', '')} {d.get('last_name', '')}".strip(),
                "specialization": d.get("specialization"),
                "department_id": str(d.get("department_id"))
                if d.get("department_id")
                else None,
            }
            for d in doctors
        ]
        dept_out = [
            {
                "id": str(d.get("id")),
                "name": d.get("name"),
                "description": d.get("description"),
                "floor_number": d.get("floor_number"),
            }
            for d in departments
        ]

        prev_ctx = None
        if previous_ai_context:
            prev_ctx = {
                "id": str(previous_ai_context.get("id")),
                "status": previous_ai_context.get("status"),
                "current_summary": previous_ai_context.get("current_summary"),
                "processing_job_id": previous_ai_context.get("processing_job_id"),
            }

        patient_overview = {
            "id": str(patient.get("id")),
            "patient_number": patient.get("patient_number"),
            "full_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
            "date_of_birth": patient.get("date_of_birth"),
            "gender": patient.get("gender"),
            "blood_group": patient.get("blood_group"),
            "phone": patient.get("phone"),
            "email": patient.get("email"),
            "city": patient.get("city"),
            "state": patient.get("state"),
            "country": patient.get("country"),
        }

        insurance = {
            "provider": patient.get("insurance_provider"),
            "number": patient.get("insurance_number"),
        }

        latest_summary = self._build_summary(
            patient_overview=patient_overview,
            allergies=allergies,
            conditions=conditions,
            medications=medications,
            appointments=appt_out,
            records_count=len(records),
            reports_count=len(reports),
            warnings=warnings,
        )

        return UnifiedMedicalHistory(
            patient=patient_overview,
            allergies=allergies,
            conditions=conditions,
            medications=medications,
            surgeries=surgeries,
            lab_reports=lab_reports,
            appointments=appt_out,
            reports=reports,
            doctors=doctor_out,
            departments=dept_out,
            insurance=insurance,
            previous_treatments=previous_treatments,
            previous_diagnoses=previous_diagnoses,
            previous_ai_context=prev_ctx,
            timeline=timeline,
            latest_summary=latest_summary,
            warnings=warnings,
        )

    def _build_summary(
        self,
        *,
        patient_overview: Dict[str, Any],
        allergies: List[str],
        conditions: List[str],
        medications: List[str],
        appointments: List[Dict[str, Any]],
        records_count: int,
        reports_count: int,
        warnings: List[str],
    ) -> str:
        parts = [
            f"History for {patient_overview.get('full_name')} "
            f"({patient_overview.get('patient_number')}).",
            f"{len(appointments)} appointment(s), {records_count} medical record(s), "
            f"{reports_count} uploaded report(s).",
        ]
        if allergies:
            parts.append(f"Allergies: {', '.join(allergies[:8])}.")
        if medications:
            parts.append(f"Medications: {', '.join(medications[:8])}.")
        if conditions:
            parts.append(f"Notable conditions/history: {', '.join(conditions[:5])}.")
        if warnings:
            parts.append("Warnings: " + "; ".join(warnings))
        return " ".join(parts)

    def generate_unified_history(
        self, history: UnifiedMedicalHistory
    ) -> Dict[str, Any]:
        return history.model_dump(mode="json")

    def save_medical_history(
        self,
        *,
        patient_id: UUID,
        processing_job_id: UUID,
        history: UnifiedMedicalHistory,
    ) -> Dict[str, Any]:
        payload = self.generate_unified_history(history)
        timeline = [e.model_dump(mode="json") for e in history.timeline]
        try:
            return self._histories.upsert(
                patient_id=patient_id,
                processing_job_id=processing_job_id,
                medical_history_json=payload,
                timeline_json=timeline,
            )
        except HTTPException as exc:
            logger.error("Corrupted / failed history save: %s", exc.detail)
            raise HTTPException(
                status_code=500,
                detail="Failed to save medical history (corrupted or unavailable storage)",
            ) from exc

    def _update_job_stage(self, job_id: UUID, *, current_stage: str) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "current_stage": current_stage,
            "status": JOB_STATUS_PROCESSING,
            "error_message": None,
        }
        if current_stage == STAGE_OCR:
            body["processing_started_at"] = datetime.utcnow().isoformat() + "Z"
        return self._jobs.update(job_id, body)

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def extract_for_job(self, job_id: UUID) -> MedicalHistoryResponse:
        job = self._jobs.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Processing job not found")

        patient_id = UUID(str(job["patient_id"]))
        logger.info(
            "Medical History Extraction start job=%s patient=%s",
            job_id,
            patient_id,
        )

        # Mark stage in progress
        self._jobs.update(
            job_id,
            {
                "current_stage": STAGE_HISTORY,
                "status": JOB_STATUS_PROCESSING,
                "processing_started_at": datetime.utcnow().isoformat() + "Z",
            },
        )

        warnings: List[str] = []
        patient = self.fetch_patient(patient_id)
        appointments = self.fetch_appointments(patient_id)
        records = self.fetch_medical_records(patient_id)

        if not appointments:
            warnings.append("Missing appointments: no appointment history found")
        if not records:
            warnings.append("No medical records found for this patient")

        doctor_ids: List[UUID] = []
        dept_ids: List[UUID] = []
        for a in appointments:
            if a.get("doctor_id"):
                doctor_ids.append(UUID(str(a["doctor_id"])))
            if a.get("department_id"):
                dept_ids.append(UUID(str(a["department_id"])))
        for r in records:
            if r.get("doctor_id"):
                doctor_ids.append(UUID(str(r["doctor_id"])))

        # Include job doctor
        if job.get("doctor_id"):
            doctor_ids.append(UUID(str(job["doctor_id"])))

        doctors = self.fetch_doctors(doctor_ids)
        for d in doctors:
            if d.get("department_id"):
                dept_ids.append(UUID(str(d["department_id"])))
        departments = self.fetch_departments(dept_ids)

        record_ids = [UUID(str(r["id"])) for r in records if r.get("id")]
        documents = self.fetch_uploaded_documents(record_ids)

        # Include registration upload metadata from the job itself
        if job.get("document_name"):
            documents = [
                {
                    "id": str(job.get("id")),
                    "medical_record_id": None,
                    "file_name": job.get("document_name"),
                    "file_url": job.get("file_url"),
                    "file_type": job.get("document_type"),
                    "file_size": job.get("file_size"),
                    "created_at": job.get("created_at"),
                    "source": "intake_registration",
                },
                *documents,
            ]

        previous_ai_context = self.fetch_previous_ai_context(patient_id)

        history = self.merge_medical_history(
            patient=patient,
            appointments=appointments,
            records=records,
            documents=documents,
            doctors=doctors,
            departments=departments,
            previous_ai_context=previous_ai_context,
            warnings=warnings,
        )

        saved = self.save_medical_history(
            patient_id=patient_id,
            processing_job_id=job_id,
            history=history,
        )

        # Advance job to next stage marker (OCR) — do not run OCR here
        self._update_job_stage(job_id, current_stage=STAGE_OCR)
        updated_job = self._jobs.get_by_id(job_id) or job

        # Refresh AI context summary shell
        try:
            self._contexts.upsert_for_patient(
                patient_id=patient_id,
                processing_job_id=job_id,
                status="Pending",
                current_summary=history.latest_summary,
            )
        except HTTPException:
            logger.warning("Could not update patient AI context after history extraction")

        logger.info(
            "Medical History Extraction complete job=%s next_stage=%s warnings=%s",
            job_id,
            STAGE_OCR,
            len(warnings),
        )

        return MedicalHistoryResponse(
            patient_id=patient_id,
            processing_job=ProcessingJobOut.model_validate(updated_job or job),
            medical_history=history,
            timeline=history.timeline,
            current_stage=STAGE_OCR,
            next_stage="OCR",
            warnings=warnings,
            history_record=PatientMedicalHistoryRecord.model_validate(saved),
        )

    def get_history(self, patient_id: UUID) -> MedicalHistoryResponse:
        """Return stored history + latest job stage (does not re-extract)."""
        # Verify patient exists
        self.fetch_patient(patient_id)

        job = self._jobs.latest_for_patient(patient_id)
        saved = self._histories.get_by_patient(patient_id)

        if not saved:
            return MedicalHistoryResponse(
                patient_id=patient_id,
                processing_job=ProcessingJobOut.model_validate(job) if job else None,
                medical_history=None,
                timeline=[],
                current_stage=(job or {}).get("current_stage")
                or "Patient Registration",
                next_stage=STAGE_HISTORY,
                warnings=["No medical history extracted yet. Run extraction first."],
                history_record=None,
            )

        history_json = saved.get("medical_history_json") or {}
        try:
            history = UnifiedMedicalHistory.model_validate(history_json)
        except Exception as exc:  # noqa: BLE001
            logger.error("Corrupted history for patient=%s: %s", patient_id, exc)
            raise HTTPException(
                status_code=500,
                detail="Corrupted medical history data",
            ) from exc

        timeline_raw = saved.get("timeline_json") or history.timeline
        timeline = [
            TimelineEvent.model_validate(t) if not isinstance(t, TimelineEvent) else t
            for t in timeline_raw
        ]

        current_stage = (job or {}).get("current_stage") or STAGE_HISTORY
        return MedicalHistoryResponse(
            patient_id=patient_id,
            processing_job=ProcessingJobOut.model_validate(job) if job else None,
            medical_history=history,
            timeline=timeline,
            current_stage=str(current_stage),
            next_stage="OCR",
            warnings=list(history.warnings or []),
            history_record=PatientMedicalHistoryRecord.model_validate(saved),
        )


def get_medical_history_extraction_service() -> MedicalHistoryExtractionService:
    return MedicalHistoryExtractionService()
