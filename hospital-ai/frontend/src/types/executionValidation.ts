export type ExecutionValidationStatus =
  | 'PASSED'
  | 'FAILED'
  | 'NOT_VALIDATABLE'
  | 'ERROR';

export interface ExecutionValidationMetrics {
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  applicable: string[];
}

export interface ExecutionValidationResult {
  validation_id: string;
  execution_id: string;
  case_id: string | null;
  task: string;
  task_label: string;
  agent_name: string;
  timestamp: string;
  prediction: {
    entities?: Array<{ type?: string; value?: string }>;
  };
  ground_truth: {
    kind?: string;
    mentions?: Array<{ str?: string; type?: string }>;
    source?: {
      dataset?: string;
      record_id?: string;
      source_file?: string;
    };
  };
  metrics: ExecutionValidationMetrics;
  counts?: {
    true_positives: number;
    false_positives: number;
    false_negatives: number;
  };
  status: ExecutionValidationStatus | string;
  message?: string | null;
  question?: string | null;
  source?: {
    dataset?: string | null;
    record_id?: string | null;
    source_file?: string | null;
    split?: string | null;
  } | null;
}

export interface IntakeDisplayMetric {
  key?: string;
  label: string;
  value: number;
}

export interface IntakeComparisonRow {
  field?: string;
  agent?: string;
  ground_truth?: string;
  mark?: 'match' | 'missing' | 'extra' | 'mismatch' | string;
}

export interface IntakeTaskHeadline {
  task: string;
  task_label: string;
  slug: string;
  total_cases: number;
  eligible_cases: number;
  evaluated_cases: number;
  failed_cases: number;
  coverage: number | null;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  applicable: string[];
  status: string;
  notes: string[];
  display_metrics?: IntakeDisplayMetric[];
  main_metric?: { key?: string; label: string; value: number | null };
  human_summary?: string | null;
}

export interface IntakeValidationSummary {
  agent: string;
  title: string;
  validation_timestamp?: string | null;
  dataset_cases_total: number;
  tasks: IntakeTaskHeadline[];
  overall_score: number | null;
  overall_score_note?: string | null;
  coverage_vs_performance_note?: string | null;
}

export interface IntakeTaskDetail {
  agent: string;
  task: string;
  task_label: string;
  total_cases: number;
  eligible_cases: number;
  evaluated_cases: number;
  failed_cases: number;
  coverage: number | null;
  coverage_note?: string | null;
  metrics: {
    accuracy: number | null;
    precision: number | null;
    recall: number | null;
    f1_score: number | null;
  };
  metric_applicability: string[];
  metric_notes: string[];
  status: string;
  dataset_mapping?: string | null;
  display_metrics?: IntakeDisplayMetric[];
  main_metric?: { key?: string; label: string; value: number | null };
  human_summary?: string | null;
  per_case_results: Array<{
    case_id?: string;
    prediction?: unknown;
    ground_truth?: unknown;
    metrics?: Record<string, number | null>;
    status?: string;
    comparison?: IntakeComparisonRow[];
    agent_text?: string;
    ground_truth_text?: string;
    human_summary?: string;
  }>;
}

export type DiagnosisDisplayMetric = IntakeDisplayMetric;
export type DiagnosisComparisonRow = IntakeComparisonRow;

export interface DiagnosisTaskHeadline {
  task: string;
  task_label: string;
  slug: string;
  total_cases: number;
  eligible_cases: number;
  evaluated_cases: number;
  failed_cases: number;
  coverage: number | null;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  applicable: string[];
  status: string;
  notes: string[];
  display_metrics?: DiagnosisDisplayMetric[];
  main_metric?: { key?: string; label: string; value: number | null };
  human_summary?: string | null;
}

export interface DiagnosisValidationSummary {
  agent: string;
  title: string;
  validation_timestamp?: string | null;
  dataset_cases_total: number;
  tasks: DiagnosisTaskHeadline[];
  overall_score: number | null;
  overall_score_note?: string | null;
  coverage_vs_performance_note?: string | null;
}

export interface ResearchTaskHeadline {
  task: string;
  task_label: string;
  slug: string;
  total_cases: number;
  eligible_cases: number;
  evaluated_cases: number;
  failed_cases: number;
  coverage: number | null;
  status: string;
  notes: string[];
  display_metrics?: DiagnosisDisplayMetric[];
  main_metric?: { key?: string; label: string; value: number | null };
  human_summary?: string | null;
}

export interface ResearchValidationSummary {
  agent: string;
  title: string;
  validation_timestamp?: string | null;
  dataset_cases_total: number;
  tasks: ResearchTaskHeadline[];
  overall_score: number | null;
  overall_score_note?: string | null;
  coverage_vs_performance_note?: string | null;
}

