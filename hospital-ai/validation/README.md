# Dataset-grounded Validation

The Validation Center follows the benchmark design used for the original five-agent validation work: each task is evaluated independently. A dataset row becomes a benchmark case, the task implementation produces a prediction, the prediction is compared with the task-specific ground truth, and the per-case result is stored before aggregate metrics are calculated.

Task-appropriate metrics are used rather than one project-wide score:

- Classification: Accuracy, Macro F1, or task-specific class metrics.
- Extraction: precision, recall, and F1 on annotated entities or fields.
- Retrieval/ranking: Recall@K and NDCG@K.
- Structured outputs: field-level accuracy or exact match where appropriate.
- Numerical forecasting: MAE, RMSE, and R2.

Tasks with no defensible reference are marked NOT_VALIDATABLE or PENDING_HUMAN_REVIEW. They are never assigned an artificial score.

## Emergency

`pipeline/run_emergency_mimic_validation.py` supports MIMIC-IV-ED triage data. It accepts `triage.csv` or `triage.csv.gz`, creates one stored result per eligible case, and computes Accuracy and Macro F1.

MIMIC-IV-ED triage includes vital signs, chief complaint, and a 1-5 acuity label. This project benchmark maps 1-2 to Critical, 3 to Urgent, 4 to Semi-Urgent, and 5 to Routine. The mapping is an evaluation convention for this project, not an official clinical triage replacement.

Example:

```powershell
python validation/pipeline/run_emergency_mimic_validation.py --triage path/to/triage.csv.gz --max-cases 100
```

The command writes `validation/results/dataset/emergency_triage/cases.jsonl` and `summary.json`. The Validation Center reads these results and replaces the pending Emergency triage row with the measured benchmark result.

## Scheduling and Resource Allocation

These agents require operational datasets with defensible target outcomes. The GitHub repository does not currently contain such labelled historical data, so their rows remain PENDING_DATASET rather than showing invented accuracy or F1.

Scheduling needs historical doctor/appointment/queue records. Resource Allocation needs historical bed/ICU/equipment/staff allocation records or a resource-demand time series. Once those datasets are supplied, the same per-case prediction/ground-truth/result structure is used.

The existing 44 deterministic engineering checks remain supplemental CI evidence. They are intentionally not treated as dataset accuracy or F1.
## Latest dataset runs

The GitHub Actions dataset run on 24 Sep 2026 completed successfully for 1,000 HLT-005 cases, 6 AISmithLab easy scheduling cases, and up to 500 cases per HLT-010 resource subtask.

Emergency results:
- Triage Classification: Accuracy 16.5%, Macro F1 17.0% (1,000 cases)
- ICU Requirement Prediction: Accuracy 82.8%, Precision 80.0%, Recall 10.7%, F1 18.9% (1,000 cases)
- Patient Priority Ranking: Accuracy 16.5%, Macro F1 17.0% (1,000 cases)
- Emergency Alert Generation: F1 62.6%, Accuracy 54.1%, Precision 70.5%, Recall 56.3% (1,000 cases). This is explicitly a proxy evaluation where the reference is ESI <= 3, not an independent alert annotation.

Scheduling:
- Appointment Scheduling: 6/6 cases, Accuracy 100.0% for earliest-valid-slot selection after benchmark constraints are resolved. The production AppointmentSlotEngine receives candidate windows after constraint filtering, so this is not a full end-to-end policy/insurance/referral/booking-mutation score.

Resource Allocation:
- Bed, ICU, Ventilator, and Equipment: 500 cases each, 100.0% availability-alignment Accuracy/Precision/Recall/F1. These are availability-alignment checks against HLT-010 operational records, not patient-to-resource historical assignment accuracy.
- Staff Allocation: not currently validatable because HLT-010 has no patient-specific staff assignment ground truth.
- Demand Forecasting: not currently implemented by the Resource Allocation Agent.

The per-case JSONL outputs are produced during the workflow and uploaded as the dataset-agent-validation-reports artifact. The aggregate values above are also recorded in validation/frozen_results.json so the Validation Center can display the latest measured run without committing the full downloaded datasets.
