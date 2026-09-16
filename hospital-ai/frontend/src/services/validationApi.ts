import apiClient from '@/services/apiClient';
import type {
  AgentDetail,
  AgentSummary,
  CaseDetail,
  CaseListParams,
  CaseListResponse,
  DatasetCoverageResponse,
  ErrorAnalysisResponse,
  ErrorListParams,
  HumanReviewStatus,
  LimitationsResponse,
  MethodologyResponse,
  MetricDefinition,
  PresentationResponse,
  CompareResponse,
  EvidenceCardData,
  ValidationHealth,
  RunDetail,
  RunListResponse,
  SafetyResponse,
  TaskDetail,
  ValidationOverview,
} from '@/types/validation';
import type {
  DiagnosisTaskDetail,
  DiagnosisValidationSummary,
  ExecutionValidationResult,
  IntakeTaskDetail,
  IntakeValidationSummary,
  PrescriptionTaskDetail,
  PrescriptionValidationSummary,
  MedicalReportTaskDetail,
  MedicalReportValidationSummary,
  ResearchTaskDetail,
  ResearchValidationSummary,
} from '@/types/executionValidation';

function withRun(params?: Record<string, unknown>, runId?: string) {
  const next: Record<string, unknown> = { ...(params || {}) };
  if (runId) next.run_id = runId;
  return next;
}

export const validationApi = {
  overview: (runId?: string) =>
    apiClient
      .get<ValidationOverview>('/validation/overview', { params: withRun({}, runId) })
      .then((r) => r.data),

  runs: () =>
    apiClient.get<RunListResponse>('/validation/runs').then((r) => r.data),

  run: (runId: string) =>
    apiClient.get<RunDetail>(`/validation/runs/${runId}`).then((r) => r.data),

  agents: (runId?: string) =>
    apiClient
      .get<AgentSummary[]>('/validation/agents', { params: withRun({}, runId) })
      .then((r) => r.data),

  agent: (agentId: string, runId?: string) =>
    apiClient
      .get<AgentDetail>(`/validation/agents/${agentId}`, {
        params: withRun({}, runId),
      })
      .then((r) => r.data),

  task: (taskId: string, runId?: string) =>
    apiClient
      .get<TaskDetail>(`/validation/tasks/${taskId}`, { params: withRun({}, runId) })
      .then((r) => r.data),

  datasets: (runId?: string) =>
    apiClient
      .get<DatasetCoverageResponse>('/validation/datasets', {
        params: withRun({}, runId),
      })
      .then((r) => r.data),

  cases: (params: CaseListParams = {}) =>
    apiClient
      .get<CaseListResponse>('/validation/cases', { params })
      .then((r) => r.data),

  case: (caseId: string, runId?: string) =>
    apiClient
      .get<CaseDetail>(`/validation/cases/${caseId}`, { params: withRun({}, runId) })
      .then((r) => r.data),

  errors: (params: ErrorListParams = {}) =>
    apiClient
      .get<ErrorAnalysisResponse>('/validation/errors', { params })
      .then((r) => r.data),

  safety: (runId?: string) =>
    apiClient
      .get<SafetyResponse>('/validation/safety', { params: withRun({}, runId) })
      .then((r) => r.data),

  limitations: (runId?: string) =>
    apiClient
      .get<LimitationsResponse>('/validation/limitations', {
        params: withRun({}, runId),
      })
      .then((r) => r.data),

  presentation: (runId?: string) =>
    apiClient
      .get<PresentationResponse>('/validation/presentation', {
        params: withRun({}, runId),
      })
      .then((r) => r.data),

  humanReview: (runId?: string) =>
    apiClient
      .get<HumanReviewStatus>('/validation/human-review', {
        params: withRun({}, runId),
      })
      .then((r) => r.data),

  health: () =>
    apiClient.get<ValidationHealth>('/validation/health').then((r) => r.data),

  metricDefinitions: () =>
    apiClient
      .get<{ metrics: MetricDefinition[]; primary_by_evaluation_type: Record<string, string> }>(
        '/validation/metrics/definitions',
      )
      .then((r) => r.data),

  evidence: (runId?: string) =>
    apiClient
      .get<EvidenceCardData[]>('/validation/evidence', { params: withRun({}, runId) })
      .then((r) => r.data),

  methodology: (taskId: string, runId?: string) =>
    apiClient
      .get<MethodologyResponse>(`/validation/methodology/${taskId}`, {
        params: withRun({}, runId),
      })
      .then((r) => r.data),

  compare: (runA: string, runB: string) =>
    apiClient
      .get<CompareResponse>('/validation/compare', {
        params: { run_a: runA, run_b: runB },
      })
      .then((r) => r.data),

  execution: (taskId: string, executionId: string) =>
    apiClient
      .get<ExecutionValidationResult>(
        `/validation/executions/${taskId}/${executionId}`,
      )
      .then((r) => r.data),

  executionByCase: (taskId: string, caseId: string) =>
    apiClient
      .get<ExecutionValidationResult>(`/validation/${taskId}/${caseId}`)
      .then((r) => r.data),

  intakeSummary: () =>
    apiClient
      .get<IntakeValidationSummary>('/validation/intake/summary')
      .then((r) => r.data),

  intakeTask: (task: string) =>
    apiClient
      .get<IntakeTaskDetail>(`/validation/intake/${task}`)
      .then((r) => r.data),

  diagnosisSummary: () =>
    apiClient
      .get<DiagnosisValidationSummary>('/validation/diagnosis/summary')
      .then((r) => r.data),

  diagnosisTask: (task: string) =>
    apiClient
      .get<DiagnosisTaskDetail>(`/validation/diagnosis/${task}`)
      .then((r) => r.data),

  researchSummary: () =>
    apiClient
      .get<ResearchValidationSummary>('/validation/research/summary')
      .then((r) => r.data),

  researchTask: (task: string) =>
    apiClient
      .get<ResearchTaskDetail>(`/validation/research/${task}`)
      .then((r) => r.data),

  prescriptionSummary: () =>
    apiClient
      .get<PrescriptionValidationSummary>('/validation/prescription/summary')
      .then((r) => r.data),

  prescriptionTask: (task: string) =>
    apiClient
      .get<PrescriptionTaskDetail>(`/validation/prescription/${task}`)
      .then((r) => r.data),

  medicalReportSummary: () =>
    apiClient
      .get<MedicalReportValidationSummary>('/validation/medical-report/summary')
      .then((r) => r.data),

  medicalReportTask: (task: string) =>
    apiClient
      .get<MedicalReportTaskDetail>(`/validation/medical-report/${task}`)
      .then((r) => r.data),
};
