import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { validationApi } from '@/services/validationApi';
import type { CaseListParams, ErrorListParams } from '@/types/validation';

export const validationKeys = {
  all: ['validation'] as const,
  overview: (runId?: string) => [...validationKeys.all, 'overview', runId ?? 'latest'] as const,
  runs: () => [...validationKeys.all, 'runs'] as const,
  run: (runId: string) => [...validationKeys.all, 'run', runId] as const,
  agents: (runId?: string) => [...validationKeys.all, 'agents', runId ?? 'latest'] as const,
  agent: (agentId: string, runId?: string) =>
    [...validationKeys.all, 'agent', agentId, runId ?? 'latest'] as const,
  task: (taskId: string, runId?: string) =>
    [...validationKeys.all, 'task', taskId, runId ?? 'latest'] as const,
  datasets: (runId?: string) => [...validationKeys.all, 'datasets', runId ?? 'latest'] as const,
  cases: (params: CaseListParams) => [...validationKeys.all, 'cases', params] as const,
  case: (caseId: string, runId?: string) =>
    [...validationKeys.all, 'case', caseId, runId ?? 'latest'] as const,
  errors: (params: ErrorListParams) => [...validationKeys.all, 'errors', params] as const,
  safety: (runId?: string) => [...validationKeys.all, 'safety', runId ?? 'latest'] as const,
  limitations: (runId?: string) =>
    [...validationKeys.all, 'limitations', runId ?? 'latest'] as const,
  presentation: (runId?: string) =>
    [...validationKeys.all, 'presentation', runId ?? 'latest'] as const,
  humanReview: (runId?: string) =>
    [...validationKeys.all, 'human-review', runId ?? 'latest'] as const,
  health: () => [...validationKeys.all, 'health'] as const,
  definitions: () => [...validationKeys.all, 'definitions'] as const,
  evidence: (runId?: string) => [...validationKeys.all, 'evidence', runId ?? 'latest'] as const,
  methodology: (taskId: string, runId?: string) =>
    [...validationKeys.all, 'methodology', taskId, runId ?? 'latest'] as const,
  compare: (runA: string, runB: string) =>
    [...validationKeys.all, 'compare', runA, runB] as const,
  execution: (taskId: string, executionId: string) =>
    [...validationKeys.all, 'execution', taskId, executionId] as const,
  intakeSummary: () => [...validationKeys.all, 'intake-summary'] as const,
  intakeTask: (task: string) => [...validationKeys.all, 'intake-task', task] as const,
  diagnosisSummary: () => [...validationKeys.all, 'diagnosis-summary'] as const,
  diagnosisTask: (task: string) => [...validationKeys.all, 'diagnosis-task', task] as const,
  researchSummary: () => [...validationKeys.all, 'research-summary'] as const,
  researchTask: (task: string) => [...validationKeys.all, 'research-task', task] as const,
  prescriptionSummary: () => [...validationKeys.all, 'prescription-summary'] as const,
  prescriptionTask: (task: string) => [...validationKeys.all, 'prescription-task', task] as const,
  medicalReportSummary: () => [...validationKeys.all, 'medical-report-summary'] as const,
  medicalReportTask: (task: string) => [...validationKeys.all, 'medical-report-task', task] as const,
};

export function useSelectedRunId(): string | undefined {
  const [params] = useSearchParams();
  return params.get('run') || undefined;
}

export function useValidationOverview(runId?: string) {
  return useQuery({
    queryKey: validationKeys.overview(runId),
    queryFn: () => validationApi.overview(runId),
  });
}

export function useValidationRuns() {
  return useQuery({
    queryKey: validationKeys.runs(),
    queryFn: () => validationApi.runs(),
  });
}

export function useValidationRun(runId: string) {
  return useQuery({
    queryKey: validationKeys.run(runId),
    queryFn: () => validationApi.run(runId),
    enabled: Boolean(runId),
  });
}

export function useValidationAgents(runId?: string) {
  return useQuery({
    queryKey: validationKeys.agents(runId),
    queryFn: () => validationApi.agents(runId),
  });
}

export function useValidationAgent(agentId: string, runId?: string) {
  return useQuery({
    queryKey: validationKeys.agent(agentId, runId),
    queryFn: () => validationApi.agent(agentId, runId),
    enabled: Boolean(agentId),
  });
}

export function useValidationTask(taskId: string, runId?: string) {
  return useQuery({
    queryKey: validationKeys.task(taskId, runId),
    queryFn: () => validationApi.task(taskId, runId),
    enabled: Boolean(taskId),
  });
}

export function useValidationDatasets(runId?: string) {
  return useQuery({
    queryKey: validationKeys.datasets(runId),
    queryFn: () => validationApi.datasets(runId),
  });
}

export function useValidationCases(params: CaseListParams) {
  return useQuery({
    queryKey: validationKeys.cases(params),
    queryFn: () => validationApi.cases(params),
  });
}

