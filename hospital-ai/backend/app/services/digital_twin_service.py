"""Digital Twin service facade."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from app.ai.digital_twin.models import DigitalTwinRun, DigitalTwinScenario, HospitalTwinState
from app.ai.digital_twin.pipeline import DigitalTwinPipeline
from app.repositories.digital_twin_repository import DigitalTwinDataRepository
from app.schemas.digital_twin import (
    DigitalTwinHistoryItemOut,
    DigitalTwinRunOut,
    DigitalTwinScenarioRequest,
    DigitalTwinStateResponse,
    HospitalTwinStateOut,
)


class DigitalTwinService:
    ENGINE = "deterministic_hospital_digital_twin_v1"

    def __init__(self, pipeline: Optional[DigitalTwinPipeline] = None, repository: Optional[DigitalTwinDataRepository] = None) -> None:
        self._pipeline = pipeline or DigitalTwinPipeline()
        self._repository = repository or DigitalTwinDataRepository()

    def state(self) -> DigitalTwinStateResponse:
        try:
            state = self._pipeline.snapshot()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Digital Twin state build failed: {exc}") from exc
        return DigitalTwinStateResponse(state=HospitalTwinStateOut.model_validate(state.model_dump(mode="json")))

    def simulate(self, request: DigitalTwinScenarioRequest) -> DigitalTwinRunOut:
        scenario = DigitalTwinScenario.model_validate(request.model_dump(mode="json"))
        try:
            state, simulation, elapsed = self._pipeline.simulate(scenario)
            row = self._repository.create_run({
                "status": "Completed",
                "engine": self.ENGINE,
                "horizon_hours": scenario.horizon_hours,
                "baseline_state_json": state.model_dump(mode="json"),
                "scenario_json": scenario.model_dump(mode="json"),
                "simulation_json": simulation.model_dump(mode="json"),
                "processing_time_ms": elapsed,
            })
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Digital Twin simulation failed: {exc}") from exc
        run = DigitalTwinRun(
            id=str(row["id"]),
            created_at=str(row.get("created_at") or simulation.generated_at),
            status=str(row.get("status") or "Completed"),
            engine=str(row.get("engine") or self.ENGINE),
            baseline_state=state,
            simulation=simulation,
            processing_time_ms=elapsed,
        )
        return DigitalTwinRunOut.model_validate(run.model_dump(mode="json"))

    def latest(self) -> DigitalTwinRunOut:
        row = self._repository.get_latest_run()
        if not row:
            raise HTTPException(status_code=404, detail="No Digital Twin simulation has been run yet.")
        try:
            return self._row_to_out(row)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Stored Digital Twin result is invalid: {exc}") from exc

    def history(self, limit: int = 20) -> list[DigitalTwinHistoryItemOut]:
        rows = self._repository.list_runs(limit=limit)
        out = []
        for row in rows:
            simulation = row.get("simulation_json") or {}
            out.append(DigitalTwinHistoryItemOut(
                id=str(row.get("id")),
                created_at=str(row.get("created_at") or ""),
                status=str(row.get("status") or "Completed"),
                engine=str(row.get("engine") or self.ENGINE),
                horizon_hours=int(row.get("horizon_hours") or (simulation.get("scenario") or {}).get("horizon_hours") or 24),
                processing_time_ms=row.get("processing_time_ms"),
                summary=str(simulation.get("summary") or ""),
            ))
        return out

    @staticmethod
    def _row_to_out(row) -> DigitalTwinRunOut:
        simulation = row.get("simulation_json") or {}
        state = row.get("baseline_state_json") or {}
        scenario = row.get("scenario_json") or simulation.get("scenario") or {}
        simulation["scenario"] = scenario
        run = DigitalTwinRun(
            id=str(row["id"]),
            created_at=str(row.get("created_at") or simulation.get("generated_at") or ""),
            status=str(row.get("status") or "Completed"),
            engine=str(row.get("engine") or DigitalTwinService.ENGINE),
            baseline_state=HospitalTwinState.model_validate(state),
            simulation=simulation,
            processing_time_ms=int(row.get("processing_time_ms") or 0),
        )
        return DigitalTwinRunOut.model_validate(run.model_dump(mode="json"))
