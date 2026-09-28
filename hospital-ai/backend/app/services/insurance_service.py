"""Insurance Agent service facade."""

from __future__ import annotations

import time
from typing import Optional
from uuid import UUID

from fastapi import HTTPException

from app.ai.insurance.pipeline import InsurancePipeline
from app.core.logging import get_logger
from app.repositories.insurance_repository import (
    InsurancePolicyRepository,
    InsuranceResultRepository,
)
from app.schemas.ai_orchestrator import OrchestratorDebugInfoOut
from app.schemas.insurance import (
    InsuranceHistoryItemOut,
    InsuranceResultOut,
    InsuranceStartRequest,
    InsuranceStartResponse,
)

logger = get_logger("hospital_ai.insurance.service")


class InsuranceService:
    def __init__(
        self,
        pipeline: Optional[InsurancePipeline] = None,
        policies: Optional[InsurancePolicyRepository] = None,
        results: Optional[InsuranceResultRepository] = None,
    ) -> None:
        self._pipeline = pipeline or InsurancePipeline()
        self._policies = policies or InsurancePolicyRepository()
        self._results = results or InsuranceResultRepository()

    def start(self, request: InsuranceStartRequest) -> InsuranceStartResponse:
        started = time.perf_counter()

        try:
            report = self._pipeline.run(
                patient_id=request.patient_id,
                policy=request.policy,
                service_name=request.service_name,
                service_date=request.service_date,
                billed_amount=request.billed_amount,
                supporting_documents=request.supporting_documents,
            )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            from app.ai.orchestrator import AIOrchestratorError

            logger.exception("Insurance pipeline failed patient=%s", request.patient_id)
            if isinstance(exc, AIOrchestratorError):
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            raise HTTPException(status_code=500, detail=f"Insurance Agent failed: {exc}") from exc

        # Store the exact policy snapshot used for the successful run.
        try:
            self._policies.upsert_for_patient(
                patient_id=request.patient_id,
                policy=request.policy.model_dump(mode="json"),
            )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Insurance policy persistence failed patient=%s", request.patient_id)
            raise HTTPException(status_code=500, detail=f"Insurance policy persistence failed: {exc}") from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        row = self._results.create(
            {
                "patient_id": str(request.patient_id),
                "service_name": request.service_name,
                "service_date": request.service_date.isoformat(),
                "billed_amount": request.billed_amount,
                "policy_number": request.policy.policy_number,
                "policy_json": request.policy.model_dump(mode="json"),
                "policy_verification_json": report.policy_verification.model_dump(mode="json"),
                "coverage_estimate_json": report.coverage_estimate.model_dump(mode="json"),
                "claim_draft_json": report.claim_draft.model_dump(mode="json"),
                "fraud_screening_json": report.fraud_screening.model_dump(mode="json"),
                "preauthorization_json": report.preauthorization.model_dump(mode="json"),
                "request_json": {
                    "service_name": request.service_name,
                    "service_date": request.service_date.isoformat(),
                    "billed_amount": request.billed_amount,
                    "supporting_documents": request.supporting_documents,
                },
                "summary": report.summary,
                "engine": report.engine,
                "status": "Completed",
                "warnings_json": report.warnings,
                "processing_time_ms": elapsed_ms,
            }
        )

        result = InsuranceResultOut.model_validate(row)
        return InsuranceStartResponse(
            patient_id=request.patient_id,
            service_name=request.service_name,
            service_date=request.service_date,
            billed_amount=request.billed_amount,
            status="Completed",
            processing_time_ms=elapsed_ms,
            summary=report.summary,
            policy=report.policy,
            policy_verification=report.policy_verification,
            coverage_estimate=report.coverage_estimate,
            claim_draft=report.claim_draft,
            fraud_screening=report.fraud_screening,
            preauthorization=report.preauthorization,
            warnings=report.warnings,
            insurance_result=result,
            ai_debug=[
                OrchestratorDebugInfoOut.model_validate(item.model_dump(mode="json"))
                for item in report.ai_debug
            ],
        )

    def result(self, patient_id: UUID) -> InsuranceResultOut:
        row = self._results.get_latest_for_patient(patient_id)
        if not row:
            raise HTTPException(
                status_code=404,
                detail="No Insurance Agent result found for this patient. Run the agent first.",
            )
        return InsuranceResultOut.model_validate(row)

    def history(self, patient_id: UUID, limit: int = 20) -> list[InsuranceHistoryItemOut]:
        rows = self._results.list_for_patient(patient_id, limit=limit)
        return [
            InsuranceHistoryItemOut(
                id=row["id"],
                created_at=row["created_at"],
                service_name=row.get("service_name") or "",
                billed_amount=float(row.get("billed_amount") or 0),
                policy_number=row.get("policy_number") or "",
                status=row.get("status") or "Completed",
            )
            for row in rows
        ]


def get_insurance_service() -> InsuranceService:
    return InsuranceService()
