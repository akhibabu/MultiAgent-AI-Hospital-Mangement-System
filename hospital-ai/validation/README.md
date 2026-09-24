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