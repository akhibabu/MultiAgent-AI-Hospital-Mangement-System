from app.ai.emergency.alert_generator import EmergencyAlertGenerator
from app.ai.emergency.critical_event_detector import CriticalEventDetector
from app.ai.emergency.icu_predictor import ICURequirementPredictor
from app.ai.emergency.priority_ranker import PatientPriorityRanker
from app.ai.emergency.triage_classifier import EmergencyTriageClassifier
from app.ai.emergency.vital_monitor import VitalMonitor


def test_vital_monitor_detects_critical_spo2_and_bp():
    result = VitalMonitor().monitor(
        [
            {"name": "SpO2", "value": "88", "unit": "%"},
            {"name": "Blood Pressure", "value": "185/122", "unit": "mmHg"},
            {"name": "Heart Rate", "value": "90", "unit": "bpm"},
        ]
    )

    assert result.monitoring_status == "critical"
    assert result.critical_count == 2
    assert result.abnormal_count == 2


def test_vital_monitor_handles_no_data():
    result = VitalMonitor().monitor([])
    assert result.monitoring_status == "no_data"
    assert result.abnormal_count == 0
    assert result.critical_count == 0


def test_critical_event_detector_detects_cardiorespiratory_signal():
    monitoring = VitalMonitor().monitor(
        [{"name": "SpO2", "value": "92", "unit": "%"}]
    )
    result = CriticalEventDetector().detect(
        conditions=[],
        symptoms=["chest pain", "shortness of breath"],
        monitoring=monitoring,
        risk_level=None,
        risk_alerts=[],
    )

    assert any(e.event_type == "cardiorespiratory_combination" for e in result.events)
    assert result.critical_event_count >= 1


def test_triage_escalates_critical_event():
    monitoring = VitalMonitor().monitor(
        [{"name": "SpO2", "value": "88", "unit": "%"}]
    )
    events = CriticalEventDetector().detect(
        conditions=["sepsis"],
        symptoms=[],
        monitoring=monitoring,
        risk_level="High",
        risk_alerts=[],
    )
    triage = EmergencyTriageClassifier().classify(
        monitoring=monitoring,
        events=events,
        risk_score=60,
        risk_level="High",
    )

    assert triage.category == "Critical"
    assert triage.escalation_required is True


def test_icu_signal_and_alert_generation():
    monitoring = VitalMonitor().monitor(
        [{"name": "SpO2", "value": "87", "unit": "%"}]
    )
    events = CriticalEventDetector().detect(
        conditions=["stroke"],
        symptoms=[],
        monitoring=monitoring,
        risk_level="Critical",
        risk_alerts=[],
    )
    triage = EmergencyTriageClassifier().classify(
        monitoring=monitoring,
        events=events,
        risk_score=85,
        risk_level="Critical",
    )
    icu = ICURequirementPredictor().predict(
        monitoring=monitoring,
        events=events,
        risk_score=85,
        risk_level="Critical",
    )
    alerts = EmergencyAlertGenerator().generate(
        monitoring=monitoring,
        triage=triage,
        events=events,
        icu=icu,
    )

    assert icu.signal == "High"
    assert alerts.alert_count >= 1
    assert alerts.highest_severity == "critical"


def test_priority_ranker_is_bounded():
    monitoring = VitalMonitor().monitor(
        [{"name": "SpO2", "value": "80", "unit": "%"}]
    )
    events = CriticalEventDetector().detect(
        conditions=["sepsis", "stroke"],
        symptoms=[],
        monitoring=monitoring,
        risk_level="Critical",
        risk_alerts=[],
    )
    triage = EmergencyTriageClassifier().classify(
        monitoring=monitoring,
        events=events,
        risk_score=100,
        risk_level="Critical",
    )
    icu = ICURequirementPredictor().predict(
        monitoring=monitoring,
        events=events,
        risk_score=100,
        risk_level="Critical",
    )
    priority = PatientPriorityRanker().rank(
        triage=triage,
        monitoring=monitoring,
        events=events,
        icu_signal=icu.signal,
    )

    assert 0 <= priority.priority_score <= 100
    assert priority.priority_level == "Critical"
