# Operational Validation

This directory contains **deterministic operational verification** for the Emergency, Scheduling, and Resource Allocation agents.

These checks are deliberately separate from the dataset-grounded validation framework used for Intake, Diagnosis, Research, and Prescription. The three agents in this suite are currently deterministic planning/rule engines, and the repository does not contain clinician-labelled ground truth for measuring real-world clinical accuracy.

The suite validates:

- Emergency vital thresholds, critical-event detection, triage escalation, ICU signalling, alert generation, and bounded patient priority scores.
- Scheduling specialty matching, appointment-slot recommendation, surgery planning semantics, follow-up intervals, queue ordering, and workload balancing.
- Resource Allocation upstream-context consumption, resource/staff matching, shortage detection, conflict detection, priority ordering, and allocation-score invariants.

Run from `hospital-ai/`:

```powershell
python validation/pipeline/run_operational_validation.py
```

Write an auditable JSON report:

```powershell
python validation/pipeline/run_operational_validation.py --output validation/results/operational/report.json
```

Interpretation:

- **PASS** means the implementation satisfied the specified deterministic invariant for that verification fixture.
- It does **not** mean the agent is clinically validated or that the policy is correct for every hospital.
- Emergency triage and ICU outputs remain project-level decision-support signals and require clinician-led validation before clinical deployment.
- A future empirical validation phase should use clinician-labelled emergency cases and hospital operational logs or simulation benchmarks for scheduling/resource allocation.
