from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.routes.validation import router
from app.schemas.auth import UserProfile
from app.schemas.enums import UserRole
from app.services.medical_report_validation_service import MedicalReportValidationService


def _user() -> UserProfile:
    now = datetime.now(timezone.utc)
    return UserProfile(
        id=uuid4(),
        full_name="Medical Report Validation Tester",
        email="medical.report.validation@example.com",
        role=UserRole.ADMIN,
        created_at=now,
        updated_at=now,
    )


def test_medical_report_endpoints(tmp_path: Path, monkeypatch) -> None:
    stamp = tmp_path / "20260916T120000Z"
    stamp.mkdir(parents=True)
    (stamp / "summary.json").write_text(
        """{
          "agent": "medical_report",
          "title": "MEDICAL REPORT AGENT VALIDATION",
          "dataset_cases_total": 100,
          "tasks": [{
            "task": "medical_report_insurance_documentation",
            "task_label": "Insurance Documentation",
            "slug": "insurance_documentation",
            "total_cases": 100,
            "eligible_cases": 100,
            "evaluated_cases": 100,
            "failed_cases": 0,
            "coverage": 1.0,
            "status": "VALIDATED",
            "notes": [],
            "main_metric": {"label": "Recall", "value": 0.05}
          }],
          "overall_score": null
        }""",
        encoding="utf-8",
    )
    (stamp / "insurance_documentation.json").write_text(
        """{
          "agent": "medical_report",
          "task": "medical_report_insurance_documentation",
          "task_label": "Insurance Documentation",
          "total_cases": 100,
          "eligible_cases": 100,
          "evaluated_cases": 100,
          "failed_cases": 0,
          "coverage": 1.0,
          "metrics": {"recall": 0.05},
          "metric_applicability": ["recall"],
          "metric_notes": [],
          "status": "VALIDATED",
          "display_metrics": [{"label": "Recall", "value": 0.05}],
          "main_metric": {"label": "Recall", "value": 0.05},
          "per_case_results": [{
            "case_id": "VC-medical_report_insurance_documentation-00001",
            "agent": "medical_report",
            "task": "medical_report_insurance_documentation",
            "prediction": {"diagnosis_codes": [{"code": "2761"}]},
            "ground_truth": {"kind": "BILLING_CODE_SET", "items": []},
            "metrics": {"recall": 0.0},
            "status": "VALIDATED"
          }]
        }""",
        encoding="utf-8",
    )
    latest = tmp_path / "latest"
    latest.mkdir()
    for name in ("summary.json", "insurance_documentation.json"):
        (latest / name).write_text((stamp / name).read_text(encoding="utf-8"), encoding="utf-8")

    service = MedicalReportValidationService(tmp_path)
    monkeypatch.setattr(
        "app.routes.validation.medical_report_validation_service",
        service,
    )

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = _user
    client = TestClient(app)

    summary = client.get("/validation/medical-report/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["agent"] == "medical_report"
    insurance = next(
        row for row in body["tasks"] if row["task"] == "medical_report_insurance_documentation"
    )
    assert insurance["main_metric"]["value"] == 0.05

    task = client.get("/validation/medical-report/insurance_documentation")
    assert task.status_code == 200
    assert task.json()["metrics"]["recall"] == 0.05

    case = client.get(
        "/validation/medical-report/insurance_documentation/"
        "VC-medical_report_insurance_documentation-00001"
    )
    assert case.status_code == 200
    assert case.json()["case_id"] == "VC-medical_report_insurance_documentation-00001"
