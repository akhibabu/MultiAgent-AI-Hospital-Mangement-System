"""Cross-agent scheduling context.

Reads the latest persisted results from Diagnosis, Emergency, Prescription,
and Medical Report. Scheduling does not ask the patient to choose treatment,
surgery, doctor, department, or visit type.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.repositories.diagnosis_repository import DiagnosisResultRepository
from app.repositories.emergency_repository import EmergencyResultRepository
from app.repositories.medical_report_repository import GeneratedMedicalReportRepository
from app.repositories.prescription_repository import PrescriptionResultRepository

NEGATIVE_SURGERY = re.compile(
    r"(?:no|not|without|does not|doesn't|do not|don't)s+"
    r"(?:requires+|recommends+|needs+)?(?:fors+)?"
    r"(?:surgery|surgical intervention|operation|operative procedure)",
    re.IGNORECASE,
)
SURGERY_LANGUAGE = re.compile(
    r"(?:(?:recommend(?:ed)?|require(?:d)?|need(?:s|ed)?|plan(?:ned)?|"
    r"schedule(?:d)?|indicat(?:e|ed|es)).{0,100}"
    r"(?:surgery|surgical intervention|operation|operative procedure))|"
    r"(?:(?:surgery|surgical intervention|operation|operative procedure)"
    r".{0,100}(?:recommend(?:ed)?|require(?:d)?|needed|planned|"
    r"schedule(?:d)?|indicat(?:e|ed|es)))",
    re.IGNORECASE | re.DOTALL,
)


class SchedulingSourceContext:
    def __init__(self) -> None:
        self.diagnosis = DiagnosisResultRepository()
        self.emergency = EmergencyResultRepository()
        self.prescription = PrescriptionResultRepository()
        self.medical_report = GeneratedMedicalReportRepository()

    def load(self, patient_id: UUID) -> Dict[str, Any]:
        return {
            "diagnosis": self.diagnosis.get_latest_for_patient(patient_id),
            "emergency": self.emergency.get_latest_for_patient(patient_id),
            "prescription": self.prescription.get_latest_for_patient(patient_id),
            "medical_report": self.medical_report.get_latest_for_patient(patient_id),
        }

    @staticmethod
    def derive(source: Dict[str, Any]) -> Dict[str, Any]:
        diagnosis = source.get("diagnosis") or {}
        emergency = source.get("emergency") or {}
        prescription = source.get("prescription") or {}
        report = source.get("medical_report") or {}

        treatment_path = diagnosis.get("treatment_path_json") or {}
        cds = diagnosis.get("clinical_decision_support_json") or {}
        severity = diagnosis.get("severity_assessment_json") or {}
        treatment_plan = prescription.get("treatment_plan_json") or {}
        validation = prescription.get("validation_summary_json") or {}
        doctor_notes = report.get("doctor_notes_json") or {}
        referral = report.get("referral_letter_json") or {}
        patient_report = report.get("patient_report_json") or {}
        discharge = report.get("discharge_summary_json") or {}

        priority = emergency.get("patient_priority_json") or {}
        triage = emergency.get("triage_classification_json") or {}
        icu = emergency.get("icu_requirement_json") or {}

        diagnosis_surgery = bool(treatment_path.get("surgery_required"))
        prescription_surgery = bool(treatment_plan.get("surgery_required"))

        diagnosis_procedures = _unique(
            treatment_path.get("recommended_procedures") or []
        )
        prescription_procedures = _unique(
            treatment_plan.get("procedure_recommendations") or []
        )
        procedures = _unique([*diagnosis_procedures, *prescription_procedures])

        evidence = _surgery_evidence(
            [
                ("Diagnosis Treatment Path", treatment_path.get("notes")),
                ("Diagnosis Clinical Notes", cds.get("clinical_notes")),
                ("Prescription Emergency Advice", treatment_plan.get("emergency_advice")),
                ("Medical Report Doctor Plan", doctor_notes.get("plan")),
                ("Medical Report Referral", referral.get("requested_evaluation")),
            ]
        )

        surgery_required = diagnosis_surgery or prescription_surgery or bool(evidence)
        surgery_conflict = (
            "surgery_required=false" in {str(x).strip().lower() for x in []}
            and False
        )
        # Detect an explicit structured disagreement, without allowing prose
        # from a generic report to override a structured recommendation.
        structured_flags = []
        if "surgery_required" in treatment_path:
            structured_flags.append(("Diagnosis", diagnosis_surgery))
        if "surgery_required" in treatment_plan:
            structured_flags.append(("Prescription", prescription_surgery))
        surgery_conflict = (
            len(structured_flags) >= 2
            and len({flag for _, flag in structured_flags}) > 1
        )

        duration = _first_duration(
            treatment_path.get("estimated_duration_minutes"),
            treatment_plan.get("estimated_duration_minutes"),
        )

        priority_level = str(priority.get("priority_level") or "").strip() or "Routine"
        priority_score = _number(priority.get("priority_score"))
        triage_category = str(triage.get("category") or "").strip() or None
        urgency = str(treatment_path.get("urgency") or "").strip() or "Routine"

        follow_up_text = (
            str(treatment_plan.get("follow_up_interval") or "").strip()
            or str(patient_report.get("follow_up") or "").strip()
            or str(discharge.get("follow_up") or "").strip()
        )

        if (
            priority_level in {"Critical", "Urgent"}
            or triage_category in {"Critical", "Urgent"}
            or urgency in {"Critical", "Urgent", "Emergency"}
        ):
            visit_type = "Emergency"
        elif follow_up_text:
            visit_type = "Follow Up"
        else:
            visit_type = "Consultation"

        specialists = _unique(
            [
                *(treatment_path.get("recommended_specialists") or []),
                *(treatment_plan.get("recommended_specialists") or []),
                referral.get("receiving_specialist") or "",
            ]
        )
        department = (
            str(treatment_path.get("recommended_department") or "").strip() or None
        )

        recommended_tests = _unique(
            [
                *(treatment_path.get("diagnostic_tests") or []),
                *(treatment_plan.get("recommended_lab_tests") or []),
            ]
        )
        recommended_imaging = _unique(
            [
                *(treatment_path.get("imaging") or []),
                *(treatment_plan.get("recommended_imaging") or []),
            ]
        )
        medications = _unique(treatment_plan.get("medication_plan") or [])

        treatment_modes: List[str] = []
        if medications:
            treatment_modes.append("Medication")
        if recommended_tests:
            treatment_modes.append("Diagnostic Testing")
        if recommended_imaging:
            treatment_modes.append("Imaging")
        if procedures or surgery_required:
            treatment_modes.append("Procedure/Surgery")
        if treatment_plan.get("monitoring_plan") or doctor_notes.get("plan"):
            treatment_modes.append("Monitoring")
        if follow_up_text:
            treatment_modes.append("Follow-up")

        clinical_parts = [
            *_strings(diagnosis.get("target_conditions_json")),
            *_strings(diagnosis.get("differential_diagnoses_json"), "condition"),
            *_strings(cds.get("possible_diagnoses")),
            treatment_path.get("recommended_department") or "",
            *diagnosis_procedures,
            *procedures,
            *recommended_tests,
            *recommended_imaging,
            *medications,
            doctor_notes.get("assessment") or "",
            doctor_notes.get("plan") or "",
            report.get("summary") or "",
        ]

        return {
            "source_ids": {
                "diagnosis_result_id": _id(diagnosis),
                "emergency_result_id": _id(emergency),
                "prescription_result_id": _id(prescription),
                "medical_report_result_id": _id(report),
            },
            "sources_available": {
                "diagnosis": bool(diagnosis),
                "emergency": bool(emergency),
                "prescription": bool(prescription),
                "medical_report": bool(report),
            },
            "department": department,
            "specialists": specialists,
            "visit_type": visit_type,
            "emergency_priority_level": priority_level,
            "emergency_priority_score": priority_score,
            "emergency_triage": triage_category,
            "icu_signal": str(icu.get("signal") or "Low"),
            "severity_level": str(severity.get("level") or "").strip() or None,
            "urgency": urgency,
            "clinical_text": " ".join(str(x) for x in clinical_parts if x).strip(),
            "surgery_required": surgery_required,
            "surgery_conflict": surgery_conflict,
            "surgery_sources": {
                "diagnosis": diagnosis_surgery,
                "prescription": prescription_surgery,
                "medical_report_explicit_text": bool(evidence),
            },
            "surgery_evidence": evidence,
            "procedures": procedures,
            "surgery_duration_minutes": duration,
            "follow_up_text": follow_up_text,
            "recommended_tests": recommended_tests,
            "recommended_imaging": recommended_imaging,
            "medications": medications,
            "treatment_modes": treatment_modes,
            "validation_status": str(validation.get("approval_status") or "").strip() or None,
        }


def _surgery_evidence(items: List[tuple[str, Any]]) -> List[str]:
    evidence: List[str] = []
    for source_name, value in items:
        values = value if isinstance(value, list) else [value]
        for raw in values:
            text = str(raw or "").strip()
            if not text or NEGATIVE_SURGERY.search(text):
                continue
            match = SURGERY_LANGUAGE.search(text)
            if match:
                evidence.append(f"{source_name}: {match.group(0).strip()[:300]}")
    return evidence[:6]


def _strings(value: Any, key: Optional[str] = None) -> List[str]:
    if not isinstance(value, list):
        return []
    result: List[str] = []
    for item in value:
        if key and isinstance(item, dict):
            item = item.get(key)
        if item is not None and str(item).strip():
            result.append(str(item).strip())
    return result


def _unique(values: List[Any]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if text and text.lower() not in seen:
            result.append(text)
            seen.add(text.lower())
    return result


def _number(value: Any) -> float:
    try:
        return round(float(value or 0), 1)
    except (TypeError, ValueError):
        return 0.0


def _first_duration(*values: Any) -> int:
    for value in values:
        try:
            number = int(float(value))
        except (TypeError, ValueError):
            continue
        if 30 <= number <= 480:
            return number
    return 0


def _id(row: Dict[str, Any]) -> str | None:
    return str(row.get("id")) if row.get("id") else None