export function useValidationCase(caseId: string, runId?: string) {
  return useQuery({
    queryKey: validationKeys.case(caseId, runId),
    queryFn: () => validationApi.case(caseId, runId),
    enabled: Boolean(caseId),
  });
}

export function useValidationErrors(params: ErrorListParams) {
  return useQuery({
    queryKey: validationKeys.errors(params),
    queryFn: () => validationApi.errors(params),
  });
}

export function useValidationSafety(runId?: string) {
  return useQuery({
    queryKey: validationKeys.safety(runId),
    queryFn: () => validationApi.safety(runId),
  });
}

export function useValidationLimitations(runId?: string) {
  return useQuery({
    queryKey: validationKeys.limitations(runId),
    queryFn: () => validationApi.limitations(runId),
  });
}

export function useValidationPresentation(runId?: string) {
  return useQuery({
    queryKey: validationKeys.presentation(runId),
    queryFn: () => validationApi.presentation(runId),
  });
}

export function useValidationHumanReview(runId?: string) {
  return useQuery({
    queryKey: validationKeys.humanReview(runId),
    queryFn: () => validationApi.humanReview(runId),
  });
}

export function useValidationHealth() {
  return useQuery({
    queryKey: validationKeys.health(),
    queryFn: () => validationApi.health(),
  });
}

export function useValidationEvidence(runId?: string) {
  return useQuery({
    queryKey: validationKeys.evidence(runId),
    queryFn: () => validationApi.evidence(runId),
  });
}

export function useValidationMethodology(taskId: string, runId?: string) {
  return useQuery({
    queryKey: validationKeys.methodology(taskId, runId),
    queryFn: () => validationApi.methodology(taskId, runId),
    enabled: Boolean(taskId),
  });
}

export function useValidationCompare(runA: string, runB: string) {
  return useQuery({
    queryKey: validationKeys.compare(runA, runB),
    queryFn: () => validationApi.compare(runA, runB),
    enabled: Boolean(runA && runB),
  });
}

export function useExecutionValidation(
  taskId: string,
  executionId: string | undefined,
  enabled = false,
) {
  return useQuery({
    queryKey: validationKeys.execution(taskId, executionId || ''),
    queryFn: () => validationApi.execution(taskId, executionId!),
    enabled: Boolean(taskId && executionId) && enabled,
    retry: false,
  });
}

export function useIntakeValidationSummary(enabled = false) {
  return useQuery({
    queryKey: validationKeys.intakeSummary(),
    queryFn: () => validationApi.intakeSummary(),
    enabled,
    retry: false,
  });
}

export function useIntakeValidationTask(task: string, enabled = false) {
  return useQuery({
    queryKey: validationKeys.intakeTask(task),
    queryFn: () => validationApi.intakeTask(task),
    enabled: Boolean(task) && enabled,
    retry: false,
  });
}

export function useDiagnosisValidationSummary(enabled = false) {
  return useQuery({
    queryKey: validationKeys.diagnosisSummary(),
    queryFn: () => validationApi.diagnosisSummary(),
    enabled,
    retry: false,
  });
}

export function useDiagnosisValidationTask(task: string, enabled = false) {
  return useQuery({
    queryKey: validationKeys.diagnosisTask(task),
    queryFn: () => validationApi.diagnosisTask(task),
    enabled: Boolean(task) && enabled,
    retry: false,
  });
}

export function useResearchValidationSummary(enabled = false) {
  return useQuery({
    queryKey: validationKeys.researchSummary(),
    queryFn: () => validationApi.researchSummary(),
    enabled,
    retry: false,
  });
}

export function useResearchValidationTask(task: string, enabled = false) {
  return useQuery({
    queryKey: validationKeys.researchTask(task),
    queryFn: () => validationApi.researchTask(task),
    enabled: Boolean(task) && enabled,
    retry: false,
  });
}

export function usePrescriptionValidationSummary(enabled = false) {
  return useQuery({
    queryKey: validationKeys.prescriptionSummary(),
    queryFn: () => validationApi.prescriptionSummary(),
    enabled,
    retry: false,
  });
}

export function usePrescriptionValidationTask(task: string, enabled = false) {
  return useQuery({
    queryKey: validationKeys.prescriptionTask(task),
    queryFn: () => validationApi.prescriptionTask(task),
    enabled: Boolean(task) && enabled,
    retry: false,
  });
}

export function useMedicalReportValidationSummary(enabled = false) {
  return useQuery({
    queryKey: validationKeys.medicalReportSummary(),
    queryFn: () => validationApi.medicalReportSummary(),
    enabled,
    retry: false,
  });
}

export function useMedicalReportValidationTask(task: string, enabled = false) {
  return useQuery({
    queryKey: validationKeys.medicalReportTask(task),
    queryFn: () => validationApi.medicalReportTask(task),
    enabled: Boolean(task) && enabled,
    retry: false,
  });
}
