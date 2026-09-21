"""Emergency Agent — six-stage deterministic pipeline."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.emergency.alert_generator import EmergencyAlertGenerator
from app.ai.emergency.critical_event_detector import CriticalEventDetector
from app.ai.emergency.icu_predictor import ICURequirementPredictor
from app.ai.emergency.models import EmergencyReport
from app.ai.emergency.priority_ranker import PatientPriorityRanker
from app.ai.emergency.triage_classifier import EmergencyTriageClassifier
from app.ai.emergency.vital_monitor import VitalMonitor
from app.core.logging import get_logger
from app.repositories.patient_context_repository import PatientClinicalContextRepository

logger = get_logger("hospital_ai.emergency.pipeline")


class EmergencyPipeline:
    """Run the Emergency Agent from shared Intake Patient Context."""

    def __init__(
        self,
        *,
        context_repo: Optional[PatientClinicalContextRepository] = None,
        vital_monitor: Optional[VitalMonitor] = None,
        triage_classifier: Optional[EmergencyTriageClassifier] = None,
        event_detector: Optional[CriticalEventDetector] = None,
        icu_predictor: Optional[ICURequirementPredictor] = None,
        alert_generator: Optional[EmergencyAlertGenerator] = None,
        priority_ranker: Optional[PatientPriorityRanker] = None,
    ) -> None:
        self._context_repo = context_repo or PatientClinicalContextRepository()
        self._vital_monitor = vital_monitor or VitalMonitor()
        self._triage = triage_classifier or EmergencyTriageClassifier()
        self._events = event_detector or CriticalEventDetector()
        self._icu = icu_predictor or ICURequirementPredictor()
        self._alerts = alert_generator or EmergencyAlertGenerator()
        self._priority = priority_ranker or PatientPriorityRanker()

    def run(self, patient_id: UUID) -> EmergencyReport:
        context = self._context_repo.load(patient_id)

        if not context.patient_id:
            raise HTTPException(status_code=404, detail="Patient not found")

        monitoring = self._vital_monitor.monitor(context.vitals)

        events = self._events.detect(
            conditions=context.conditions,
            symptoms=context.symptoms,
            monitoring=monitoring,
            risk_level=context.risk_overall_level,
            risk_alerts=context.risk_alerts,
        )

        triage = self._triage.classify(
            monitoring=monitoring,
            events=events,
            risk_score=context.risk_overall_score,
            risk_level=context.risk_overall_level,
        )

        icu = self._icu.predict(
            monitoring=monitoring,
            events=events,
            risk_score=context.risk_overall_score,
            risk_level=context.risk_overall_level,
        )

        alerts = self._alerts.generate(
            monitoring=monitoring,
            triage=triage,
            events=events,
            icu=icu,
        )

        priority = self._priority.rank(
            triage=triage,
            monitoring=monitoring,
            events=events,
            icu_signal=icu.signal,
        )

        warnings = list(context.validation_warnings)
        if not context.vitals:
            warnings.append("No vital signs are available in the current Intake Patient Context.")
        if not context.risk_overall_level:
            warnings.append(
                "No Intake risk level is available; Emergency scoring is based on current signals only."
            )

        summary = self._summary(
            context.patient_name,
            triage.category,
            triage.score,
            events.detected_event_count,
            icu.signal,
            alerts.alert_count,
        )

        logger.info(
            "Emergency pipeline complete patient=%s triage=%s score=%s events=%s icu=%s",
            patient_id,
            triage.category,
            triage.score,
            events.detected_event_count,
            icu.signal,
        )

        return EmergencyReport(
            patient_id=str(patient_id),
            patient_name=context.patient_name,
            status="Completed",
            vital_monitoring=monitoring,
            triage_classification=triage,
            critical_event_detection=events,
            icu_requirement=icu,
            emergency_alerts=alerts,
            patient_priority=priority,
            summary=summary,
            warnings=warnings,
        )

    @staticmethod
    def _summary(
        patient_name: str,
        triage: str,
        triage_score: float,
        event_count: int,
        icu_signal: str,
        alert_count: int,
    ) -> str:
        return (
            f"{patient_name}: Emergency Agent classified the current snapshot as "
            f"{triage} (acuity score {triage_score}/100), detected {event_count} "
            f"event signal(s), assigned an ICU requirement signal of {icu_signal}, "
            f"and generated {alert_count} in-application alert(s)."
        )
