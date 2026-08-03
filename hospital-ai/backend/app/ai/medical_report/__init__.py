"""Medical Report Agent — professional hospital documentation.

Generates Clinical Summary, Doctor Notes, Discharge Summary, Referral
Letter, Insurance Documentation, and a plain-language Patient Report from
every previous AI Agent's output. Assists — never replaces — clinician
review and sign-off.
"""

from app.ai.medical_report.models import (
    ClinicalSummary,
    DischargeSummary,
    DoctorNotes,
    InsuranceDocumentation,
    MedicalReportBundle,
    PatientReport,
    ReferralLetter,
)
from app.ai.medical_report.pipeline import MedicalReportPipeline

__all__ = [
    "ClinicalSummary",
    "DischargeSummary",
    "DoctorNotes",
    "InsuranceDocumentation",
    "MedicalReportBundle",
    "MedicalReportPipeline",
    "PatientReport",
    "ReferralLetter",
]
