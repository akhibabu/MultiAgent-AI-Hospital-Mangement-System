from types import SimpleNamespace
from uuid import uuid4

from app.ai.resource_allocation.availability_assessor import AvailabilityAssessor
from app.ai.resource_allocation.conflict_detector import ConflictDetector
from app.ai.resource_allocation.context import ResourceAllocationContext
from app.ai.resource_allocation.models import ResourceRequirement
from app.ai.resource_allocation.priority_allocator import PriorityAllocator
from app.schemas.resource_allocation import ResourceAllocationStartRequest


def _patient():
    return SimpleNamespace(patient_id="patient-1", patient_name="Test Patient")


def test_resource_allocation_request_contains_only_patient_id():
    assert set(ResourceAllocationStartRequest.model_fields) == {"patient_id"}


def test_context_uses_scheduling_requirements_and_emergency_priority():
    derived = ResourceAllocationContext.derive(
        {
            "patient": _patient(),
            "scheduling": {
                "id": "s1",
                "emergency_priority_level": "Urgent",
                "emergency_priority_score": 86,
                "resource_requirements_json": [
                    "ICU Bed",
                    "Operating Theatre",
                    "Specialist Staff",
                    "Laboratory Capacity",
                ],
                "procedures_json": ["Angioplasty"],
                "surgery_scheduling_json": {"required": True},
                "surgery_recommendation_json": ["Diagnosis Treatment Path: surgery required"],
            },
            "emergency": {"id": "e1", "icu_requirement_json": {"signal": "High"}},
        }
    )

    labels = [r.requirement for r in derived["requirements"]]
    assert labels == [
        "ICU Bed",
        "Operating Theatre",
        "Specialist Staff",
        "Laboratory Capacity",
    ]
    assert derived["priority_level"] == "Urgent"
    assert derived["priority_score"] == 86
    assert derived["procedures"] == ["Angioplasty"]
    assert derived["source_result_ids"] == {"scheduling": "s1", "emergency": "e1"}


def test_context_falls_back_to_emergency_icu_signal_when_scheduling_missing():
    derived = ResourceAllocationContext.derive(
        {
            "patient": _patient(),
            "scheduling": {},
            "emergency": {
                "id": "e1",
                "patient_priority_json": {"priority_level": "Critical", "priority_score": 99},
                "icu_requirement_json": {"signal": "High"},
            },
        }
    )
    assert [r.requirement for r in derived["requirements"]] == ["ICU Bed"]
    assert derived["requirements"][0].resource_type == "ICU Bed"
    assert derived["priority_level"] == "Critical"


def test_availability_assessor_matches_inventory_and_specialist_staff():
    requirements = [
        ResourceRequirement(
            requirement="ICU Bed", resource_type="ICU Bed", required_quantity=1,
            source="Scheduling Agent", rationale="ICU required", priority=100,
        ),
        ResourceRequirement(
            requirement="Specialist Staff", resource_type=None, required_quantity=1,
            source="Scheduling Agent", rationale="Cardiologist needed", priority=85,
        ),
    ]
    assessor = AvailabilityAssessor()
    allocations = assessor.assess(
        requirements=requirements,
        resources=[
            {
                "id": str(uuid4()),
                "resource_name": "ICU-01",
                "resource_type": "ICU Bed",
                "available_quantity": 2,
                "status": "Available",
            },
            {
                "id": str(uuid4()),
                "resource_name": "ICU-02",
                "resource_type": "ICU Bed",
                "available_quantity": 0,
                "status": "In Use",
            },
        ],
        doctors=[
            {
                "id": "doc-1",
                "first_name": "Asha",
                "last_name": "Rao",
                "specialization": "Cardiology",
                "availability_status": "Available",
            }
        ],
        selected_doctor_id="doc-1",
        preferred_specialists=["Cardiologist"],
    )

    assert allocations[0].allocated_quantity == 1
    assert allocations[0].status == "Allocated"
    assert allocations[1].allocated_quantity == 1
    assert allocations[1].matched_resources[0].resource_id == "doc-1"


def test_shortage_and_upstream_conflict_are_detected():
    item = AvailabilityAssessor().assess(
        requirements=[
            ResourceRequirement(
                requirement="Operating Theatre", resource_type="Operation Theatre",
                required_quantity=1, source="Scheduling Agent", rationale="Surgery", priority=88,
            )
        ],
        resources=[],
        doctors=[],
    )[0]
    conflicts = ConflictDetector().detect(
        allocations=[item], surgery_conflict=True, scheduling_available=True
    )
    assert any(c.code == "RESOURCE_SHORTAGE" for c in conflicts)
    assert any(c.code == "UPSTREAM_SURGERY_CONFLICT" for c in conflicts)


def test_priority_allocator_scores_fully_available_plan_at_100():
    item = AvailabilityAssessor().assess(
        requirements=[
            ResourceRequirement(
                requirement="Bed", resource_type="Bed", required_quantity=1,
                source="Scheduling Agent", rationale="Bed", priority=40,
            )
        ],
        resources=[
            {
                "id": "bed-1", "resource_name": "Bed 1", "resource_type": "Bed",
                "available_quantity": 1, "status": "Available",
            }
        ],
        doctors=[],
    )[0]
    assert PriorityAllocator().allocation_score([item]) == 100.0
