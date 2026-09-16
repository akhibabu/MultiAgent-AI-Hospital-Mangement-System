"""
Canonical Medical Report Agent validation tasks.
"""

from __future__ import annotations

from typing import Dict, List

MEDICAL_REPORT_TASKS: List[Dict[str, str]] = [
    {
        "task_id": "medical_report_clinical_summary",
        "slug": "clinical_summary",
        "label": "Clinical Summary",
        "alias": "clinical_summary",
        "validator": "HumanReviewValidator",
        "validatable": "false",
        "primary_metric": "",
    },
    {
        "task_id": "medical_report_doctor_notes_generation",
        "slug": "doctor_notes_generation",
        "label": "Doctor Notes Generation",
        "alias": "doctor_notes_generation",
        "validator": "NotValidatableValidator",
        "validatable": "false",
        "primary_metric": "",
    },
    {
        "task_id": "medical_report_discharge_summary",
        "slug": "discharge_summary",
        "label": "Discharge Summary",
        "alias": "discharge_summary",
        "validator": "HumanReviewValidator",
        "validatable": "false",
        "primary_metric": "",
    },
    {
        "task_id": "medical_report_referral_letter_creation",
        "slug": "referral_letter_creation",
        "label": "Referral Letter Creation",
        "alias": "referral_letter_creation",
        "validator": "NotValidatableValidator",
        "validatable": "false",
        "primary_metric": "",
    },
    {
        "task_id": "medical_report_insurance_documentation",
        "slug": "insurance_documentation",
        "label": "Insurance Documentation",
        "alias": "insurance_documentation",
        "validator": "InsuranceDocumentationValidator",
        "validatable": "true",
        "primary_metric": "recall",
    },
    {
        "task_id": "medical_report_patient_report_generation",
        "slug": "patient_report_generation",
        "label": "Patient Report Generation",
        "alias": "patient_report_generation",
        "validator": "NotValidatableValidator",
        "validatable": "false",
        "primary_metric": "",
    },
]

MEDICAL_REPORT_TASK_IDS = [item["task_id"] for item in MEDICAL_REPORT_TASKS]

_ALIAS_TO_ID: Dict[str, str] = {}
for _item in MEDICAL_REPORT_TASKS:
    _ALIAS_TO_ID[_item["task_id"]] = _item["task_id"]
    _ALIAS_TO_ID[_item["alias"]] = _item["task_id"]
    _ALIAS_TO_ID[_item["slug"]] = _item["task_id"]
    _ALIAS_TO_ID[_item["label"].lower().replace(" ", "_")] = _item["task_id"]


def is_medical_report_agent(value: str | None) -> bool:
    if not value:
        return False
    cleaned = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    return cleaned in {"medical_report", "medical_report_agent"}


def resolve_medical_report_task(value: str) -> str:
    cleaned = str(value).strip()
    if cleaned.upper() in {"ALL", "*"}:
        return "ALL"
    key = cleaned.lower().replace(" ", "_").replace("-", "_")
    if key in _ALIAS_TO_ID:
        return _ALIAS_TO_ID[key]
    if key in MEDICAL_REPORT_TASK_IDS:
        return key
    return cleaned


def resolve_medical_report_tasks(values: List[str]) -> List[str]:
    resolved: List[str] = []
    for value in values:
        item = resolve_medical_report_task(value)
        if item == "ALL":
            return list(MEDICAL_REPORT_TASK_IDS)
        resolved.append(item)
    return resolved


def task_meta(task_id: str) -> Dict[str, str]:
    for item in MEDICAL_REPORT_TASKS:
        if item["task_id"] == task_id:
            return item
    return {
        "task_id": task_id,
        "slug": task_id.replace("medical_report_", ""),
        "label": task_id,
        "alias": task_id,
        "validator": "",
        "validatable": "false",
        "primary_metric": "",
    }
