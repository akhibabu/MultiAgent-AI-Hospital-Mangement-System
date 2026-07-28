"""
Diagnosis Agent — sequential pipeline.

Patient Context -> Load Knowledge Graph -> Validate ->
1. Symptom Analysis -> 2. Differential Diagnosis -> 3. Disease Probability
Scoring -> 4. Severity Prediction -> 5. Treatment Path Recommendation ->
6. Clinical Decision Support.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.diagnosis.clinical_decision_support import ClinicalDecisionSupportGenerator
from app.ai.diagnosis.differential_engine import DifferentialDiagnosisEngine
from app.ai.diagnosis.factory import (
    DiagnosisStrategyFactory,
    get_diagnosis_strategy_factory,
)
from app.ai.diagnosis.models import DiagnosisReport
from app.ai.diagnosis.probability_scorer import DiseaseProbabilityScorer
from app.ai.diagnosis.severity_predictor import SeverityPredictor
from app.ai.diagnosis.symptom_analyzer import SymptomAnalyzer
from app.ai.diagnosis.treatment_path import TreatmentPathRecommender
from app.core.logging import get_logger
from app.repositories.patient_context_repository import (
    PatientClinicalContextRepository,
)

logger = get_logger("hospital_ai.diagnosis.pipeline")


class DiagnosisPipeline:
    """Orchestrates the six-stage Diagnosis Agent pipeline."""

    def __init__(
        self,
        *,
        context_repo: Optional[PatientClinicalContextRepository] = None,
        strategy_factory: Optional[DiagnosisStrategyFactory] = None,
        probability_scorer: Optional[DiseaseProbabilityScorer] = None,
        severity_predictor: Optional[SeverityPredictor] = None,
        treatment_path_recommender: Optional[TreatmentPathRecommender] = None,
        cds_generator: Optional[ClinicalDecisionSupportGenerator] = None,
    ) -> None:
        self._context_repo = context_repo or PatientClinicalContextRepository()
        self._factory = strategy_factory or get_diagnosis_strategy_factory()
        self._symptom_analyzer = SymptomAnalyzer(self._factory.create_symptom_strategy())
        self._differential_engine = DifferentialDiagnosisEngine(
            self._factory.create_differential_strategy()
        )
        self._probability_scorer = probability_scorer or DiseaseProbabilityScorer(
            self._factory.knowledge_base()
        )
        self._severity_predictor = severity_predictor or SeverityPredictor()
        self._treatment_path_recommender = (
            treatment_path_recommender
            or TreatmentPathRecommender(self._factory.knowledge_base())
        )
        self._cds_generator = cds_generator or ClinicalDecisionSupportGenerator()

    def run(
        self,
        patient_id: UUID,
        *,
        chief_complaint: Optional[str] = None,
        focus_symptoms: Optional[List[str]] = None,
    ) -> DiagnosisReport:
        # Load Patient Context -> Load Knowledge Graph
        context = self._context_repo.load(patient_id)

        # Validate Patient Information
        if not context.patient_id:
            raise HTTPException(status_code=404, detail="Patient not found")

        if focus_symptoms:
            merged = list(dict.fromkeys(context.symptoms + list(focus_symptoms)))
            context = context.model_copy(update={"symptoms": merged})

        # 1. Symptom Analysis
        symptom_analysis = self._symptom_analyzer.analyze(context)

        # 2. Differential Diagnosis
        differentials = self._differential_engine.generate(context, symptom_analysis)

        # 3. Disease Probability Scoring
        probabilities = self._probability_scorer.score(context, differentials)

        # 4. Severity Prediction
        top_weight = 0.0
        if differentials:
            profile = self._factory.knowledge_base().get(differentials[0].condition)
            top_weight = profile.severity_weight if profile else 0.0
        severity = self._severity_predictor.predict(context, top_weight)

        # 5. Treatment Path Recommendation
        treatment_path = self._treatment_path_recommender.recommend(differentials, severity)

        # 6. Clinical Decision Support
        cds = self._cds_generator.generate(
            context, symptom_analysis, differentials, probabilities, severity, treatment_path
        )

        top_condition = probabilities[0].condition if probabilities else None
        summary = ClinicalDecisionSupportGenerator.build_summary(
            len(probabilities), top_condition, severity.level
        )

        warnings = list(context.validation_warnings)
        if not differentials:
            warnings.append(
                "No matching conditions found in the rule-based knowledge base — "
                "consider direct clinical evaluation."
            )

        logger.info(
            "Diagnosis pipeline complete patient=%s conditions=%s severity=%s",
            patient_id,
            len(probabilities),
            severity.level,
        )

        return DiagnosisReport(
            patient_id=str(patient_id),
            chief_complaint=chief_complaint,
            focus_symptoms=list(focus_symptoms or []),
            symptom_analysis=symptom_analysis,
            differential_diagnoses=differentials,
            probability_scores=probabilities,
            severity_assessment=severity,
            treatment_path=treatment_path,
            clinical_decision_support=cds,
            summary=summary,
            engine=self._factory.engine_name,
            warnings=warnings,
        )