export interface PrescriptionTaskHeadline {
  task: string;
  task_label: string;
  slug: string;
  total_cases: number;
  eligible_cases: number;
  evaluated_cases: number;
  failed_cases: number;
  coverage: number | null;
  status: string;
  notes: string[];
  display_metrics?: DiagnosisDisplayMetric[];
  main_metric?: { key?: string; label: string; value: number | null };
  human_summary?: string | null;
}

export interface PrescriptionValidationSummary {
  agent: string;
  title: string;
  validation_timestamp?: string | null;
  dataset_cases_total: number;
  tasks: PrescriptionTaskHeadline[];
  overall_score: number | null;
  overall_score_note?: string | null;
  coverage_vs_performance_note?: string | null;
}

export interface MedicalReportTaskHeadline {
  task: string;
  task_label: string;
  slug: string;
  total_cases: number;
  eligible_cases: number;
  evaluated_cases: number;
  failed_cases: number;
  coverage: number | null;
  status: string;
  notes: string[];
  display_metrics?: DiagnosisDisplayMetric[];
  main_metric?: { key?: string; label: string; value: number | null };
  human_summary?: string | null;
}

export interface MedicalReportValidationSummary {
  agent: string;
  title: string;
  validation_timestamp?: string | null;
  source_metrics_dir?: string | null;
  dataset_cases_total: number;
  tasks: MedicalReportTaskHeadline[];
  overall_score: number | null;
  overall_score_note?: string | null;
  coverage_vs_performance_note?: string | null;
}

export interface MedicalReportTaskDetail {
  agent: string;
  task: string;
  task_label: string;
  total_cases: number;
  eligible_cases: number;
  evaluated_cases: number;
  failed_cases: number;
  coverage: number | null;
  coverage_note?: string | null;
  metrics: Record<string, number | null>;
  metric_applicability: string[];
  metric_notes: string[];
  status: string;
  dataset_mapping?: string | null;
  display_metrics?: DiagnosisDisplayMetric[];
  main_metric?: { key?: string; label: string; value: number | null };
  human_summary?: string | null;
  per_case_results?: Array<Record<string, unknown>>;
}

export interface PrescriptionTaskDetail {
  agent: string;
  task: string;
  task_label: string;
  total_cases: number;
  eligible_cases: number;
  evaluated_cases: number;
  failed_cases: number;
  coverage: number | null;
  coverage_note?: string | null;
  metrics: Record<string, number | null>;
  metric_applicability: string[];
  metric_notes: string[];
  status: string;
  dataset_mapping?: string | null;
  display_metrics?: DiagnosisDisplayMetric[];
  main_metric?: { key?: string; label: string; value: number | null };
  human_summary?: string | null;
  per_case_results?: Array<Record<string, unknown>>;
}

export interface ResearchTaskDetail {
  agent: string;
  task: string;
  task_label: string;
  total_cases: number;
  eligible_cases: number;
  evaluated_cases: number;
  failed_cases: number;
  coverage: number | null;
  coverage_note?: string | null;
  metrics: Record<string, number | null>;
  metric_applicability: string[];
  metric_notes: string[];
  status: string;
  dataset_mapping?: string | null;
  display_metrics?: DiagnosisDisplayMetric[];
  main_metric?: { key?: string; label: string; value: number | null };
  human_summary?: string | null;
  per_case_results: Array<{
    case_id?: string;
    prediction?: unknown;
    ground_truth?: unknown;
    metrics?: Record<string, number | null>;
    status?: string;
    agent_text?: string;
    ground_truth_text?: string;
    human_summary?: string;
  }>;
}

export interface DiagnosisTaskDetail {
  agent: string;
  task: string;
  task_label: string;
  total_cases: number;
  eligible_cases: number;
  evaluated_cases: number;
  failed_cases: number;
  coverage: number | null;
  coverage_note?: string | null;
  metrics: {
    accuracy: number | null;
    precision: number | null;
    recall: number | null;
    f1_score: number | null;
    top_1_accuracy?: number | null;
    top_k_accuracy?: number | null;
    macro_f1?: number | null;
  };
  metric_applicability: string[];
  metric_notes: string[];
  status: string;
  dataset_mapping?: string | null;
  display_metrics?: DiagnosisDisplayMetric[];
  main_metric?: { key?: string; label: string; value: number | null };
  human_summary?: string | null;
  per_case_results: Array<{
    case_id?: string;
    prediction?: unknown;
    ground_truth?: unknown;
    metrics?: Record<string, number | null>;
    status?: string;
    comparison?: DiagnosisComparisonRow[];
    agent_text?: string;
    ground_truth_text?: string;
    human_summary?: string;
  }>;
}
