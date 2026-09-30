"""Dataset validation for the newly added Insurance Agent and Hospital Digital Twin.

This runner is deliberately isolated from the existing validation runners. It
uses only the new-agent benchmark and writes only new-agent result artifacts.

Run from hospital-ai/:
    python validation/pipeline/run_new_agents_validation.py --cases 25
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
BENCHMARK_PATH = PROJECT_ROOT / "validation" / "benchmarks" / "new_agents_v1.json"
RESULT_ROOT = PROJECT_ROOT / "validation" / "results" / "dataset" / "new_agents_v1"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def accuracy(matches: Iterable[bool]) -> float:
    values = list(matches)
    return sum(1 for value in values if value) / len(values) if values else 0.0


def precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def set_f1(truth_sets: list[set[str]], pred_sets: list[set[str]]) -> tuple[float, float, float]:
    tp = fp = fn = 0
    for truth, pred in zip(truth_sets, pred_sets):
        tp += len(truth & pred)
        fp += len(pred - truth)
        fn += len(truth - pred)
    return precision_recall_f1(tp, fp, fn)


def write_results(task_id: str, records: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    (RESULT_ROOT / f"{task_id}.jsonl").write_text(
        "".join(json.dumps(record, separators=(",", ":")) + "\n" for record in records),
        encoding="utf-8",
    )
    (RESULT_ROOT / f"{task_id}.summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )


def case_result(
    *,
    agent: str,
    task_id: str,
    case_id: str,
    prediction: Any,
    ground_truth: Any,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "task_id": task_id,
        "agent": agent,
        "status": "SCORED",
        "prediction": prediction,
        "ground_truth": ground_truth,
        "metrics": metrics,
        "benchmark_type": "synthetic_project_reference",
    }


def task_summary(
    *,
    task_id: str,
    task: str,
    status: str,
    metric: str | None,
    value: float | None,
    cases: int,
    note: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "task": task,
        "status": status,
        "cases_evaluated": cases if status == "VALIDATED" else 0,
        "cases_in_benchmark": cases,
        "headline_metric": metric,
        "headline_value": value,
        "dataset": "NEW-AGENTS-REF-25-v1 (synthetic project reference)",
        "note": note,
        **extra,
    }


def run_insurance(cases: list[dict[str, Any]]) -> None:
    from app.ai.insurance.models import InsurancePolicy
    from app.ai.insurance.policy_engine import CoverageEstimator, PolicyVerifier

    verifier = PolicyVerifier()
    estimator = CoverageEstimator()

    verification_records: list[dict[str, Any]] = []
    coverage_records: list[dict[str, Any]] = []
    preauth_records: list[dict[str, Any]] = []

    verification_matches: list[bool] = []
    coverage_matches: list[bool] = []
    preauth_matches: list[bool] = []

    def service_match(service_name: str, values: list[str]) -> bool:
        service = service_name.strip().lower()
        return any(
            service == value.strip().lower()
            or service in value.strip().lower()
            or value.strip().lower() in service
            for value in values
            if value.strip()
        )

    for item in cases:
        inp = item["input"]
        policy = InsurancePolicy.model_validate(inp["policy"])
        service_date = date.fromisoformat(inp["service_date"])
        verification = verifier.verify(
            policy=policy,
            service_name=inp["service_name"],
            service_date=service_date,
            checked_on=service_date,
        )
        coverage = estimator.estimate(
            policy=policy,
            service_name=inp["service_name"],
            billed_amount=inp["billed_amount"],
            verification=verification,
        )
        gt = item["ground_truth"]

        pred_verification = {
            "verified": verification.verified,
            "coverage_active": verification.coverage_active,
            "issue_count": len(verification.issues),
        }
        verification_match = pred_verification == gt["policy_verification"]
        verification_matches.append(verification_match)
        verification_records.append(
            case_result(
                agent="Insurance",
                task_id="insurance_policy_verification",
                case_id=item["case_id"],
                prediction=pred_verification,
                ground_truth=gt["policy_verification"],
                metrics={"match": verification_match},
            )
        )

        pred_coverage = {
            "eligible_amount": coverage.eligible_amount,
            "deductible_applied": coverage.deductible_applied,
            "insurer_estimate": coverage.insurer_estimate,
            "patient_estimate": coverage.patient_estimate,
        }
        coverage_match = all(
            abs(float(pred_coverage[key]) - float(gt["coverage_estimate"][key])) < 0.01
            for key in pred_coverage
        )
        coverage_matches.append(coverage_match)
        coverage_records.append(
            case_result(
                agent="Insurance",
                task_id="insurance_coverage_estimation",
                case_id=item["case_id"],
                prediction=pred_coverage,
                ground_truth=gt["coverage_estimate"],
                metrics={"match": coverage_match},
            )
        )

        authorization_required = service_match(
            inp["service_name"],
            policy.preauthorization_services,
        )
        preauth_match = authorization_required == gt["preauthorization"]["authorization_required"]
        preauth_matches.append(preauth_match)
        preauth_records.append(
            case_result(
                agent="Insurance",
                task_id="insurance_preauthorization_requirement",
                case_id=item["case_id"],
                prediction={"authorization_required": authorization_required},
                ground_truth=gt["preauthorization"],
                metrics={"match": preauth_match},
            )
        )

    verification_accuracy = accuracy(verification_matches)
    coverage_accuracy = accuracy(coverage_matches)
    preauth_accuracy = accuracy(preauth_matches)

    write_results(
        "insurance_policy_verification",
        verification_records,
        task_summary(
            task_id="insurance_policy_verification",
            task="Policy Verification",
            status="VALIDATED",
            metric="Exact Structured Accuracy",
            value=verification_accuracy,
            cases=len(cases),
            note=(
                "Synthetic reference evaluation of deterministic policy consistency fields "
                "(verified, coverage_active, and issue count). It does not verify carrier-side eligibility."
            ),
            accuracy=verification_accuracy,
            f1_score=verification_accuracy,
        ),
    )
    write_results(
        "insurance_coverage_estimation",
        coverage_records,
        task_summary(
            task_id="insurance_coverage_estimation",
            task="Coverage Estimation",
            status="VALIDATED",
            metric="Exact Structured Accuracy",
            value=coverage_accuracy,
            cases=len(cases),
            note=(
                "Synthetic reference evaluation of eligible amount, deductible, insurer estimate, "
                "and patient estimate produced by the deterministic coverage calculator."
            ),
            accuracy=coverage_accuracy,
            f1_score=coverage_accuracy,
        ),
    )
    write_results(
        "insurance_preauthorization_requirement",
        preauth_records,
        task_summary(
            task_id="insurance_preauthorization_requirement",
            task="Preauthorization Requirement Detection",
            status="VALIDATED",
            metric="Accuracy",
            value=preauth_accuracy,
            cases=len(cases),
            note=(
                "Evaluation covers only the deterministic requirement flag derived from supplied "
                "policy terms. It does not score the LLM-generated clinical-necessity recommendation."
            ),
            accuracy=preauth_accuracy,
        ),
    )

    for task_id, task_name in (
        ("insurance_claim_generation", "Claim Generation"),
        ("insurance_fraud_screening", "Fraud Screening"),
    ):
        write_results(
            task_id,
            [],
            task_summary(
                task_id=task_id,
                task=task_name,
                status="PENDING_HUMAN_REVIEW",
                metric=None,
                value=None,
                cases=len(cases),
                note=(
                    "The new Insurance Agent stage is LLM-backed and produces narrative/review judgments. "
                    "This repository currently has no defensible labelled ground truth for automatic semantic "
                    "scoring, so it remains pending human review rather than receiving an invented accuracy/F1."
                ),
            ),
        )


def run_digital_twin(cases: list[dict[str, Any]]) -> None:
    from app.ai.digital_twin.models import DigitalTwinScenario, HospitalTwinState
    from app.ai.digital_twin.simulator import DigitalTwinSimulator

    simulator = DigitalTwinSimulator()
    projection_records: list[dict[str, Any]] = []
    bottleneck_records: list[dict[str, Any]] = []
    pressure_records: list[dict[str, Any]] = []
    feedback_records: list[dict[str, Any]] = []

    projection_matches: list[bool] = []
    bottleneck_truth: list[set[str]] = []
    bottleneck_pred: list[set[str]] = []
    pressure_matches: list[bool] = []
    feedback_truth: list[set[str]] = []
    feedback_pred: list[set[str]] = []

    for item in cases:
        source_state = dict(item["input"]["state"])
        source_state.update(
            {
                "captured_at": "2026-09-30T00:00:00+00:00",
                "source_status": {},
                "source_timestamps": {},
            }
        )
        state = HospitalTwinState.model_validate(source_state)
        scenario = DigitalTwinScenario.model_validate(item["input"]["scenario"])
        result = simulator.run(state, scenario)
        gt = item["ground_truth"]

        pred_projections = [p.model_dump(mode="json") for p in result.resource_projections]
        projection_match = pred_projections == gt["resource_projections"]
        projection_matches.append(projection_match)
        projection_records.append(
            case_result(
                agent="Digital Twin",
                task_id="digital_twin_capacity_projection",
                case_id=item["case_id"],
                prediction=pred_projections,
                ground_truth=gt["resource_projections"],
                metrics={"match": projection_match},
            )
        )

        pred_bottlenecks = sorted({b.resource_type for b in result.bottlenecks})
        gt_bottlenecks = sorted(gt["bottleneck_types"])
        bottleneck_truth.append(set(gt_bottlenecks))
        bottleneck_pred.append(set(pred_bottlenecks))
        bottleneck_records.append(
            case_result(
                agent="Digital Twin",
                task_id="digital_twin_bottleneck_detection",
                case_id=item["case_id"],
                prediction=pred_bottlenecks,
                ground_truth=gt_bottlenecks,
                metrics={
                    "match": pred_bottlenecks == gt_bottlenecks,
                    "prediction_count": len(pred_bottlenecks),
                    "ground_truth_count": len(gt_bottlenecks),
                },
            )
        )

        pressure_match = (
            abs(
                float(result.flow_projection.projected_operational_pressure)
                - float(gt["projected_operational_pressure"])
            )
            < 0.01
        )
        pressure_matches.append(pressure_match)
        pressure_records.append(
            case_result(
                agent="Digital Twin",
                task_id="digital_twin_operational_pressure_projection",
                case_id=item["case_id"],
                prediction=result.flow_projection.projected_operational_pressure,
                ground_truth=gt["projected_operational_pressure"],
                metrics={"match": pressure_match},
            )
        )

        pred_targets = sorted({s.target_agent for s in result.feedback_signals})
        gt_targets = sorted(gt["feedback_targets"])
        feedback_truth.append(set(gt_targets))
        feedback_pred.append(set(pred_targets))
        feedback_records.append(
            case_result(
                agent="Digital Twin",
                task_id="digital_twin_feedback_generation",
                case_id=item["case_id"],
                prediction=pred_targets,
                ground_truth=gt_targets,
                metrics={"match": pred_targets == gt_targets},
            )
        )

    projection_accuracy = accuracy(projection_matches)
    bottleneck_p, bottleneck_r, bottleneck_f1 = set_f1(bottleneck_truth, bottleneck_pred)
    pressure_accuracy = accuracy(pressure_matches)
    feedback_p, feedback_r, feedback_f1 = set_f1(feedback_truth, feedback_pred)

    write_results(
        "digital_twin_capacity_projection",
        projection_records,
        task_summary(
            task_id="digital_twin_capacity_projection",
            task="Capacity Projection",
            status="VALIDATED",
            metric="Exact Structured Accuracy",
            value=projection_accuracy,
            cases=len(cases),
            note=(
                "Synthetic reference evaluation of deterministic resource projections for the "
                "Digital Twin what-if simulator."
            ),
            accuracy=projection_accuracy,
        ),
    )
    write_results(
        "digital_twin_bottleneck_detection",
        bottleneck_records,
        task_summary(
            task_id="digital_twin_bottleneck_detection",
            task="Bottleneck Detection",
            status="VALIDATED",
            metric="F1",
            value=bottleneck_f1,
            cases=len(cases),
            note=(
                f"Synthetic reference set evaluation of projected bottleneck resource types. "
                f"Precision {bottleneck_p:.1%}; Recall {bottleneck_r:.1%}; F1 {bottleneck_f1:.1%}."
            ),
            precision=bottleneck_p,
            recall=bottleneck_r,
            f1_score=bottleneck_f1,
        ),
    )
    write_results(
        "digital_twin_operational_pressure_projection",
        pressure_records,
        task_summary(
            task_id="digital_twin_operational_pressure_projection",
            task="Operational Pressure Projection",
            status="VALIDATED",
            metric="Accuracy",
            value=pressure_accuracy,
            cases=len(cases),
            note="Synthetic reference evaluation of the deterministic projected operational-pressure value.",
            accuracy=pressure_accuracy,
        ),
    )
    write_results(
        "digital_twin_feedback_generation",
        feedback_records,
        task_summary(
            task_id="digital_twin_feedback_generation",
            task="Agent Feedback Generation",
            status="VALIDATED",
            metric="F1",
            value=feedback_f1,
            cases=len(cases),
            note=(
                f"Synthetic reference set evaluation of target operations agents for advisory feedback. "
                f"Precision {feedback_p:.1%}; Recall {feedback_r:.1%}; F1 {feedback_f1:.1%}."
            ),
            precision=feedback_p,
            recall=feedback_r,
            f1_score=feedback_f1,
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=25, choices=range(1, 26))
    args = parser.parse_args()

    benchmark = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    insurance_cases = benchmark["insurance_cases"][: args.cases]
    twin_cases = benchmark["digital_twin_cases"][: args.cases]

    run_insurance(insurance_cases)
    run_digital_twin(twin_cases)

    print(f"Validated new-agent deterministic benchmark cases: {args.cases}")
    print(f"Results written to: {RESULT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
