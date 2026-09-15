"""
Medical Report Agent adapter.

Runs the production `MedicalReportPipeline`. As with prescription, the prior
diagnosis, research and prescription results a live workflow would supply do
not exist for a validation case, so those repositories return nothing. The
agent therefore writes from patient context alone, which is a weaker starting
position than production and should be read that way.
"""

from __future__ import annotations

from typing import Any, Dict

from adapters.base import (
    AgentAdapter,
    ExecutionRuntime,
    context_payload,
    dump,
    prepare_patient_context,
)
from case_loader import AgentInput, InputNotSupported, SealedCase

#: task_id -> attribute on MedicalReportBundle holding that task's output.
_OUTPUT_FIELDS: Dict[str, str] = {
    "medical_report_clinical_summary": "clinical_summary",
    "medical_report_discharge_summary": "discharge_summary",
    "medical_report_insurance_documentation": "insurance_documentation",
}


class MedicalReportAdapter(AgentAdapter):
    agent = "medical_report"
    entry_points = {
        task_id: "app.ai.medical_report.pipeline.MedicalReportPipeline.run"
        for task_id in _OUTPUT_FIELDS
    }

    def build_input(self, case: SealedCase, runtime: ExecutionRuntime) -> AgentInput:
        if case.task_id not in _OUTPUT_FIELDS:
            raise InputNotSupported(
                f"No medical report entry point for {case.task_id}."
            )

        patient_uuid, context, notes, _ = prepare_patient_context(case, runtime)
        notes.append(
            "no prior diagnosis, research or prescription result supplied; the "
            "report is written from patient context alone"
        )
        return AgentInput(
            case_id=case.validation_case_id,
            adapter="medical_report_adapter",
            entry_point=self.entry_points[case.task_id],
            payload={
                "patient_id": str(patient_uuid),
                "context": context_payload(context),
            },
            notes=notes,
        )

    def execute(
        self,
        case: SealedCase,
        agent_input: AgentInput,
        runtime: ExecutionRuntime,
    ) -> Any:
        from app.ai.medical_report.pipeline import MedicalReportPipeline
        from backend_bridge import NullPriorResultRepository

        pipeline = MedicalReportPipeline(
            context_repo=runtime.context_registry,
            diagnosis_repo=NullPriorResultRepository(),
            research_repo=NullPriorResultRepository(),
            prescription_repo=NullPriorResultRepository(),
        )
        bundle = pipeline.run(case.patient_uuid)
        return dump(getattr(bundle, _OUTPUT_FIELDS[case.task_id]))
