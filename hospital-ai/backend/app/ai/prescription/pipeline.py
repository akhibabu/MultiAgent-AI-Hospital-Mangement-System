"""
Prescription Agent — sequential pipeline.

Diagnosis Results + Research Findings + Patient Context + Knowledge Graph ->
1. Medication Selection -> 2. Drug Interaction Check -> 3. Allergy
Verification -> 4. Dosage Optimization -> 5. Treatment Plan Creation ->
6. Prescription Validation.

Never replaces a physician. Never generates a final prescription.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.prescription.allergy_verifier import AllergyVerifier
from app.ai.prescription.dosage_optimizer import DosageOptimizer
from app.ai.prescription.factory import (
    PrescriptionStrategyFactory,
    get_prescription_strategy_factory,
)
from app.ai.prescription.interaction_checker import DrugInteractionChecker
from app.ai.prescription.models import PrescriptionReport
from app.ai.prescription.prescription_validator import PrescriptionValidator
from app.ai.prescription.treatment_plan_builder import TreatmentPlanBuilder
from app.core.logging import get_logger
from app.repositories.diagnosis_repository import DiagnosisResultRepository
from app.repositories.patient_context_repository import (
    PatientClinicalContextRepository,
)
from app.repositories.research_repository import ResearchResultRepository

logger = get_logger("hospital_ai.prescription.pipeline")

_MAX_TARGET_CONDITIONS = 3


class PrescriptionPipeline:
    """Orchestrates the six-stage Prescription Agent pipeline."""

    def __init__(
        self,
        *,
        context_repo: Optional[PatientClinicalContextRepository] = None,
        diagnosis_repo: Optional[DiagnosisResultRepository] = None,
        research_repo: Optional[ResearchResultRepository] = None,
        strategy_factory: Optional[PrescriptionStrategyFactory] = None,
        interaction_checker: Optional[DrugInteractionChecker] = None,
        allergy_verifier: Optional[AllergyVerifier] = None,
        dosage_optimizer: Optional[DosageOptimizer] = None,
        treatment_plan_builder: Optional[TreatmentPlanBuilder] = None,
        validator: Optional[PrescriptionValidator] = None,
    ) -> None:
        self._context_repo = context_repo or PatientClinicalContextRepository()
        self._diagnosis_repo = diagnosis_repo or DiagnosisResultRepository()
        self._research_repo = research_repo or ResearchResultRepository()
        self._factory = strategy_factory or get_prescription_strategy_factory()
        self._selector = self._factory.create_medication_selector()
        self._interaction_checker = interaction_checker or DrugInteractionChecker(
            self._factory.knowledge_base()
        )
        self._allergy_verifier = allergy_verifier or AllergyVerifier(self._factory.knowledge_base())
        self._dosage_optimizer = dosage_optimizer or DosageOptimizer(self._factory.knowledge_base())
        self._treatment_plan_builder = treatment_plan_builder or TreatmentPlanBuilder(
            self._factory.knowledge_base()
        )
        self._validator = validator or PrescriptionValidator()

    def run(
        self,
        patient_id: UUID,
        *,
        diagnosis_result_id: Optional[UUID] = None,
        research_result_id: Optional[UUID] = None,
    ) -> PrescriptionReport:
        context = self._context_repo.load(patient_id)
        if not context.patient_id:
            raise HTTPException(status_code=404, detail="Patient not found")

        diagnosis_row = self._load_diagnosis(patient_id, diagnosis_result_id)
        research_row = self._load_research(patient_id, research_result_id, diagnosis_row)

        warnings: List[str] = list(context.validation_warnings)
        if not diagnosis_row:
            warnings.append(
                "No Diagnosis Agent result found for this patient — run the Diagnosis "
                "Agent first for medication recommendations grounded in a differential diagnosis."
            )

        target_conditions = self._target_conditions(diagnosis_row) or context.conditions[:_MAX_TARGET_CONDITIONS]
        severity_level = ((diagnosis_row or {}).get("severity_assessment_json") or {}).get("level")
        treatment_path = (diagnosis_row or {}).get("treatment_path_json") or {}
        research_by_condition = self._research_by_condition(research_row)

        current_drugs = [
            str(m.get("name")) if isinstance(m, dict) else str(m)
            for m in context.medications
            if (m.get("name") if isinstance(m, dict) else m)
        ]

        if not target_conditions:
            warnings.append(
                "No target conditions available — complete the Diagnosis Agent or ensure "
                "Patient Context includes recognized conditions before running Prescription."
            )

        # 1. Medication Selection
        medications = self._selector.select(context, target_conditions, research_by_condition)
        suggested_drugs = [m.medication_name for m in medications]

        # 2. Drug Interaction Check
        interactions = self._interaction_checker.check(current_drugs, suggested_drugs)

        # 3. Allergy Verification
        allergy_checks = self._allergy_verifier.verify(context.allergies, suggested_drugs)

        # 4. Dosage Optimization
        dosages = self._dosage_optimizer.optimize(context, suggested_drugs, severity_level)

        # 5. Treatment Plan Creation
        treatment_plan = self._treatment_plan_builder.build(
            target_conditions=target_conditions,
            medications=medications,
            allergy_checks=allergy_checks,
            dosages=dosages,
            severity_level=severity_level,
            diagnosis_specialists=treatment_path.get("recommended_specialists"),
            diagnosis_tests=treatment_path.get("diagnostic_tests"),
            diagnosis_imaging=treatment_path.get("imaging"),
        )

        # 6. Prescription Validation
        validation = self._validator.validate(
            current_drugs=current_drugs,
            medications=medications,
            interactions=interactions,
            allergy_checks=allergy_checks,
            dosages=dosages,
        )

        summary = self._build_summary(target_conditions, medications, validation)

        logger.info(
            "Prescription pipeline complete patient=%s medications=%s approval=%s",
            patient_id,
            len(medications),
            validation.approval_status,
        )

        return PrescriptionReport(
            patient_id=str(patient_id),
            diagnosis_result_id=str(diagnosis_row["id"]) if diagnosis_row else None,
            research_result_id=str(research_row["id"]) if research_row else None,
            target_conditions=target_conditions,
            medication_recommendations=medications,
            drug_interactions=interactions,
            allergy_checks=allergy_checks,
            dosage_recommendations=dosages,
            treatment_plan=treatment_plan,
            validation=validation,
            summary=summary,
            engine=self._factory.engine_name,
            warnings=warnings,
        )

    def _load_diagnosis(
        self, patient_id: UUID, diagnosis_result_id: Optional[UUID]
    ) -> Optional[Dict[str, Any]]:
        if diagnosis_result_id:
            row = self._diagnosis_repo.get_by_id(diagnosis_result_id)
            if not row:
                raise HTTPException(status_code=404, detail="Diagnosis result not found")
            return row
        return self._diagnosis_repo.get_latest_for_patient(patient_id)

    def _load_research(
        self,
        patient_id: UUID,
        research_result_id: Optional[UUID],
        diagnosis_row: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if research_result_id:
            rows = self._research_repo.list_for_patient(patient_id, limit=100)
            for row in rows:
                if str(row.get("id")) == str(research_result_id):
                    return row
            raise HTTPException(status_code=404, detail="Research result not found")
        return self._research_repo.get_latest_for_patient(patient_id)

    @staticmethod
    def _target_conditions(diagnosis_row: Optional[Dict[str, Any]]) -> List[str]:
        if not diagnosis_row:
            return []
        probs = diagnosis_row.get("probability_scores_json") or []
        conditions = [p.get("condition") for p in probs if isinstance(p, dict) and p.get("condition")]
        return conditions[:_MAX_TARGET_CONDITIONS]

    @staticmethod
    def _research_by_condition(
        research_row: Optional[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        if not research_row:
            return {}
        recs = research_row.get("recommendation_json") or []
        return {
            r.get("condition"): r
            for r in recs
            if isinstance(r, dict) and r.get("condition")
        }

    @staticmethod
    def _build_summary(
        target_conditions: List[str],
        medications: List[Any],
        validation: Any,
    ) -> str:
        if not target_conditions:
            return (
                "No target conditions were available for medication recommendation. "
                "Run the Diagnosis Agent first."
            )
        cond_text = ", ".join(target_conditions)
        return (
            f"Prescription Agent reviewed {cond_text} and suggested {len(medications)} "
            f"medication(s). Validation status: {validation.approval_status} "
            f"(confidence {round(validation.confidence_score * 100)}%). Physician review required."
        )
