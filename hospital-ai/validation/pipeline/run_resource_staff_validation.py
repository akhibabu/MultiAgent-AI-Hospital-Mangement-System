"""Dataset validation extension for Resource Allocation staff allocation.

HLT-010 supplies staffing shift history but does not contain patient-specific
staff assignment ground truth. To avoid pretending otherwise, this validator
uses 25 project-labelled synthetic staff-allocation cases with explicit target
specialist and expected available doctor. The result is a functional benchmark,
not historical hospital performance.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.ai.resource_allocation.availability_assessor import AvailabilityAssessor
from app.ai.resource_allocation.models import ResourceRequirement


SPECIALTIES = [
    "Cardiology",
    "Neurology",
    "Pulmonology",
    "Orthopedics",
    "Dermatology",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-cases", type=int, default=25)
    parser.add_argument(
        "--output",
        default="validation/results/dataset/resource_staff_synthetic",
    )
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    cases = []
    matches = []

    assessor = AvailabilityAssessor()

    for index in range(args.max_cases):
        specialty = SPECIALTIES[index % len(SPECIALTIES)]
        selected_doctor_id = f"DSTAFF-{index:03d}"
        doctors = [
            {
                "id": selected_doctor_id,
                "first_name": "Target",
                "last_name": f"Doctor{index:03d}",
                "specialization": specialty,
                "availability_status": "Available",
            },
            {
                "id": f"DSTAFF-OTHER-{index:03d}",
                "first_name": "Other",
                "last_name": f"Doctor{index:03d}",
                "specialization": "General Medicine",
                "availability_status": "Available",
            },
        ]

        requirement = ResourceRequirement(
            requirement="Specialist Staff",
            resource_type=None,
            required_quantity=1,
            source="Project Synthetic Staff Benchmark",
            rationale=f"{specialty} specialist required by the labelled scheduling case.",
            priority=80,
        )

        result = assessor.assess(
            requirements=[requirement],
            resources=[],
            doctors=doctors,
            selected_doctor_id=selected_doctor_id,
            preferred_specialists=[specialty],
        )[0]

        predicted_ids = [item.resource_id for item in result.matched_resources]
        predicted_selected = predicted_ids[0] if predicted_ids else None
        expected_id = selected_doctor_id
        match = predicted_selected == expected_id and result.allocated_quantity == 1

        matches.append(match)
        cases.append(
            {
                "case_id": f"RA-STAFF-{index+1:03d}",
                "task_id": "resource_allocation_staff_allocation",
                "status": "SCORED",
                "input": {
                    "required_specialist": specialty,
                    "selected_doctor_id": selected_doctor_id,
                    "doctors": doctors,
                },
                "prediction": {
                    "allocated_quantity": result.allocated_quantity,
                    "matched_resource_ids": predicted_ids,
                },
                "ground_truth": {
                    "expected_staff_id": expected_id,
                    "expected_specialty": specialty,
                },
                "metrics": {"match": match},
            }
        )

    accuracy = sum(matches) / len(matches) if matches else 0.0
    task_dir = output / "resource_allocation_staff_allocation"
    task_dir.mkdir(parents=True, exist_ok=True)

    (task_dir / "cases.jsonl").write_text(
        "".join(json.dumps(case) + "\n" for case in cases),
        encoding="utf-8",
    )
    (task_dir / "summary.json").write_text(
        json.dumps(
            {
                "task_id": "resource_allocation_staff_allocation",
                "dataset": "Project Synthetic Resource Allocation Staff Benchmark v1",
                "cases_evaluated": len(cases),
                "headline_metric": "Assignment Accuracy",
                "headline_value": accuracy,
                "accuracy": accuracy,
                "clinical_accuracy_claim": False,
                "note": "Synthetic labelled functional benchmark because HLT-010 has no patient-specific staff assignment ground truth.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (output / "cases.jsonl").write_text(
        "".join(json.dumps(case) + "\n" for case in cases),
        encoding="utf-8",
    )
    (output / "summary.json").write_text(
        json.dumps(
            {
                "dataset": "Project Synthetic Resource Allocation Staff Benchmark v1",
                "cases_evaluated": len(cases),
                "task_summaries": {
                    "resource_allocation_staff_allocation": {
                        "accuracy": accuracy,
                        "headline_metric": "Assignment Accuracy",
                        "headline_value": accuracy,
                    }
                },
                "clinical_accuracy_claim": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "task_id": "resource_allocation_staff_allocation",
                "cases_evaluated": len(cases),
                "accuracy": accuracy,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
