import { useMemo, useState } from 'react';
import Modal from '@/components/ui/Modal';
import {
  useMedicalReportValidationSummary,
  useMedicalReportValidationTask,
} from '@/hooks/useValidation';
import { formatHeadlineValue, formatPercent } from '@/utils/validationDisplay';
import {
  applyMedicalReportSummaryDemo,
  MEDICAL_REPORT_DEMO_NOTE,
} from '@/utils/medicalReportValidationDemo';
import type { MedicalReportTaskHeadline } from '@/types/executionValidation';

type View = 'list' | 'task';

function statusTone(status: string) {
  if (status === 'VALIDATED') return { icon: '✓', label: 'Validated', className: 'text-emerald-600' };
  if (status === 'PENDING_HUMAN_REVIEW') {
    return { icon: '◷', label: 'Human review', className: 'text-amber-600' };
  }
  if (status === 'NOT_VALIDATABLE' || status === 'NOT_EXECUTED' || status === 'SKIPPED') {
    return { icon: '⚠', label: 'Not Validatable', className: 'text-slate-500' };
  }
  if (status === 'ERROR') return { icon: '✗', label: 'Error', className: 'text-rose-600' };
  return { icon: '✗', label: 'Failed', className: 'text-rose-600' };
}

function shortCaseId(id: string) {
  const match = id.match(/VC-medical_report_[^-]+-(\d+)$/);
  return match ? `case ${match[1]}` : id.replace(/^VC-/, '');
}

function mainMetricLabel(row: MedicalReportTaskHeadline) {
  const metric = row.main_metric;
  if (metric && typeof metric.value === 'number') {
    return `${metric.label}: ${formatHeadlineValue(metric.label, metric.value)}`;
  }
  const cases =
    row.evaluated_cases && row.total_cases
      ? `${row.evaluated_cases}/${row.total_cases} cases`
      : null;
  return cases || row.human_summary || row.status.replace(/_/g, ' ');
}

export default function MedicalReportValidationResults() {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<View>('list');
  const [taskId, setTaskId] = useState('medical_report_insurance_documentation');
  const [caseId, setCaseId] = useState<string | null>(null);
  const summaryQuery = useMedicalReportValidationSummary(open);
  const taskQuery = useMedicalReportValidationTask(taskId, open && view === 'task');
  const tasks = summaryQuery.data
    ? applyMedicalReportSummaryDemo(summaryQuery.data).tasks
    : [];
  const selected = useMemo(
    () => tasks.find((row) => row.task === taskId) || tasks[0],
    [tasks, taskId],
  );
  const detail = taskQuery.data;
  const activeCase =
    (detail?.per_case_results || []).find((row) => row.case_id === caseId) ||
    detail?.per_case_results?.[0];
  const validatedCount = tasks.filter((row) => row.status === 'VALIDATED').length;
  const notValidatable = tasks.filter((row) => row.status === 'NOT_VALIDATABLE').length;
  const casesScored = tasks
    .filter((row) => row.status === 'VALIDATED')
    .reduce((sum, row) => sum + (row.evaluated_cases || 0), 0);
  const casesExecuted = tasks.reduce((sum, row) => sum + (row.evaluated_cases || 0), 0);

  const openTask = (id: string) => {
    setTaskId(id);
    setCaseId(null);
    setView('task');
  };

  const close = () => {
    setOpen(false);
    setView('list');
    setCaseId(null);
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-xl border border-[var(--border-color)] px-3 py-2 text-sm font-medium text-[var(--text-primary)]"
      >
        View Validation Results
      </button>
      <Modal open={open} title="MEDICAL REPORT AGENT VALIDATION" onClose={close} wide>
        {summaryQuery.isLoading ? (
          <p className="text-sm text-[var(--text-secondary)]">Loading Medical Report validation…</p>
        ) : summaryQuery.isError ? (
          <p className="text-sm text-[var(--text-secondary)]">Validation unavailable</p>
        ) : view === 'list' ? (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <SummaryChip label="Validated Tasks" value={`${validatedCount} / ${tasks.length}`} />
              <SummaryChip label="Not Validatable" value={String(notValidatable)} />
              <SummaryChip label="Cases Scored" value={String(casesScored)} />
              <SummaryChip
                label="Execution Success"
                value={
                  casesExecuted
                    ? formatPercent(
                        1 -
                          tasks.reduce((sum, row) => sum + (row.failed_cases || 0), 0) /
                            casesExecuted,
                      )
                    : 'n/a'
                }
              />
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              {MEDICAL_REPORT_DEMO_NOTE}
            </p>
            <p className="text-xs text-[var(--text-secondary)]">
              {summaryQuery.data?.coverage_vs_performance_note}
            </p>
            <div className="divide-y divide-[var(--border-color)] rounded-2xl border border-[var(--border-color)]">
              {tasks.map((row) => {
                const tone = statusTone(row.status);
                return (
                  <div key={row.task} className="flex items-center justify-between gap-3 px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-[var(--text-primary)]">{row.task_label}</p>
                      <p className={`text-xs ${tone.className}`}>
                        {tone.icon} {tone.label}
                        {row.evaluated_cases ? ` · ${row.evaluated_cases} cases` : ''}
                      </p>
                      <p className="mt-1 text-xs text-[var(--text-secondary)]">
                        {mainMetricLabel(row)}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => openTask(row.task)}
                      className="shrink-0 text-sm font-medium text-primary-600"
                    >
                      {'View Results >'}
                    </button>
                  </div>
                );
              })}
            </div>
            {summaryQuery.data?.overall_score_note ? (
              <p className="text-xs text-[var(--text-secondary)]">
                {summaryQuery.data.overall_score_note}
              </p>
            ) : null}
          </div>
        ) : (
          <TaskDetail
            selected={selected}
            detail={taskQuery.data}
            loading={taskQuery.isLoading}
            activeCase={activeCase}
            onBack={() => setView('list')}
            onSelectCase={setCaseId}
          />
        )}
      </Modal>
    </>
  );
}

function SummaryChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--border-color)] px-3 py-2">
      <p className="text-[11px] text-[var(--text-secondary)]">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}

function TaskDetail({
  selected,
  detail,
  loading,
  activeCase,
  onBack,
  onSelectCase,
}: {
  selected?: MedicalReportTaskHeadline;
  detail?: {
    task?: string;
    task_label?: string;
    evaluated_cases?: number;
    total_cases?: number;
    coverage?: number | null;
    status?: string;
    human_summary?: string | null;
    display_metrics?: Array<{ label: string; value: number }>;
    metric_notes?: string[];
    per_case_results?: Array<Record<string, unknown>>;
  };
  loading: boolean;
  activeCase?: Record<string, unknown>;
  onBack: () => void;
  onSelectCase: (id: string) => void;
}) {
  if (!selected) return null;
  const tone = statusTone(detail?.status || selected.status);
  const metrics = detail?.display_metrics || selected.display_metrics || [];
  const cases = detail?.per_case_results || [];
  const produced = String(activeCase?.agent_text || '');
  const reference = String(activeCase?.ground_truth_text || '');
  const status = detail?.status || selected.status;

  return (
    <div className="space-y-5">
      <button type="button" onClick={onBack} className="text-xs text-primary-600">
        ← All Medical Report tasks
      </button>
      <div>
        <h3 className="text-lg font-semibold">{detail?.task_label || selected.task_label}</h3>
        <p className="text-sm text-[var(--text-secondary)]">
          Cases Evaluated: {detail?.evaluated_cases ?? selected.evaluated_cases} /{' '}
          {detail?.total_cases ?? selected.total_cases}
          {(detail?.coverage ?? selected.coverage) != null
            ? ` · Dataset coverage ${formatPercent(detail?.coverage ?? selected.coverage)} (not accuracy)`
            : ''}
        </p>
      </div>
      <p className={`text-sm font-medium ${tone.className}`}>
        {tone.icon} {tone.label.toUpperCase()}
      </p>
      <p className="text-sm text-[var(--text-secondary)]">
        {detail?.human_summary || selected.human_summary}
      </p>
      {metrics.length ? (
        <div className="grid gap-2 sm:grid-cols-3">
          {metrics.map((metric) => (
            <div key={metric.label} className="rounded-xl border border-[var(--border-color)] px-3 py-2">
              <p className="text-xs text-[var(--text-secondary)]">{metric.label}</p>
              <p className="text-xl font-semibold">{formatHeadlineValue(metric.label, metric.value)}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-[var(--text-secondary)]">
          No applicable performance metrics for this task.
        </p>
      )}
      {(detail?.metric_notes || selected.notes || []).map((note) => (
        <p key={note} className="text-xs text-[var(--text-secondary)]">
          {note}
        </p>
      ))}
      {loading ? (
        <p className="text-sm text-[var(--text-secondary)]">Loading task cases…</p>
      ) : cases.length ? (
        <>
          <div className="flex max-h-32 flex-wrap gap-2 overflow-auto">
            {cases.map((row) => {
              const id = String(row.case_id || '');
              const selectedCase = id === String(activeCase?.case_id || '');
              const caseTone = statusTone(String(row.status || ''));
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => onSelectCase(id)}
                  className={`rounded-full px-2 py-1 text-[11px] ${
                    selectedCase
                      ? 'bg-primary-600 text-white'
                      : 'border border-[var(--border-color)] text-[var(--text-secondary)]'
                  }`}
                >
                  {caseTone.icon} {shortCaseId(id)}
                </button>
              );
            })}
          </div>
          {(produced || reference) && status !== 'NOT_VALIDATABLE' ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <TextBlock title="WHAT THE AGENT PRODUCED" text={produced || 'No agent output'} />
              <TextBlock title="WHAT THE DATASET SHOWS" text={reference || 'No ground truth'} />
            </div>
          ) : null}
          {activeCase?.human_summary ? (
            <p className="text-xs text-[var(--text-secondary)]">{String(activeCase.human_summary)}</p>
          ) : null}
        </>
      ) : status === 'NOT_VALIDATABLE' || status === 'PENDING_HUMAN_REVIEW' ? (
        <p className="text-sm text-[var(--text-secondary)]">
          {status === 'PENDING_HUMAN_REVIEW'
            ? 'This task requires human review; no automatic score is produced.'
            : 'Dataset does not contain sufficient ground-truth information for this task.'}
        </p>
      ) : null}
    </div>
  );
}

function TextBlock({ title, text }: { title: string; text: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
        {title}
      </p>
      <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded-xl border border-[var(--border-color)] bg-[var(--bg-primary)]/30 p-3 text-xs">
        {text}
      </pre>
    </div>
  );
}
