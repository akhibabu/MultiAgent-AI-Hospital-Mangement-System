from datetime import date
from uuid import uuid4

from app.ai.diagnosis.models import TreatmentPathRecommendation
from app.ai.prescription.models import TreatmentPlan
from app.ai.scheduling.context import SchedulingSourceContext
from app.ai.scheduling.models import SurgerySchedulingResult
from app.ai.scheduling.surgery_scheduler import SurgeryScheduler
from app.schemas.scheduling import SchedulingStartRequest


def test_structured_upstream_models_carry_procedure_metadata():
    diagnosis = TreatmentPathRecommendation(
        surgery_required=True,
        recommended_procedures=["Angioplasty"],
        estimated_duration_minutes=90,
    )
    prescription = TreatmentPlan(
        surgery_required=True,
        procedure_recommendations=["Angioplasty"],
        estimated_duration_minutes=90,
    )

    assert diagnosis.surgery_required is True
    assert diagnosis.recommended_procedures == ["Angioplasty"]
    assert diagnosis.estimated_duration_minutes == 90
    assert prescription.procedure_recommendations == ["Angioplasty"]


def test_scheduling_request_exposes_no_clinical_decision_fields():
    fields = set(SchedulingStartRequest.model_fields)
    assert fields == {"patient_id", "preferred_date"}


def test_scheduling_context_combines_upstream_results():
    derived = SchedulingSourceContext.derive(
        {
            "diagnosis": {
                "id": "d1",
                "target_conditions_json": ["Coronary Artery Disease"],
                "treatment_path_json": {
                    "recommended_department": "Cardiology",
                    "recommended_specialists": ["Cardiologist"],
                    "diagnostic_tests": ["ECG"],
                    "imaging": ["Coronary CT"],
                    "urgency": "Urgent",
                    "surgery_required": True,
                    "recommended_procedures": ["Angioplasty"],
                    "estimated_duration_minutes": 90,
                },
                "severity_assessment_json": {"level": "High"},
                "clinical_decision_support_json": {
                    "possible_diagnoses": ["Coronary Artery Disease"],
                    "clinical_notes": ["Procedural evaluation recommended."],
                },
            },
            "emergency": {
                "id": "e1",
                "patient_priority_json": {
                    "priority_level": "Urgent",
                    "priority_score": 84,
                },
                "triage_classification_json": {"category": "Urgent"},
                "icu_requirement_json": {"signal": "Moderate"},
            },
            "prescription": {
                "id": "p1",
                "treatment_plan_json": {
                    "medication_plan": ["Physician review required."],
                    "recommended_lab_tests": ["Troponin"],
                    "recommended_imaging": ["Echocardiogram"],
                    "recommended_specialists": ["Cardiologist"],
                    "follow_up_interval": "7 days",
                    "surgery_required": True,
                    "procedure_recommendations": ["Angioplasty"],
                    "estimated_duration_minutes": 90,
                    "monitoring_plan": ["Cardiac monitoring"],
                },
                "validation_summary_json": {
                    "approval_status": "Requires Physician Review"
                },
            },
            "medical_report": {
                "id": "m1",
                "doctor_notes_json": {
                    "assessment": "Stable for specialist procedural review.",
                    "plan": "Arrange cardiology follow-up.",
                },
                "referral_letter_json": {
                    "receiving_specialist": "Cardiologist",
                    "requested_evaluation": "Evaluate for angioplasty.",
                },
            },
        }
    )

    assert derived["sources_available"] == {
        "diagnosis": True,
        "emergency": True,
        "prescription": True,
        "medical_report": True,
    }
    assert derived["visit_type"] == "Emergency"
    assert derived["department"] == "Cardiology"
    assert derived["specialists"] == ["Cardiologist"]
    assert derived["procedures"] == ["Angioplasty"]
    assert derived["surgery_required"] is True
    assert derived["surgery_duration_minutes"] == 90
    assert derived["recommended_tests"] == ["ECG", "Troponin"]
    assert derived["recommended_imaging"] == ["Coronary CT", "Echocardiogram"]
    assert "Medication" in derived["treatment_modes"]
    assert "Procedure/Surgery" in derived["treatment_modes"]
    assert derived["resource_requirements"] == [
        "Monitored Bed",
        "Operating Theatre",
        "Specialist Staff",
        "Laboratory Capacity",
        "Imaging Capacity",
    ]


def test_surgery_is_not_inferred_from_documented_procedure_without_recommendation():
    derived = SchedulingSourceContext.derive(
        {
            "diagnosis": {"treatment_path_json": {}},
            "emergency": {},
            "prescription": {},
            "medical_report": {
                "discharge_summary_json": {
                    "procedures": ["Appendectomy completed"]
                }
            },
        }
    )
    assert derived["surgery_required"] is False


def test_negative_surgery_language_does_not_trigger_surgery():
    derived = SchedulingSourceContext.derive(
        {
            "diagnosis": {
                "treatment_path_json": {
                    "notes": "No surgery is recommended at this stage."
                }
            },
            "emergency": {},
            "prescription": {},
            "medical_report": {},
        }
    )
    assert derived["surgery_required"] is False


def test_conflicting_structured_surgery_recommendations_are_flagged():
    derived = SchedulingSourceContext.derive(
        {
            "diagnosis": {
                "treatment_path_json": {
                    "surgery_required": True,
                    "recommended_procedures": ["Procedure A"],
                }
            },
            "emergency": {},
            "prescription": {
                "treatment_plan_json": {
                    "surgery_required": False,
                    "procedure_recommendations": [],
                }
            },
            "medical_report": {},
        }
    )
    assert derived["surgery_required"] is True
    assert derived["surgery_conflict"] is True


def test_missing_upstream_duration_does_not_create_fake_surgery_slot():
    result = SurgerySchedulingResult(
        required=True,
        procedure_names=["Angioplasty"],
        duration_minutes=None,
        resource_allocation_required=True,
        notes=["Duration not provided upstream."],
    )
    assert result.duration_minutes is None
    assert result.resource_allocation_required is True


def test_surgery_scheduler_defers_without_upstream_duration():
    result = SurgeryScheduler().recommend(
        required=True,
        procedure_names=["Angioplasty"],
        windows=[],
        doctor_id="doctor-1",
        doctor_name="Dr. Test",
        duration_minutes=0,
    )
    assert result.recommended_slot is None
    assert result.duration_minutes is None
    assert result.resource_allocation_required is True
