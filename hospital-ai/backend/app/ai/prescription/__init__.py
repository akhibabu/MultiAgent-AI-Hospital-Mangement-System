"""Prescription Agent — physician-review treatment recommendations.

Never replaces a physician. Never generates a final prescription. Consumes
Diagnosis Agent + Research Agent output plus Patient Context and Knowledge
Graph.
"""

from app.ai.prescription.factory import PrescriptionStrategyFactory
from app.ai.prescription.models import (
    AllergyCheckItem,
    DosageRecommendation,
    DrugInteraction,
    MedicationRecommendation,
    PrescriptionReport,
    PrescriptionValidation,
    TreatmentPlan,
)
from app.ai.prescription.pipeline import PrescriptionPipeline

__all__ = [
    "AllergyCheckItem",
    "DosageRecommendation",
    "DrugInteraction",
    "MedicationRecommendation",
    "PrescriptionPipeline",
    "PrescriptionReport",
    "PrescriptionStrategyFactory",
    "PrescriptionValidation",
    "TreatmentPlan",
]
