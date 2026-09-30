# Real-data validation

This directory contains the empirical validation path for the Emergency, Scheduling, Resource Allocation, Insurance, and Digital Twin work. It is deliberately separate from the historical synthetic/functional benchmarks.

## What counts as a real result

A result is labelled real-world only when the benchmark input and reference outcome come from an external dataset that is independent of the implementation under test. Synthetic/reference cases are kept as engineering checks and are not reused as empirical accuracy.

### Emergency
MIMIC-IV-ED Demo v2.2 is downloaded from PhysioNet for CI/local smoke validation. The runner evaluates triage acuity against the documented MIMIC acuity field and observed ICU admission by linking edstays.hadm_id to MIMIC-IV demo icustays.hadm_id. The ICU result is explicitly an observed-admission outcome, not a clinical-necessity label.

The full MIMIC-IV-ED dataset is supported locally through --mimic-ed-dir and can replace the demo for the report that is ultimately presented. Full MIMIC access is credentialed; the open demo is intentionally small.

### Resource Allocation
The HHS hospital-capacity time series is downloaded from HealthData.gov. Bed and ICU tasks are reported as **real-data availability alignment**: the agent is tested against facility-reported capacity state, not historical patient-to-resource assignment. Equipment and staff assignment remain unscored because the public time series does not contain those patient-level assignments.

### Digital Twin
The runner performs a restricted one-day real-data projection test using the HHS time series. It uses the prior day's reported adult admissions as the incoming-admission input and compares projected next-day inpatient-bed availability with the independently observed next-day value. This is a restricted forecast/replay benchmark, not a full hospital digital-twin forecast or causal claim.

### Scheduling
The repository contains the Hangu real outpatient consultation dataset. It is ingested and audited, but it does not provide an independently labelled optimal doctor/slot policy for the current deterministic Scheduling Agent. Therefore appointment/doctor/surgery/queue/workload accuracy is **not** fabricated from the observed schedule. A real operating-room scheduling dataset is recorded in the dataset manifest for the next scheduling benchmark.

### Insurance
CMS public claims/plan data and the OIG exclusion list are real sources, but they do not provide member-level insurance eligibility or a labelled fraud ground truth that maps cleanly onto the current Insurance Agent interface. The project therefore keeps Policy Verification, Coverage Estimation, Fraud Screening, and Preauthorization as PENDING_REAL_GROUND_TRUTH rather than inventing scores. Claim Generation can be human-adjudicated later using real claim contexts.

## Local run

From hospital-ai/:

\`\`\`bash
python validation/real_data/run_real_data_validation.py
\`\`\`

Use --max-cases to cap the local run. The runner writes summaries and per-case JSONL under validation/results/dataset/real_data_v1/.

No raw credentialed MIMIC data is committed to this repository. Public small data that is redistributed here carries source attribution and license terms in its dataset directory.

CI workflow: `.github/workflows/real-data-validation.yml` runs the empirical benchmark on this validation path and records measured summaries only.
