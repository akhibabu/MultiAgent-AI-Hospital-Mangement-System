import type { AgentDetail } from '@/types/validation';
import type {
  MedicalReportTaskHeadline,
  MedicalReportValidationSummary,
} from '@/types/executionValidation';

export const MEDICAL_REPORT_DEMO_NOTE =
  'No demonstration metrics are used. Medical Report tasks remain pending until a benchmark run produces measured results.';

export function isMedicalReportAgent(agentId: string): boolean {
  const key = agentId.toLowerCase().replace(/\s+/g, '_').replace(/_agent$/, '');
  return key === 'medical_report';
}

export function applyMedicalReportAgentDemo(data: AgentDetail): AgentDetail {
  return data;
}

export function applyMedicalReportSummaryDemo(
  summary: MedicalReportValidationSummary,
): MedicalReportValidationSummary {
  return summary;
}
