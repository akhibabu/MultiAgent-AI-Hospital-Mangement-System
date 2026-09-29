"""Digital Twin pipeline: snapshot -> simulate -> feedback -> persistable result."""
from __future__ import annotations

import time

from app.ai.digital_twin.models import DigitalTwinScenario, DigitalTwinSimulation, HospitalTwinState
from app.ai.digital_twin.simulator import DigitalTwinSimulator
from app.ai.digital_twin.state_builder import DigitalTwinStateBuilder


class DigitalTwinPipeline:
    def __init__(self, state_builder: DigitalTwinStateBuilder | None = None, simulator: DigitalTwinSimulator | None = None) -> None:
        self._state = state_builder or DigitalTwinStateBuilder()
        self._simulator = simulator or DigitalTwinSimulator()

    def snapshot(self) -> HospitalTwinState:
        return self._state.build()

    def simulate(self, scenario: DigitalTwinScenario) -> tuple[HospitalTwinState, DigitalTwinSimulation, int]:
        started = time.perf_counter()
        state = self._state.build()
        simulation = self._simulator.run(state, scenario)
        elapsed = int((time.perf_counter() - started) * 1000)
        return state, simulation, elapsed
