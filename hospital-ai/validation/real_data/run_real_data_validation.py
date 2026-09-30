"""Empirical validation runner for external healthcare datasets.

Run from hospital-ai/:
    python validation/real_data/run_real_data_validation.py

The runner never generates ground truth.\n# CI also verifies that every persisted score is tagged real_world. It only scores tasks where the
external dataset supplies an independent observed target. Unsupported tasks
are written as PENDING_REAL_GROUND_TRUTH.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import sys
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
RESULT_ROOT = PROJECT_ROOT / "validation" / "results" / "dataset" / "real_data_v1"
HANGU_PATH = PROJECT_ROOT / "validation" / "datasets" / "hangu_real" / "Data.csv"
MIMIC_ED_URL = "https://physionet.org/files/mimic-iv-ed-demo/2.2/ed"
MIMIC_ICU_URL = "https://physionet.org/files/mimic-iv-demo/2.2/icu/icustays.csv.gz"
HHS_API = "https://healthdata.gov/resource/sgxm-t72h.json"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def f1_binary(truth: list[bool], pred: list[bool]) -> tuple[float, float, float]:
    tp = sum(a and b for a, b in zip(truth, pred))
    fp = sum((not a) and b for a, b in zip(truth, pred))
    fn = sum(a and (not b) for a, b in zip(truth, pred))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def macro_f1(truth: list[str], pred: list[str]) -> float:
    labels = sorted(set(truth) | set(pred))
    scores = []
    for label in labels:
        tp = sum(a == label and b == label for a, b in zip(truth, pred))
        fp = sum(a != label and b == label for a, b in zip(truth, pred))
        fn = sum(a == label and b != label for a, b in zip(truth, pred))
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        scores.append(2 * p * r / (p + r) if p + r else 0.0)
    return sum(scores) / len(scores) if scores else 0.0


def mae(values: list[float]) -> float:
    return sum(abs(x) for x in values) / len(values) if values else 0.0


def rmse(values: list[float]) -> float:
    return math.sqrt(sum(x * x for x in values) / len(values)) if values else 0.0


def write_task(task_id: str, records: list[dict], summary: dict) -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    (RESULT_ROOT / f"{task_id}.jsonl").write_text(
        "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in records),
        encoding="utf-8",
    )
    (RESULT_ROOT / f"{task_id}.summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )


def summary(
    task_id: str,
    task: str,
    status: str,
    cases: int,
    dataset: str,
    metric: str | None = None,
    value: float | None = None,
    **extra,
) -> dict:
    return {
        "task_id": task_id,
        "task": task,
        "status": status,
        "cases_evaluated": cases if status.startswith("VALIDATED") else 0,
        "cases_in_benchmark": cases,
        "headline_metric": metric,
        "headline_value": value,
        "dataset": dataset,
        "benchmark_type": "real_world",
        **extra,
    }


def download(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        return destination
    req = Request(url, headers={"User-Agent": "hospital-ai-real-validation/1.0"})
    with urlopen(req, timeout=60) as response:
        destination.write_bytes(response.read())
    return destination


def open_csv(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", newline="", encoding="utf-8")
    return path.open("r", newline="", encoding="utf-8")


def ensure_mimic_demo(root: Path) -> tuple[Path, Path, Path]:
    ed_root = root / "mimic-iv-ed-demo" / "ed"
    triage = download(f"{MIMIC_ED_URL}/triage.csv.gz", ed_root / "triage.csv.gz")
    edstays = download(f"{MIMIC_ED_URL}/edstays.csv.gz", ed_root / "edstays.csv.gz")
    icu = download(MIMIC_ICU_URL, root / "mimic-iv-demo" / "icu" / "icustays.csv.gz")
    return triage, edstays, icu


def run_emergency(triage_path: Path, edstays_path: Path, icu_path: Path, max_cases: int | None) -> None:
    from app.ai.emergency.critical_event_detector import CriticalEventDetector
    from app.ai.emergency.icu_predictor import ICURequirementPredictor
    from app.ai.emergency.triage_classifier import EmergencyTriageClassifier
    from app.ai.emergency.vital_monitor import VitalMonitor

    def label(acuity: int) -> str:
        return {1: "Critical", 2: "Critical", 3: "Urgent", 4: "Semi-Urgent", 5: "Routine"}[acuity]

    icu_hadm: set[str] = set()
    with open_csv(icu_path) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if str(row.get("hadm_id") or "").strip():
                icu_hadm.add(str(row["hadm_id"]).strip())

    hadm_by_stay: dict[str, str] = {}
    with open_csv(edstays_path) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stay_id = str(row.get("stay_id") or "").strip()
            hadm_id = str(row.get("hadm_id") or "").strip()
            if stay_id:
                hadm_by_stay[stay_id] = hadm_id

    monitor = VitalMonitor()
    detector = CriticalEventDetector()
    classifier = EmergencyTriageClassifier()
    icu_predictor = ICURequirementPredictor()

    triage_truth: list[str] = []
    triage_pred: list[str] = []
    icu_truth: list[bool] = []
    icu_pred: list[bool] = []
    triage_records = []
    icu_records = []

    with open_csv(triage_path) as handle:
        reader = csv.DictReader(handle)
        required = {"stay_id", "acuity", "chiefcomplaint", "heartrate", "o2sat", "sbp", "dbp"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise RuntimeError(f"MIMIC triage is missing columns: {sorted(missing)}")

        processed = 0
        for row in reader:
            if max_cases is not None and processed >= max_cases:
                break
            try:
                acuity = int(float(row.get("acuity", "")))
            except (TypeError, ValueError):
                continue
            if acuity not in {1, 2, 3, 4, 5}:
                continue

            vitals = []
            for name, key, unit in (
                ("Temperature", "temperature", "F"),
                ("Respiratory Rate", "resprate", "breaths/min"),
                ("Heart Rate", "heartrate", "bpm"),
                ("SpO2", "o2sat", "%"),
            ):
                value = str(row.get(key) or "").strip()
                if value:
                    vitals.append({"name": name, "value": value, "unit": unit})
            sbp = str(row.get("sbp") or "").strip()
            dbp = str(row.get("dbp") or "").strip()
            if sbp and dbp:
                vitals.append({"name": "Blood Pressure", "value": f"{sbp}/{dbp}", "unit": "mmHg"})

            chief = str(row.get("chiefcomplaint") or "").strip()
            monitoring = monitor.monitor(vitals)
            events = detector.detect(
                conditions=[],
                symptoms=[chief] if chief else [],
                monitoring=monitoring,
                risk_level=None,
                risk_alerts=[],
            )
            triage = classifier.classify(
                monitoring=monitoring, events=events, risk_score=None, risk_level=None
            )
            icu = icu_predictor.predict(
                monitoring=monitoring, events=events, risk_score=None, risk_level=None
            )

            stay_id = str(row["stay_id"])
            hadm_id = hadm_by_stay.get(stay_id, "")
            observed_icu = bool(hadm_id and hadm_id in icu_hadm)

            truth_label = label(acuity)
            triage_truth.append(truth_label)
            triage_pred.append(triage.category)
            icu_truth.append(observed_icu)
            icu_pred.append(icu.signal == "High")

            triage_records.append({
                "case_id": f"MIMIC-ED-DEMO-{stay_id}",
                "task_id": "emergency_triage_classification",
                "status": "SCORED",
                "prediction": triage.category,
                "ground_truth": {"mimic_acuity": acuity, "mapped_label": truth_label},
                "metrics": {"match": triage.category == truth_label},
            })
            icu_records.append({
                "case_id": f"MIMIC-ED-DEMO-{stay_id}",
                "task_id": "emergency_icu_requirement_prediction",
                "status": "SCORED",
                "prediction": {"signal": icu.signal, "positive": icu.signal == "High"},
                "ground_truth": {
                    "observed_icu_admission": observed_icu,
                    "hadm_id_present": bool(hadm_id),
                },
                "metrics": {"match": (icu.signal == "High") == observed_icu},
            })
            processed += 1

    triage_accuracy = (
        sum(a == b for a, b in zip(triage_truth, triage_pred)) / len(triage_truth)
        if triage_truth else 0.0
    )
    triage_f1 = macro_f1(triage_truth, triage_pred)
    write_task(
        "emergency_triage_classification",
        triage_records,
        summary(
            "emergency_triage_classification",
            "Triage Classification",
            "VALIDATED_REAL",
            len(triage_truth),
            "MIMIC-IV-ED Demo v2.2",
            "Accuracy",
            triage_accuracy,
            accuracy=triage_accuracy,
            macro_f1=triage_f1,
            f1_score=triage_f1,
            source_url="https://physionet.org/content/mimic-iv-ed-demo/2.2/",
            note="Ground truth is the MIMIC triage acuity assigned in the ED record. Project mapping 1-2 Critical, 3 Urgent, 4 Semi-Urgent, 5 Routine. This is retrospective dataset validation, not a clinical validation study.",
        ),
    )

    p, r, f1 = f1_binary(icu_truth, icu_pred)
    acc = sum(a == b for a, b in zip(icu_truth, icu_pred)) / len(icu_truth) if icu_truth else 0.0
    write_task(
        "emergency_icu_requirement_prediction",
        icu_records,
        summary(
            "emergency_icu_requirement_prediction",
            "ICU Requirement Prediction",
            "VALIDATED_REAL",
            len(icu_truth),
            "MIMIC-IV-ED Demo v2.2 + MIMIC-IV Clinical Database Demo v2.2",
            "F1",
            f1,
            accuracy=acc,
            precision=p,
            recall=r,
            f1_score=f1,
            source_url="https://physionet.org/content/mimic-iv-ed-demo/2.2/",
            note="Ground truth is observed ICU admission linked through edstays.hadm_id to MIMIC-IV demo icustays. It is an observed disposition/outcome proxy, not a clinician-labelled statement that ICU admission was medically required.",
        ),
    )

    for task_id, task in (
        ("emergency_vital_monitoring", "Real-Time Vital Monitoring"),
        ("emergency_critical_event_detection", "Critical Event Detection"),
        ("emergency_alert_generation", "Emergency Alert Generation"),
        ("emergency_patient_priority_ranking", "Patient Priority Ranking"),
    ):
        write_task(
            task_id,
            [],
            summary(
                task_id,
                task,
                "PENDING_REAL_GROUND_TRUTH",
                0,
                "MIMIC-IV-ED Demo v2.2",
                source_url="https://physionet.org/content/mimic-iv-ed-demo/2.2/",
                note="The public dataset contains relevant observations but no independent clinician-labelled target matching this exact project output. No proxy score is substituted.",
            ),
        )


def parse_num(value: object) -> float | None:
    text = str(value or "").strip()
    if not text or text.lower() in {"nan", "null", "none"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def hhs_records(max_cases: int | None) -> list[dict[str, object]]:
    query = f"{HHS_API}?$limit={max_cases or 5000}"
    req = Request(query, headers={"User-Agent": "hospital-ai-real-validation/1.0"})
    with urlopen(req, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload


def run_hhs_capacity(records: list[dict[str, object]], max_cases: int | None) -> None:
    from app.ai.resource_allocation.availability_assessor import AvailabilityAssessor
    from app.ai.resource_allocation.models import ResourceRequirement

    assessor = AvailabilityAssessor()
    bed_truth: list[bool] = []
    bed_pred: list[bool] = []
    icu_truth: list[bool] = []
    icu_pred: list[bool] = []
    bed_cases = []
    icu_cases = []

    rows = records[:max_cases] if max_cases else records
    for idx, row in enumerate(rows, 1):
        state = str(row.get("state") or "")
        day = str(row.get("date") or "")
        total_beds = parse_num(row.get("inpatient_beds"))
        used_beds = parse_num(row.get("inpatient_beds_used"))
        if total_beds is not None and used_beds is not None and total_beds >= 0 and used_beds >= 0:
            available = max(int(round(total_beds - used_beds)), 0)
            requirement = ResourceRequirement(
                requirement="Bed",
                resource_type="Bed",
                required_quantity=1,
                source="HHS real facility/state capacity time series",
            )
            output = assessor.assess(
                requirements=[requirement],
                resources=[{
                    "id": f"hhs-bed-{idx}",
                    "resource_name": "Reported inpatient beds",
                    "resource_type": "Bed",
                    "available_quantity": available,
                    "status": "Available" if available > 0 else "Unavailable",
                }],
                doctors=[],
            )[0]
            truth = available > 0
            pred = output.allocated_quantity > 0
            bed_truth.append(truth)
            bed_pred.append(pred)
            bed_cases.append({
                "case_id": f"HHS-BED-{state}-{day}-{idx}",
                "task_id": "resource_allocation_bed_allocation",
                "status": "SCORED",
                "prediction": {"status": output.status, "available_quantity": available},
                "ground_truth": {"reported_available_beds": available, "allocatable": truth},
                "metrics": {"match": pred == truth},
            })

        icu_total = parse_num(row.get("total_staffed_adult_icu_beds"))
        icu_used = parse_num(row.get("adult_icu_bed_utilization_numerator"))
        if icu_used is None:
            util = parse_num(row.get("adult_icu_bed_utilization"))
            if util is not None and icu_total is not None:
                icu_used = icu_total * util
        if icu_total is not None and icu_used is not None and icu_total >= 0 and icu_used >= 0:
            available = max(int(round(icu_total - icu_used)), 0)
            requirement = ResourceRequirement(
                requirement="ICU Bed",
                resource_type="ICU Bed",
                required_quantity=1,
                source="HHS real facility/state capacity time series",
            )
            output = assessor.assess(
                requirements=[requirement],
                resources=[{
                    "id": f"hhs-icu-{idx}",
                    "resource_name": "Reported staffed adult ICU beds",
                    "resource_type": "ICU Bed",
                    "available_quantity": available,
                    "status": "Available" if available > 0 else "Unavailable",
                }],
                doctors=[],
            )[0]
            truth = available > 0
            pred = output.allocated_quantity > 0
            icu_truth.append(truth)
            icu_pred.append(pred)
            icu_cases.append({
                "case_id": f"HHS-ICU-{state}-{day}-{idx}",
                "task_id": "resource_allocation_icu_allocation",
                "status": "SCORED",
                "prediction": {"status": output.status, "available_quantity": available},
                "ground_truth": {"reported_available_icu_beds": available, "allocatable": truth},
                "metrics": {"match": pred == truth},
            })

    for task_id, task_name, truth, pred, cases, resource_label in (
        ("resource_allocation_bed_allocation", "Bed Allocation", bed_truth, bed_pred, bed_cases, "inpatient beds"),
        ("resource_allocation_icu_allocation", "ICU Allocation", icu_truth, icu_pred, icu_cases, "staffed adult ICU beds"),
    ):
        p, r, f1 = f1_binary(truth, pred)
        acc = sum(a == b for a, b in zip(truth, pred)) / len(truth) if truth else 0.0
        write_task(
            task_id,
            cases,
            summary(
                task_id,
                task_name,
                "VALIDATED_REAL_AVAILABILITY",
                len(truth),
                "HHS COVID-19 Reported Patient Impact and Hospital Capacity by State Timeseries",
                "Availability Alignment F1",
                f1,
                accuracy=acc,
                precision=p,
                recall=r,
                f1_score=f1,
                source_url="https://healthdata.gov/Hospital/COVID-19-Reported-Patient-Impact-and-Hospital-Capa/sgxm-t72h",
                note=f"Real facility/state capacity data used for {resource_label}. The target is whether reported capacity leaves at least one unit available. This is availability alignment, not historical patient-to-resource assignment accuracy.",
            ),
        )

    for task_id, task_name in (
        ("resource_allocation_ventilator_allocation", "Ventilator Allocation"),
        ("resource_allocation_equipment_allocation", "Equipment Allocation"),
        ("resource_allocation_staff_allocation", "Staff Allocation"),
        ("resource_allocation_demand_forecasting", "Demand Forecasting"),
    ):
        write_task(
            task_id,
            [],
            summary(
                task_id,
                task_name,
                "PENDING_REAL_GROUND_TRUTH",
                0,
                "HHS COVID-19 Reported Patient Impact and Hospital Capacity by State Timeseries",
                source_url="https://healthdata.gov/Hospital/COVID-19-Reported-Patient-Impact-and-Hospital-Capa/sgxm-t72h",
                note="The public dataset does not contain the required patient-level equipment/staff assignment or a future-demand label matching this project task. No synthetic target is used.",
            ),
        )


def run_digital_twin(records: list[dict[str, object]], max_cases: int | None) -> None:
    from app.ai.digital_twin.models import DigitalTwinScenario, HospitalTwinState, ResourceTwinState, StaffTwinState, FlowTwinState
    from app.ai.digital_twin.simulator import DigitalTwinSimulator

    grouped: dict[str, list[dict[str, object]]] = {}
    for row in records:
        state = str(row.get("state") or "").strip()
        day = str(row.get("date") or "").strip()
        if not state or not day:
            continue
        if parse_num(row.get("inpatient_beds")) is None or parse_num(row.get("inpatient_beds_used")) is None:
            continue
        grouped.setdefault(state, []).append(row)

    errors: list[float] = []
    records_out = []
    simulator = DigitalTwinSimulator()

    for state, rows in grouped.items():
        rows.sort(key=lambda r: str(r.get("date")))
        for current, nxt in zip(rows, rows[1:]):
            if max_cases is not None and len(records_out) >= max_cases:
                break
            current_total = parse_num(current.get("inpatient_beds"))
            current_used = parse_num(current.get("inpatient_beds_used"))
            current_util = parse_num(current.get("inpatient_beds_utilization"))
            prior_adm = parse_num(current.get("previous_day_admission_adult_covid_confirmed"))
            next_total = parse_num(nxt.get("inpatient_beds"))
            next_used = parse_num(nxt.get("inpatient_beds_used"))
            if None in (current_total, current_used, next_total, next_used):
                continue
            incoming = int(round(max(prior_adm or 0.0, 0.0)))
            # DigitalTwinScenario caps planned_admissions at 1000. Do not clip
            # a real observation silently; exclude out-of-contract rows instead.
            if incoming > 1000:
                continue
            state_model = HospitalTwinState(
                resources=[ResourceTwinState(
                    resource_type="Bed",
                    total_quantity=max(int(round(current_total)), 0),
                    available_quantity=max(int(round(current_total - current_used)), 0),
                    in_use_quantity=max(int(round(current_used)), 0),
                    maintenance_quantity=0,
                    out_of_service_quantity=0,
                    utilization_percent=max(0.0, min(100.0, (current_util or (current_used / current_total if current_total else 0.0)) * 100.0 if (current_util is not None and current_util <= 1.0) else (current_util or 0.0))),
                )],
                staff=StaffTwinState(total_doctors=0, available_doctors=0, busy_doctors=0, on_leave_doctors=0, utilization_percent=0),
                flow=FlowTwinState(
                    appointments_next_24h=0,
                    appointments_next_7d=0,
                    emergency_results_last_24h=0,
                    high_or_critical_emergencies=0,
                    icu_signals_last_24h=0,
                    scheduling_runs_last_24h=0,
                    allocation_runs_last_24h=0,
                    allocation_conflicts_last_24h=0,
                ),
                operational_pressure=max(0.0, min(100.0, (current_util or 0.0) * 100.0 if (current_util or 0.0) <= 1.0 else (current_util or 0.0))),
            )
            scenario = DigitalTwinScenario(
                horizon_hours=24,
                emergency_arrivals=0,
                planned_admissions=incoming,
                expected_discharges=0,
            )
            simulation = simulator.run(state_model, scenario)
            prediction = next(
                (p.projected_available for p in simulation.resource_projections if p.resource_type == "Bed"),
                0,
            )
            truth_available = max(int(round(next_total - next_used)), 0)
            error = float(prediction - truth_available)
            errors.append(error)
            records_out.append({
                "case_id": f"HHS-TWIN-{state}-{current.get('date')}",
                "task_id": "digital_twin_capacity_projection",
                "status": "SCORED",
                "prediction": {"projected_available_beds": prediction},
                "ground_truth": {"next_day_observed_available_beds": truth_available},
                "metrics": {"error_beds": error, "absolute_error_beds": abs(error)},
                "input": {"state": state, "current_date": current.get("date"), "next_date": nxt.get("date"), "previous_day_confirmed_admissions": incoming},
            })

    m = mae(errors)
    r = rmse(errors)
    write_task(
        "digital_twin_capacity_projection",
        records_out,
        summary(
            "digital_twin_capacity_projection",
            "Capacity Projection",
            "VALIDATED_REAL_RESTRICTED",
            len(errors),
            "HHS COVID-19 Reported Patient Impact and Hospital Capacity by State Timeseries",
            "MAE (beds)",
            m,
            mae_beds=m,
            rmse_beds=r,
            source_url="https://healthdata.gov/Hospital/COVID-19-Reported-Patient-Impact-and-Hospital-Capa/sgxm-t72h",
            note="Restricted real-data one-day projection test. The simulator receives prior-day reported adult confirmed COVID admissions as an incoming-admission input and is compared with the independently observed next-day bed availability. This is not a full hospital forecast, and it is not a causal digital-twin validation.",
        ),
    )
    for task_id, task in (
        ("digital_twin_bottleneck_detection", "Bottleneck Detection"),
        ("digital_twin_operational_pressure_projection", "Operational Pressure Projection"),
        ("digital_twin_feedback_generation", "Agent Feedback Generation"),
    ):
        write_task(
            task_id,
            [],
            summary(
                task_id,
                task,
                "PENDING_REAL_GROUND_TRUTH",
                0,
                "HHS COVID-19 Reported Patient Impact and Hospital Capacity by State Timeseries",
                source_url="https://healthdata.gov/Hospital/COVID-19-Reported-Patient-Impact-and-Hospital-Capa/sgxm-t72h",
                note="The public capacity series does not contain an independent labelled target for this exact Digital Twin output. The repository will not score these tasks against its own scenario equations.",
            ),
        )


def run_scheduling_manifest() -> None:
    row_count = 0
    sessions = set()
    with HANGU_PATH.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row_count += 1
            sessions.add(str(row.get("Session") or ""))
    for task_id, task_name in (
        ("scheduling_doctor_assignment", "Doctor Assignment"),
        ("scheduling_appointment_scheduling", "Appointment Scheduling"),
        ("scheduling_surgery_scheduling", "Surgery Scheduling"),
        ("scheduling_follow_up_planning", "Follow-Up Planning"),
        ("scheduling_queue_optimization", "Queue Optimization"),
        ("scheduling_workload_balancing", "Workload Balancing"),
    ):
        write_task(
            task_id,
            [],
            summary(
                task_id,
                task_name,
                "PENDING_REAL_GROUND_TRUTH",
                row_count,
                "Hangu real outpatient consultation dataset",
                source_url="https://github.com/fenghaolin/HanguData",
                note=f"Loaded real outpatient data ({row_count} consultation rows, {len(sessions)} sessions) including observed service times and appointment/session timing. It does not contain an independently adjudicated optimal doctor/slot/queue policy for the current deterministic agent, so no accuracy score is assigned.",
            ),
        )


def run_insurance_manifest() -> None:
    for task_id, task_name in (
        ("insurance_policy_verification", "Policy Verification"),
        ("insurance_coverage_estimation", "Coverage Estimation"),
        ("insurance_claim_generation", "Claim Generation"),
        ("insurance_fraud_screening", "Fraud Screening"),
        ("insurance_preauthorization_requirement", "Preauthorization Requirement Detection"),
    ):
        write_task(
            task_id,
            [],
            summary(
                task_id,
                task_name,
                "PENDING_REAL_GROUND_TRUTH",
                0,
                "CMS Medicare Physician & Other Practitioners / CMS plan data / OIG LEIE",
                source_url="https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-geography-and-service",
                note="Real CMS/OIG sources are available for claims, service codes, payment context, plan benefits, and provider exclusions, but they do not provide a member-level eligibility label or a complete, independently adjudicated fraud/authorization ground truth matching this agent interface. No synthetic score is substituted.",
            ),
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="validation/datasets/_downloaded_real")
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--mimic-ed-dir")
    args = parser.parse_args()

    data_root = PROJECT_ROOT / args.data_root
    mimic_root = Path(args.mimic_ed_dir).resolve() if args.mimic_ed_dir else data_root

    if args.skip_download:
        triage = mimic_root / "mimic-iv-ed-demo" / "ed" / "triage.csv.gz"
        edstays = mimic_root / "mimic-iv-ed-demo" / "ed" / "edstays.csv.gz"
        icu = mimic_root / "mimic-iv-demo" / "icu" / "icustays.csv.gz"
    else:
        triage, edstays, icu = ensure_mimic_demo(mimic_root)

    run_emergency(triage, edstays, icu, args.max_cases)

    hhs = hhs_records(args.max_cases)
    run_hhs_capacity(hhs, args.max_cases)
    run_digital_twin(hhs, args.max_cases)

    run_scheduling_manifest()
    run_insurance_manifest()

    manifest = {
        "version": 1,
        "benchmark_type": "real_world",
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "datasets": {
            "mimic_iv_ed_demo_2_2": {
                "source": "PhysioNet",
                "url": "https://physionet.org/content/mimic-iv-ed-demo/2.2/",
                "access": "open_demo",
            },
            "mimic_iv_demo_2_2": {
                "source": "PhysioNet",
                "url": "https://physionet.org/content/mimic-iv-demo/2.2/",
                "access": "open_demo",
            },
            "hangu_real_outpatient": {
                "source": "fenghaolin/HanguData",
                "url": "https://github.com/fenghaolin/HanguData",
                "access": "committed_with_attribution",
            },
            "hhs_capacity": {
                "source": "U.S. Department of Health & Human Services / HealthData.gov",
                "url": "https://healthdata.gov/Hospital/COVID-19-Reported-Patient-Impact-and-Hospital-Capa/sgxm-t72h",
                "access": "public_api",
            },
            "cms_insurance": {
                "source": "CMS",
                "url": "https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-geography-and-service",
                "access": "public_dataset",
            },
        },
    }
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    (RESULT_ROOT / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
