/**
 * Intake Agent — single staff-facing workflow page.
 * Technical OCR/JSON details live only under Developer Mode.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import Badge from '@/components/common/Badge';
import Card from '@/components/common/Card';
import { usePatients } from '@/hooks/usePatients';
import { useDoctors } from '@/hooks/useDoctors';
import { useAppointments } from '@/hooks/useAppointments';
import {
  useProcessingJobs,
  useRegisterForProcessing,
} from '@/hooks/useRegistration';
import {
  useExtractMedicalHistory,
  useMedicalHistory,
} from '@/hooks/useMedicalHistory';
import {
  useOcrResult,
  usePatientContext,
  useStartOcr,
} from '@/hooks/useOcr';
import { useNerResult, useStartNer } from '@/hooks/useNer';
import { useRiskResult, useStartRisk } from '@/hooks/useRisk';
import {
  useKnowledgeGraphResult,
  useStartKnowledgeGraph,
} from '@/hooks/useKnowledgeGraph';
import HighlightedReport from '@/components/ai/HighlightedReport';
import PatientKnowledgeGraphViewer from '@/components/ai/PatientKnowledgeGraphViewer';
import {
  validateMedicalFile,
  formatFileSize,
} from '@/services/medicalStorageService';
import { INTAKE_STAGES, type IntakeStageId } from '@/types/ocr';
import type { ProcessingJob } from '@/types/registration';
import type { EntityStatistics, PatientEntitySummary } from '@/types/ner';
import type { CategoryRisk, RiskAlert } from '@/types/risk';
import { RISK_LEVEL_TONE } from '@/types/risk';
import type {
  GraphNode,
  GraphRelationship,
  GraphStatistics,
  PatientGraphSummary,
} from '@/types/knowledgeGraph';

function niceDocType(mime?: string | null) {
  if (!mime) return 'Document';
  if (mime.includes('pdf')) return 'PDF';
  if (mime.startsWith('image/')) return 'Image';
  return 'Document';
}

function staffText(raw?: string | null) {
  if (!raw) return '';
  // Never show PDF binary / object streams in the clinical UI
  if (
    raw.includes('%PDF-') ||
    raw.includes('endobj') ||
    raw.includes('/FlateDecode') ||
    raw.includes('/FontDescriptor')
  ) {
    return '';
  }
  return raw.trim();
}

function methodLabel(method?: string | null) {
  if (method === 'embedded_text') return 'Embedded text';
  if (method === 'ocr') return 'OCR';
  return method || '—';
}

function docTypeLabel(type?: string | null, mime?: string | null) {
  if (type === 'digital_pdf') return 'Digital PDF';
  if (type === 'scanned_pdf') return 'Scanned PDF';
  if (type === 'image') return 'Image';
  return niceDocType(mime);
}

function readableReportText(ocr?: {
  clean_text?: string | null;
  raw_text?: string | null;
} | null) {
  return staffText(ocr?.clean_text || ocr?.raw_text || '');
}

function previewParagraphs(text: string, count = 3) {
  const clean = staffText(text);
  const parts = clean.split(/\n\n+/).map((p) => p.trim()).filter(Boolean);
  if (parts.length) return parts.slice(0, count).join('\n\n');
  return clean.slice(0, 480);
}

function formatWhen(iso?: string | null) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return `${d.toLocaleDateString()} · ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  } catch {
    return iso;
  }
}

function stageStatus(
  stageId: IntakeStageId,
  job: ProcessingJob | null,
  hasHistory: boolean,
  ocrDone: boolean,
  nerDone: boolean,
  riskDone: boolean,
  kgDone: boolean,
): 'complete' | 'active' | 'future' {
  if (!job) return stageId === 'registration' ? 'active' : 'future';

  if (stageId === 'registration') return 'complete';
  if (stageId === 'history') {
    if (hasHistory) return 'complete';
    return 'active';
  }
  if (stageId === 'context') {
    if (hasHistory) return 'complete';
    return 'future';
  }
  if (stageId === 'ocr') {
    if (ocrDone) return 'complete';
    if (hasHistory) return 'active';
    return 'future';
  }
  if (stageId === 'ner') {
    if (nerDone) return 'complete';
    if (ocrDone) return 'active';
    return 'future';
  }
  if (stageId === 'risk') {
    if (riskDone) return 'complete';
    if (nerDone) return 'active';
    return 'future';
  }
  if (stageId === 'knowledge') {
    if (kgDone) return 'complete';
    if (riskDone) return 'active';
    return 'future';
  }
  return 'future';
}

function progressFor(
  job: ProcessingJob | null,
  ocrDone: boolean,
  nerDone: boolean,
  riskDone: boolean,
  kgDone: boolean,
) {
  if (!job) return 5;
  if (kgDone || job.current_stage === 'Completed' || job.status === 'Completed')
    return 100;
  if (riskDone || job.current_stage === 'Patient Knowledge Graph') return 95;
  if (nerDone || job.current_stage === 'Patient Risk Profiling') return 85;
  if (ocrDone || job.current_stage === 'Medical Entity Recognition') return 70;
  if (job.current_stage === 'OCR') return 55;
  if (job.current_stage === 'Medical History Extraction') return 40;
  if (job.current_stage === 'Patient Registration') return 20;
  return 30;
}

function etaLabel(
  job: ProcessingJob | null,
  ocrDone: boolean,
  nerDone: boolean,
  riskDone: boolean,
  kgDone: boolean,
) {
  if (!job) return 'About 2–4 minutes after upload';
  if (kgDone) return 'Intake complete';
  if (riskDone) return 'Ready for Knowledge Graph';
  if (nerDone) return 'Ready for Risk Profiling';
  if (ocrDone) return 'Ready for Entity Recognition';
  if (job.current_stage === 'OCR') return 'About 30–90 seconds';
  if (job.current_stage === 'Patient Registration') return 'About 1–2 minutes';
  return 'About 1 minute';
}

function riskTone(level?: string | null): 'green' | 'blue' | 'amber' | 'red' | 'gray' {
  if (!level) return 'gray';
  return RISK_LEVEL_TONE[level] || 'gray';
}

export default function IntakeAgentPage() {
  const [patientId, setPatientId] = useState('');
  const [doctorId, setDoctorId] = useState('');
  const [appointmentId, setAppointmentId] = useState('');
  const [jobId, setJobId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [devOpen, setDevOpen] = useState(false);
  const [fullReportOpen, setFullReportOpen] = useState(false);
  const [showUploadForm, setShowUploadForm] = useState(false);

  const patientsQuery = usePatients({
    page: 1,
    page_size: 100,
    sort_by: 'created_at',
    sort_order: 'desc',
  });
  const doctorsQuery = useDoctors({
    page: 1,
    page_size: 100,
    sort_by: 'created_at',
    sort_order: 'desc',
  });
  const appointmentsQuery = useAppointments({
    page: 1,
    page_size: 100,
    patient_id: patientId || undefined,
    doctor_id: doctorId || undefined,
    sort_by: 'appointment_date',
    sort_order: 'desc',
  });
  const jobsQuery = useProcessingJobs(patientId || undefined);
  const historyQuery = useMedicalHistory(patientId || undefined);
  const contextQuery = usePatientContext(patientId || undefined);
  const registerMutation = useRegisterForProcessing();
  const historyMutation = useExtractMedicalHistory(patientId || undefined);
  const ocrMutation = useStartOcr(patientId || undefined);
  const nerMutation = useStartNer(patientId || undefined);
  const riskMutation = useStartRisk(patientId || undefined);
  const kgMutation = useStartKnowledgeGraph(patientId || undefined);

  const jobs = jobsQuery.data ?? [];
  const selectedJob = jobs.find((j) => j.id === jobId) || jobs[0] || null;
  const activeJobId = selectedJob?.id;

  const ocrResultQuery = useOcrResult(
    activeJobId,
    Boolean(
      activeJobId &&
        (selectedJob?.current_stage === 'Medical Entity Recognition' ||
          selectedJob?.current_stage === 'Patient Risk Profiling' ||
          selectedJob?.current_stage === 'Patient Knowledge Graph' ||
          selectedJob?.current_stage === 'Completed' ||
          selectedJob?.status === 'Completed' ||
          contextQuery.data?.ocr_completed ||
          ocrMutation.isSuccess),
    ),
  );

  const nerResultQuery = useNerResult(
    activeJobId,
    Boolean(
      activeJobId &&
        (selectedJob?.current_stage === 'Patient Risk Profiling' ||
          selectedJob?.current_stage === 'Patient Knowledge Graph' ||
          selectedJob?.current_stage === 'Completed' ||
          selectedJob?.status === 'Completed' ||
          selectedJob?.current_stage === 'Medical Entity Recognition' ||
          nerMutation.isSuccess ||
          contextQuery.data?.ocr_completed ||
          ocrMutation.isSuccess),
    ),
  );

  const riskResultQuery = useRiskResult(
    activeJobId,
    Boolean(
      activeJobId &&
        (selectedJob?.current_stage === 'Patient Knowledge Graph' ||
          selectedJob?.current_stage === 'Completed' ||
          selectedJob?.status === 'Completed' ||
          selectedJob?.current_stage === 'Patient Risk Profiling' ||
          riskMutation.isSuccess ||
          nerMutation.isSuccess),
    ),
  );

  const kgResultQuery = useKnowledgeGraphResult(
    activeJobId,
    Boolean(
      activeJobId &&
        (selectedJob?.current_stage === 'Completed' ||
          selectedJob?.status === 'Completed' ||
          selectedJob?.current_stage === 'Patient Knowledge Graph' ||
          kgMutation.isSuccess),
    ),
  );

  useEffect(() => {
    if (jobs.length && !jobId) setJobId(jobs[0].id);
  }, [jobs, jobId]);

  useEffect(() => {
    setAppointmentId('');
  }, [patientId, doctorId]);

  const doctors = doctorsQuery.data?.items ?? [];
  const appointments = useMemo(() => {
    return (appointmentsQuery.data?.items ?? []).filter((a) => {
      if (patientId && a.patient_id !== patientId) return false;
      if (doctorId && a.doctor_id !== doctorId) return false;
      return true;
    });
  }, [appointmentsQuery.data?.items, patientId, doctorId]);

  const history = historyQuery.data?.medical_history;
  const hasHistory = Boolean(history);
  const ocrResult = ocrResultQuery.data || ocrMutation.data?.ocr_result;
  const ocrDone = Boolean(
    contextQuery.data?.ocr_completed ||
      selectedJob?.current_stage === 'Medical Entity Recognition' ||
      selectedJob?.current_stage === 'Patient Risk Profiling' ||
      selectedJob?.current_stage === 'Patient Knowledge Graph' ||
      selectedJob?.current_stage === 'Completed' ||
      selectedJob?.status === 'Completed' ||
      ocrResult,
  );
  const nerResult = nerResultQuery.data || nerMutation.data?.ner_result;
  const nerDone = Boolean(
    (contextQuery.data?.patient_context_json as { ner_metadata?: { completed?: boolean } } | undefined)
      ?.ner_metadata?.completed ||
      selectedJob?.current_stage === 'Patient Risk Profiling' ||
      selectedJob?.current_stage === 'Patient Knowledge Graph' ||
      selectedJob?.current_stage === 'Completed' ||
      selectedJob?.status === 'Completed' ||
      nerResult ||
      nerMutation.isSuccess,
  );
  const riskResult = riskResultQuery.data || riskMutation.data?.risk_profile;
  const riskDone = Boolean(
    (contextQuery.data?.patient_context_json as { risk_metadata?: { completed?: boolean } } | undefined)
      ?.risk_metadata?.completed ||
      selectedJob?.current_stage === 'Patient Knowledge Graph' ||
      selectedJob?.current_stage === 'Completed' ||
      selectedJob?.status === 'Completed' ||
      riskResult ||
      riskMutation.isSuccess,
  );
  const kgResult = kgResultQuery.data || kgMutation.data?.knowledge_graph;
  const kgDone = Boolean(
    (contextQuery.data as { kg_completed?: boolean } | undefined)?.kg_completed ||
      (contextQuery.data?.patient_context_json as { kg_metadata?: { completed?: boolean } } | undefined)
        ?.kg_metadata?.completed ||
      selectedJob?.current_stage === 'Completed' ||
      selectedJob?.status === 'Completed' ||
      kgResult ||
      kgMutation.isSuccess,
  );
  const nerRunning =
    nerMutation.isPending ||
    (selectedJob?.current_stage === 'Medical Entity Recognition' && !nerDone);
  const riskRunning =
    riskMutation.isPending ||
    (selectedJob?.current_stage === 'Patient Risk Profiling' && !riskDone);
  const kgRunning =
    kgMutation.isPending ||
    (selectedJob?.current_stage === 'Patient Knowledge Graph' && !kgDone);
  const ocrRunning = ocrMutation.isPending || selectedJob?.current_stage === 'OCR';
  const progress = progressFor(selectedJob, ocrDone, nerDone, riskDone, kgDone);
  const reportText = readableReportText(ocrResult);
  const textPreview = previewParagraphs(reportText);
  const processingMethod =
    ocrResult?.processing_method ||
    ocrMutation.data?.processing_method ||
    ocrResult?.extraction_method ||
    ocrMutation.data?.extraction_method ||
    (ocrResult?.provenance_json?.processing_method as string | undefined) ||
    (ocrResult?.provenance_json?.extraction_method as string | undefined);
  const lowConfidence =
    ocrResult?.confidence != null && Number(ocrResult.confidence) < 0.7;
  const ocrWarnings = ocrMutation.data?.warnings || [];

  const nerEntities =
    nerMutation.data?.entities ||
    (nerResult?.entities_json as import('@/types/ner').MedicalEntity[] | undefined) ||
    [];
  const nerStats: EntityStatistics | null =
    nerMutation.data?.statistics ||
    (nerResult?.statistics_json as EntityStatistics | undefined) ||
    null;
  const nerSummary: PatientEntitySummary | null =
    nerMutation.data?.summary ||
    (nerResult?.summary_json as PatientEntitySummary | undefined) ||
    null;
  const nerSourceText =
    nerMutation.data?.source_text ||
    nerResult?.source_text_preview ||
    reportText;

  const riskCategories: CategoryRisk[] =
    riskMutation.data?.categories ||
    (riskResult?.categories_json as CategoryRisk[] | undefined) ||
    [];
  const riskAlerts: RiskAlert[] =
    riskMutation.data?.alerts ||
    (riskResult?.alerts_json as RiskAlert[] | undefined) ||
    [];
  const riskFactors =
    riskMutation.data?.top_risk_factors ||
    (riskResult?.top_risk_factors_json as string[] | undefined) ||
    [];
  const riskFindings =
    riskMutation.data?.important_findings ||
    (riskResult?.important_findings_json as string[] | undefined) ||
    [];
  const riskDistribution =
    riskMutation.data?.distribution ||
    (riskResult?.distribution_json as Record<string, number> | undefined) ||
    {};
  const riskTimeline =
    riskMutation.data?.timeline ||
    (riskResult?.timeline_json as Array<Record<string, unknown>> | undefined) ||
    [];
  const overallRiskLevel =
    riskMutation.data?.overall_level || riskResult?.overall_level || null;
  const overallRiskScore =
    riskMutation.data?.overall_score ?? riskResult?.overall_score ?? null;

  const kgNodes: GraphNode[] =
    kgMutation.data?.nodes ||
    (kgResult?.nodes_json as GraphNode[] | undefined) ||
    [];
  const kgRels: GraphRelationship[] =
    kgMutation.data?.relationships ||
    (kgResult?.relationships_json as GraphRelationship[] | undefined) ||
    [];
  const kgStats: GraphStatistics | null =
    kgMutation.data?.statistics ||
    (kgResult?.statistics_json as GraphStatistics | undefined) ||
    null;
  const kgPatientSummary: PatientGraphSummary | null =
    kgMutation.data?.patient_summary ||
    (kgResult?.patient_summary_json as PatientGraphSummary | undefined) ||
    null;
  const kgSummaryText =
    kgMutation.data?.summary || kgResult?.summary || null;

  const patientInfo = history?.patient as
    | {
        full_name?: string;
        patient_number?: string;
        gender?: string;
        blood_group?: string;
        date_of_birth?: string;
      }
    | undefined;

  const timelineItems = useMemo(() => {
    const items: { title: string; when: string; status: string }[] = [];
    if (selectedJob) {
      items.push({
        title: 'Report uploaded',
        when: formatWhen(selectedJob.created_at),
        status: 'Done',
      });
    }
    if (hasHistory) {
      items.push({
        title: 'Medical history extracted',
        when: formatWhen(historyQuery.data?.history_record?.last_updated),
        status: 'Done',
      });
    }
    if (ocrDone) {
      items.push({
        title: 'Document processing completed',
        when: formatWhen(contextQuery.data?.ocr_timestamp || ocrResult?.created_at),
        status: 'Done',
      });
      if (nerDone) {
        items.push({
          title: 'Entities recognized',
          when: formatWhen(nerResult?.created_at || nerMutation.data?.ner_result?.created_at),
          status: 'Done',
        });
        if (riskDone) {
          items.push({
            title: 'Risk profile assessed',
            when: formatWhen(riskResult?.created_at || riskMutation.data?.risk_profile?.created_at),
            status: 'Done',
          });
          if (kgDone) {
            items.push({
              title: 'Knowledge graph created',
              when: formatWhen(kgResult?.created_at || kgMutation.data?.knowledge_graph?.created_at),
              status: 'Done',
            });
            items.push({
              title: 'Intake Agent completed',
              when: 'Done',
              status: 'Complete',
            });
          } else {
            items.push({
              title: 'Patient knowledge graph',
              when: kgRunning ? 'In progress' : 'Ready to start',
              status: kgRunning ? 'Running' : 'Next',
            });
          }
        } else {
          items.push({
            title: 'Patient risk profiling',
            when: riskRunning ? 'In progress' : 'Ready to start',
            status: riskRunning ? 'Running' : 'Next',
          });
        }
      } else {
        items.push({
          title: 'Medical entity recognition',
          when: nerRunning ? 'In progress' : 'Ready to start',
          status: nerRunning ? 'Running' : 'Next',
        });
      }
    } else if (hasHistory) {
      items.push({
        title: 'Document processing (OCR)',
        when: ocrRunning ? 'In progress' : 'Ready to start',
        status: ocrRunning ? 'Running' : 'Next',
      });
    } else if (selectedJob) {
      items.push({
        title: 'Medical history extraction',
        when: 'Ready to start',
        status: 'Next',
      });
    }
    return items;
  }, [
    selectedJob,
    hasHistory,
    ocrDone,
    ocrRunning,
    nerDone,
    nerRunning,
    riskDone,
    riskRunning,
    kgDone,
    kgRunning,
    historyQuery.data?.history_record?.last_updated,
    contextQuery.data?.ocr_timestamp,
    ocrResult?.created_at,
    nerResult?.created_at,
    nerMutation.data?.ner_result?.created_at,
    riskResult?.created_at,
    riskMutation.data?.risk_profile?.created_at,
    kgResult?.created_at,
    kgMutation.data?.knowledge_graph?.created_at,
  ]);

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    if (!patientId || !appointmentId || !doctorId || !file) {
      setFileError('Please select patient, doctor, appointment, and a file');
      return;
    }
    const err = validateMedicalFile(file);
    if (err) {
      setFileError(err);
      return;
    }
    const result = await registerMutation.mutateAsync({
      patient_id: patientId,
      appointment_id: appointmentId,
      doctor_id: doctorId,
      file,
    });
    setJobId(result.job_id);
    setFile(null);
    setShowUploadForm(false);
    jobsQuery.refetch();
  }

  async function handleContinue() {
    if (!activeJobId) return;
    if (!hasHistory || selectedJob?.current_stage === 'Patient Registration') {
      await historyMutation.mutateAsync(activeJobId);
      jobsQuery.refetch();
      contextQuery.refetch();
      return;
    }
    if (!ocrDone || selectedJob?.current_stage === 'OCR') {
      await ocrMutation.mutateAsync(activeJobId);
      jobsQuery.refetch();
      contextQuery.refetch();
      ocrResultQuery.refetch();
      return;
    }
    if (ocrDone && !nerDone) {
      await nerMutation.mutateAsync(activeJobId);
      jobsQuery.refetch();
      contextQuery.refetch();
      nerResultQuery.refetch();
      return;
    }
    if (nerDone && !riskDone) {
      await riskMutation.mutateAsync(activeJobId);
      jobsQuery.refetch();
      contextQuery.refetch();
      riskResultQuery.refetch();
      return;
    }
    if (riskDone && !kgDone) {
      await kgMutation.mutateAsync(activeJobId);
      jobsQuery.refetch();
      contextQuery.refetch();
      kgResultQuery.refetch();
    }
  }

  const primaryActionLabel = !selectedJob
    ? null
    : !hasHistory || selectedJob.current_stage === 'Patient Registration'
      ? historyMutation.isPending
        ? 'Extracting history…'
        : 'Extract medical history'
      : !ocrDone
        ? ocrMutation.isPending
          ? 'Reading document…'
          : 'Start document reading (OCR)'
        : !nerDone
          ? nerMutation.isPending
            ? 'Recognizing entities…'
            : 'Start medical entity recognition'
          : !riskDone
            ? riskMutation.isPending
              ? 'Profiling risk…'
              : 'Start patient risk profiling'
            : !kgDone
              ? kgMutation.isPending
                ? 'Building knowledge graph…'
                : 'Build patient knowledge graph'
              : null;

  const ocrStatusLabel = ocrMutation.isPending
    ? 'Running'
    : ocrDone
      ? 'Completed'
      : selectedJob?.status === 'Failed' && selectedJob.current_stage === 'OCR'
        ? 'Failed'
        : hasHistory
          ? 'Ready'
          : 'Waiting';

  return (
    <ErrorBoundary title="Intake Agent error">
      <div className="mx-auto max-w-6xl space-y-8">
        {/* Header */}
        <header className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary-600">
                AI Center
              </p>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[var(--text-primary)]">
                Intake Agent
              </h1>
              <p className="mt-2 max-w-xl text-sm leading-relaxed text-[var(--text-secondary)]">
                Collects patient information and prepares it for AI diagnosis.
              </p>
            </div>
            <Link
              to="/ai"
              className="rounded-xl border border-[var(--border-color)] px-3 py-2 text-sm text-[var(--text-secondary)] transition hover:border-primary-500/40"
            >
              Back to AI Center
            </Link>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Current status</p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                {selectedJob?.status === 'Failed'
                  ? 'Needs attention'
                  : kgDone
                    ? 'Intake completed'
                    : riskDone
                      ? 'Ready for Knowledge Graph'
                      : nerDone
                        ? 'Ready for risk profiling'
                        : ocrDone
                          ? 'Ready for entity recognition'
                          : selectedJob
                            ? 'In progress'
                            : 'Waiting to start'}
              </p>
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Current stage</p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                {kgDone
                  ? 'Completed'
                  : riskDone
                    ? 'Patient Knowledge Graph'
                    : nerDone
                      ? 'Patient Risk Profiling'
                      : ocrDone
                        ? 'Medical Entity Recognition'
                        : selectedJob?.current_stage === 'OCR'
                          ? 'Document Processing'
                          : selectedJob?.current_stage || 'Patient Registration'}
              </p>
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Overall progress</p>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-black/5 dark:bg-white/10">
                <div
                  className="h-full rounded-full bg-primary-600 transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="mt-1 text-xs text-[var(--text-secondary)]">{progress}%</p>
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Estimated time</p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                {etaLabel(selectedJob, ocrDone, nerDone, riskDone, kgDone)}
              </p>
            </Card>
          </div>
        </header>

        {/* Patient picker — minimal */}
        <Card>
          <div className="flex flex-wrap items-end gap-3">
            <label className="min-w-[220px] flex-1 text-sm">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Patient</span>
              <select
                className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5"
                value={patientId}
                onChange={(e) => {
                  setPatientId(e.target.value);
                  setJobId('');
                }}
              >
                <option value="">Select a patient…</option>
                {(patientsQuery.data?.items ?? []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.first_name} {p.last_name}
                    {p.patient_number ? ` (${p.patient_number})` : ''}
                  </option>
                ))}
              </select>
            </label>
            {patientId ? (
              <button
                type="button"
                onClick={() => setShowUploadForm((v) => !v)}
                className="rounded-xl border border-[var(--border-color)] px-4 py-2.5 text-sm"
              >
                {showUploadForm ? 'Hide upload' : 'Upload new report'}
              </button>
            ) : null}
            {primaryActionLabel ? (
              <button
                type="button"
                disabled={
                  historyMutation.isPending ||
                  ocrMutation.isPending ||
                  nerMutation.isPending ||
                  riskMutation.isPending ||
                  kgMutation.isPending
                }
                onClick={handleContinue}
                className="rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
              >
                {primaryActionLabel}
              </button>
            ) : null}
          </div>

          {showUploadForm ? (
            <form
              onSubmit={handleRegister}
              className="mt-5 grid gap-3 border-t border-[var(--border-color)] pt-5 md:grid-cols-2"
            >
              <label className="text-sm">
                <span className="mb-1.5 block text-[var(--text-secondary)]">Doctor</span>
                <select
                  required
                  className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5"
                  value={doctorId}
                  onChange={(e) => setDoctorId(e.target.value)}
                >
                  <option value="">Select doctor…</option>
                  {doctors.map((d) => (
                    <option key={d.id} value={d.id}>
                      Dr. {d.first_name} {d.last_name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                <span className="mb-1.5 block text-[var(--text-secondary)]">
                  Appointment
                </span>
                <select
                  required
                  disabled={!doctorId}
                  className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5 disabled:opacity-50"
                  value={appointmentId}
                  onChange={(e) => setAppointmentId(e.target.value)}
                >
                  <option value="">Select appointment…</option>
                  {appointments.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.appointment_number} · {a.appointment_date}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm md:col-span-2">
                <span className="mb-1.5 block text-[var(--text-secondary)]">
                  Medical report
                </span>
                <input
                  type="file"
                  accept=".pdf,.png,.jpeg,.jpg,.webp"
                  onChange={(e) => {
                    const f = e.target.files?.[0] ?? null;
                    setFile(f);
                    setFileError(f ? validateMedicalFile(f) : null);
                  }}
                />
                {file ? (
                  <p className="mt-1 text-xs text-[var(--text-secondary)]">
                    {file.name} · {formatFileSize(file.size)}
                  </p>
                ) : null}
                {fileError ? (
                  <p className="mt-1 text-xs text-red-600">{fileError}</p>
                ) : null}
              </label>
              <button
                type="submit"
                disabled={registerMutation.isPending || Boolean(fileError)}
                className="rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50 md:col-span-2"
              >
                {registerMutation.isPending ? 'Uploading…' : 'Register report'}
              </button>
            </form>
          ) : null}
        </Card>

        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          {/* Workflow */}
          <Card>
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">
              Workflow
            </h2>
            <ol className="mt-5 space-y-0">
              {INTAKE_STAGES.map((stage, i) => {
                const status = stageStatus(
                  stage.id,
                  selectedJob,
                  hasHistory,
                  ocrDone,
                  nerDone,
                  riskDone,
                  kgDone,
                );
                return (
                  <li key={stage.id} className="relative flex gap-3 pb-5 last:pb-0">
                    {i < INTAKE_STAGES.length - 1 ? (
                      <span className="absolute left-[11px] top-7 h-[calc(100%-12px)] w-px bg-[var(--border-color)]" />
                    ) : null}
                    <span
                      className={`relative z-10 mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                        status === 'complete'
                          ? 'bg-emerald-500 text-white'
                          : status === 'active'
                            ? 'animate-pulse bg-primary-600 text-white'
                            : 'border border-[var(--border-color)] text-[var(--text-secondary)]'
                      }`}
                    >
                      {status === 'complete' ? '✓' : status === 'active' ? '…' : ''}
                    </span>
                    <div className={status === 'future' ? 'opacity-50' : ''}>
                      <p className="text-sm font-medium text-[var(--text-primary)]">
                        {stage.label}
                      </p>
                      <p className="mt-0.5 text-xs leading-relaxed text-[var(--text-secondary)]">
                        {stage.description}
                      </p>
                      <p className="mt-1 text-[10px] uppercase tracking-wide text-[var(--text-secondary)]">
                        {status === 'complete'
                          ? 'Completed'
                          : status === 'active'
                            ? 'In progress'
                            : 'Upcoming'}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </Card>

          <div className="space-y-6">
            {/* Current stage card */}
            {(hasHistory || ocrRunning || ocrDone) && (
              <Card>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[var(--text-secondary)]">
                      Current stage
                    </p>
                    <h2 className="mt-1 text-lg font-semibold text-[var(--text-primary)]">
                      {kgDone
                        ? 'Intake Agent Completed'
                        : riskDone
                          ? 'Patient Knowledge Graph'
                          : nerDone
                            ? 'Patient Risk Profiling'
                            : ocrDone
                              ? 'Medical Entity Recognition'
                              : 'Document Processing'}
                    </h2>
                    <p className="mt-1 max-w-lg text-sm text-[var(--text-secondary)]">
                      {kgDone
                        ? 'All intake stages finished. The Patient Knowledge Graph is ready for downstream AI agents.'
                        : riskDone
                          ? 'Risk profiling is complete. Build the knowledge graph to finish intake.'
                          : nerDone
                            ? 'Estimate clinical risk categories from recognized entities and history. Decision-support only — not a diagnosis.'
                            : ocrDone
                              ? 'Identify diseases, medications, symptoms, vitals, and other medical entities from the cleaned report. Recognition only — no diagnosis.'
                              : 'Extract readable text from digital PDFs or images.'}
                    </p>
                  </div>
                  <Badge
                    tone={
                      kgDone
                        ? 'green'
                        : kgRunning || riskRunning || nerRunning
                          ? 'blue'
                          : riskDone
                            ? 'amber'
                            : nerDone || ocrDone
                              ? nerDone
                                ? 'green'
                                : ocrDone
                                  ? 'amber'
                                  : 'green'
                              : ocrStatusLabel === 'Running'
                                ? 'blue'
                                : ocrStatusLabel === 'Failed'
                                  ? 'red'
                                  : 'amber'
                    }
                  >
                    {kgDone
                      ? 'Completed'
                      : kgRunning
                        ? 'Running'
                        : riskRunning
                          ? 'Running'
                          : nerRunning
                            ? 'Running'
                            : riskDone
                              ? 'Ready'
                              : nerDone
                                ? 'Completed'
                                : ocrDone
                                  ? 'Ready'
                                  : ocrStatusLabel}
                  </Badge>
                </div>

                {ocrDone ? (
                  <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    <div>
                      <p className="text-xs text-[var(--text-secondary)]">Diseases</p>
                      <p className="mt-1 text-sm font-medium">
                        {nerStats?.disease_count ?? '—'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--text-secondary)]">Medications</p>
                      <p className="mt-1 text-sm font-medium">
                        {nerStats?.medication_count ?? '—'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--text-secondary)]">Symptoms</p>
                      <p className="mt-1 text-sm font-medium">
                        {nerStats?.symptom_count ?? '—'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--text-secondary)]">Allergies</p>
                      <p className="mt-1 text-sm font-medium">
                        {nerStats?.allergy_count ?? '—'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--text-secondary)]">Vitals</p>
                      <p className="mt-1 text-sm font-medium">
                        {nerStats?.vital_count ?? '—'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--text-secondary)]">Lab tests</p>
                      <p className="mt-1 text-sm font-medium">
                        {nerStats?.lab_test_count ?? '—'}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    <div>
                      <p className="text-xs text-[var(--text-secondary)]">Progress</p>
                      <div className="mt-2 h-2 overflow-hidden rounded-full bg-black/5 dark:bg-white/10">
                        <div
                          className="h-full rounded-full bg-primary-600 transition-all"
                          style={{
                            width: `${ocrDone ? 100 : ocrRunning ? 65 : hasHistory ? 10 : 0}%`,
                          }}
                        />
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--text-secondary)]">Pages processed</p>
                      <p className="mt-1 text-sm font-medium">
                        {ocrResult?.page_count ?? '—'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--text-secondary)]">Next stage</p>
                      <p className="mt-1 text-sm font-medium">
                        Medical Entity Recognition
                      </p>
                    </div>
                  </div>
                )}
              </Card>
            )}

            {/* Uploaded documents */}
            <Card>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                Uploaded documents
              </h2>
              {!jobs.length ? (
                <p className="mt-3 text-sm text-[var(--text-secondary)]">
                  No reports yet. Upload a medical report to begin.
                </p>
              ) : (
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {jobs.map((job) => {
                    const jobOcrDone =
                      job.current_stage === 'Medical Entity Recognition' ||
                      job.current_stage === 'Patient Risk Profiling' ||
                      job.current_stage === 'Patient Knowledge Graph' ||
                      job.current_stage === 'Completed' ||
                      job.status === 'Completed' ||
                      (job.id === activeJobId && ocrDone);
                    const jobNerDone =
                      job.current_stage === 'Patient Risk Profiling' ||
                      job.current_stage === 'Patient Knowledge Graph' ||
                      job.current_stage === 'Completed' ||
                      job.status === 'Completed' ||
                      (job.id === activeJobId && nerDone);
                    const jobRiskDone =
                      job.current_stage === 'Patient Knowledge Graph' ||
                      job.current_stage === 'Completed' ||
                      job.status === 'Completed' ||
                      (job.id === activeJobId && riskDone);
                    const jobKgDone =
                      job.current_stage === 'Completed' ||
                      job.status === 'Completed' ||
                      (job.id === activeJobId && kgDone);
                    return (
                      <div
                        key={job.id}
                        className={`rounded-xl border p-4 transition ${
                          job.id === activeJobId
                            ? 'border-primary-500/50 bg-primary-600/5'
                            : 'border-[var(--border-color)]'
                        }`}
                      >
                        <button
                          type="button"
                          className="w-full text-left"
                          onClick={() => setJobId(job.id)}
                        >
                          <p className="truncate text-sm font-medium text-[var(--text-primary)]">
                            {job.document_name}
                          </p>
                          <p className="mt-1 text-xs text-[var(--text-secondary)]">
                            {niceDocType(job.document_type)} ·{' '}
                            {formatWhen(job.created_at)}
                          </p>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <Badge tone="gray">{job.status}</Badge>
                            <Badge tone={jobOcrDone ? 'green' : 'amber'}>
                              OCR {jobOcrDone ? 'done' : 'pending'}
                            </Badge>
                            <Badge tone={jobNerDone ? 'green' : 'gray'}>
                              NER {jobNerDone ? 'done' : 'pending'}
                            </Badge>
                            <Badge tone={jobRiskDone ? 'green' : 'gray'}>
                              Risk {jobRiskDone ? 'done' : 'pending'}
                            </Badge>
                            <Badge tone={jobKgDone ? 'green' : 'gray'}>
                              KG {jobKgDone ? 'done' : 'pending'}
                            </Badge>
                          </div>
                        </button>
                        {job.id === activeJobId && ocrDone ? (
                          <button
                            type="button"
                            className="mt-3 text-xs font-medium text-primary-600"
                            onClick={() => setFullReportOpen(true)}
                          >
                            View report
                          </button>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              )}
            </Card>

            {/* Document processing summary */}
            {ocrDone && ocrResult ? (
              <Card>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="green">Document processed</Badge>
                  {lowConfidence ? (
                    <Badge tone="amber">Low confidence — review text</Badge>
                  ) : null}
                </div>
                {ocrWarnings.length ? (
                  <ul className="mt-3 space-y-1 text-sm text-amber-800 dark:text-amber-200">
                    {ocrWarnings.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                ) : null}
                <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <div>
                    <p className="text-xs text-[var(--text-secondary)]">Document name</p>
                    <p className="mt-1 truncate text-sm font-medium">
                      {selectedJob?.document_name || '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-[var(--text-secondary)]">Document type</p>
                    <p className="mt-1 text-sm font-medium">
                      {docTypeLabel(
                        ocrResult.document_type ||
                          ocrMutation.data?.document_type,
                        selectedJob?.document_type,
                      )}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-[var(--text-secondary)]">
                      Processing method
                    </p>
                    <p className="mt-1 text-sm font-medium">
                      {methodLabel(processingMethod)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-[var(--text-secondary)]">Status</p>
                    <p className="mt-1 text-sm font-medium">
                      {ocrResult.status ||
                        ocrResult.document_status ||
                        ocrMutation.data?.document_status ||
                        'Completed'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-[var(--text-secondary)]">Confidence</p>
                    <p className="mt-1 text-sm font-medium">
                      {(Number(ocrResult.confidence || 0) * 100).toFixed(0)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-[var(--text-secondary)]">Pages</p>
                    <p className="mt-1 text-sm font-medium">{ocrResult.page_count}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[var(--text-secondary)]">Language</p>
                    <p className="mt-1 text-sm font-medium">
                      {ocrResult.detected_language || '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-[var(--text-secondary)]">Processing time</p>
                    <p className="mt-1 text-sm font-medium">
                      {ocrResult.processing_time_ms != null
                        ? `${(ocrResult.processing_time_ms / 1000).toFixed(1)}s`
                        : '—'}
                    </p>
                  </div>
                </div>
                <div className="mt-5">
                  <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                    Text preview
                  </p>
                  <div className="mt-2 rounded-xl border border-[var(--border-color)] bg-[var(--bg-primary)]/40 p-4">
                    <p className="whitespace-pre-wrap font-serif text-sm leading-relaxed text-[var(--text-primary)]">
                      {textPreview ||
                        'No readable text was found. For scanned documents, ensure PaddleOCR or Tesseract is installed and retry.'}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setFullReportOpen(true)}
                    className="mt-3 text-sm font-medium text-primary-600"
                  >
                    View full report
                  </button>
                </div>
              </Card>
            ) : null}

            {/* Medical Entity Recognition */}
            {ocrDone ? (
              <Card>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                      Medical Entity Recognition
                    </h2>
                    <p className="mt-1 text-sm text-[var(--text-secondary)]">
                      Structured findings from the cleaned report text.
                    </p>
                  </div>
                  {nerDone ? (
                    <Badge tone="green">Entities recognized</Badge>
                  ) : (
                    <Badge tone="amber">Pending</Badge>
                  )}
                </div>

                {!nerDone ? (
                  <div className="mt-4">
                    <p className="text-sm text-[var(--text-secondary)]">
                      Run entity recognition to highlight diseases, medications,
                      symptoms, vitals, and more. This stage does not diagnose.
                    </p>
                    <button
                      type="button"
                      disabled={nerMutation.isPending || !activeJobId}
                      onClick={() => activeJobId && nerMutation.mutate(activeJobId)}
                      className="mt-4 rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
                    >
                      {nerMutation.isPending
                        ? 'Recognizing…'
                        : 'Start medical entity recognition'}
                    </button>
                  </div>
                ) : (
                  <div className="mt-5 space-y-6">
                    {(nerMutation.data?.warnings || []).length ? (
                      <ul className="space-y-1 text-sm text-amber-800 dark:text-amber-200">
                        {(nerMutation.data?.warnings || []).map((w) => (
                          <li key={w}>{w}</li>
                        ))}
                      </ul>
                    ) : null}

                    <div>
                      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                        Entity statistics
                      </p>
                      <div className="mt-3 grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
                        {[
                          ['Diseases', nerStats?.disease_count],
                          ['Medications', nerStats?.medication_count],
                          ['Symptoms', nerStats?.symptom_count],
                          ['Allergies', nerStats?.allergy_count],
                          ['Vitals', nerStats?.vital_count],
                          ['Lab tests', nerStats?.lab_test_count],
                        ].map(([label, count]) => (
                          <div
                            key={String(label)}
                            className="rounded-xl border border-[var(--border-color)] px-3 py-2"
                          >
                            <p className="text-[11px] text-[var(--text-secondary)]">
                              {label}
                            </p>
                            <p className="mt-1 text-lg font-semibold">
                              {count ?? 0}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>

                    {nerSummary ? (
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                          Medical entity summary
                        </p>
                        <div className="mt-3 grid gap-4 sm:grid-cols-2 text-sm">
                          <div>
                            <p className="text-xs text-[var(--text-secondary)]">Conditions</p>
                            <p className="mt-1">
                              {nerSummary.conditions?.length
                                ? nerSummary.conditions.join(', ')
                                : '—'}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-[var(--text-secondary)]">
                              Current medications
                            </p>
                            <p className="mt-1">
                              {nerSummary.current_medications?.length
                                ? nerSummary.current_medications
                                    .map((m) =>
                                      [m.name, m.dosage, m.frequency]
                                        .filter(Boolean)
                                        .join(' '),
                                    )
                                    .join('; ')
                                : '—'}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-[var(--text-secondary)]">Symptoms</p>
                            <p className="mt-1">
                              {nerSummary.symptoms?.length
                                ? nerSummary.symptoms.join(', ')
                                : '—'}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-[var(--text-secondary)]">Allergies</p>
                            <p className="mt-1">
                              {nerSummary.allergies?.length
                                ? nerSummary.allergies.join(', ')
                                : '—'}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-[var(--text-secondary)]">Recent tests</p>
                            <p className="mt-1">
                              {nerSummary.recent_tests?.length
                                ? nerSummary.recent_tests.join(', ')
                                : '—'}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-[var(--text-secondary)]">
                              Recent procedures
                            </p>
                            <p className="mt-1">
                              {nerSummary.recent_procedures?.length
                                ? nerSummary.recent_procedures.join(', ')
                                : '—'}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-[var(--text-secondary)]">Follow-up</p>
                            <p className="mt-1">
                              {nerSummary.follow_up?.length
                                ? nerSummary.follow_up.join(', ')
                                : '—'}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-[var(--text-secondary)]">
                              Doctors / Hospitals
                            </p>
                            <p className="mt-1">
                              {[
                                ...(nerSummary.doctors || []),
                                ...(nerSummary.hospitals || []),
                              ].join(', ') || '—'}
                            </p>
                          </div>
                        </div>
                      </div>
                    ) : null}

                    <div>
                      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                        Interactive highlighted report
                      </p>
                      <div className="mb-3 flex flex-wrap gap-2 text-[11px]">
                        {[
                          ['Disease', 'bg-red-500/20 text-red-800'],
                          ['Medication', 'bg-blue-500/20 text-blue-800'],
                          ['Symptom', 'bg-orange-500/20 text-orange-800'],
                          ['Lab Value', 'bg-purple-500/20 text-purple-800'],
                          ['Allergy', 'bg-yellow-400/30 text-yellow-900'],
                          ['Date', 'bg-emerald-500/20 text-emerald-800'],
                        ].map(([label, cls]) => (
                          <span
                            key={label}
                            className={`rounded px-2 py-0.5 ${cls}`}
                          >
                            {label}
                          </span>
                        ))}
                      </div>
                      <HighlightedReport
                        text={nerSourceText || reportText}
                        entities={nerEntities}
                      />
                    </div>

                    <div>
                      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                        Recognized entities
                      </p>
                      <ul className="mt-3 max-h-56 space-y-2 overflow-auto text-sm">
                        {nerEntities.length ? (
                          nerEntities.map((e, idx) => (
                            <li
                              key={`${e.type}-${e.value}-${idx}`}
                              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--border-color)] px-3 py-2"
                            >
                              <div>
                                <span className="text-xs text-[var(--text-secondary)]">
                                  {e.type}
                                </span>
                                <p className="font-medium">{e.value}</p>
                              </div>
                              <span className="text-xs text-[var(--text-secondary)]">
                                {(e.confidence * 100).toFixed(0)}%
                              </span>
                            </li>
                          ))
                        ) : (
                          <li className="text-[var(--text-secondary)]">
                            No entities recognized.
                          </li>
                        )}
                      </ul>
                    </div>
                  </div>
                )}
              </Card>
            ) : null}

            {/* Patient Risk Profiling */}
            {nerDone ? (
              <Card>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                      Patient Risk Profiling
                    </h2>
                    <p className="mt-1 text-sm text-[var(--text-secondary)]">
                      Decision-support risk estimates from entities and history.
                      Does not diagnose or prescribe.
                    </p>
                  </div>
                  {riskDone ? (
                    <Badge tone={riskTone(overallRiskLevel)}>
                      {overallRiskLevel || 'Completed'}
                    </Badge>
                  ) : (
                    <Badge tone="amber">Pending</Badge>
                  )}
                </div>

                {!riskDone ? (
                  <div className="mt-4">
                    <p className="text-sm text-[var(--text-secondary)]">
                      Run risk profiling to estimate cardiovascular, diabetes,
                      respiratory, emergency, and other risk categories.
                    </p>
                    <button
                      type="button"
                      disabled={riskMutation.isPending || !activeJobId}
                      onClick={() => activeJobId && riskMutation.mutate(activeJobId)}
                      className="mt-4 rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
                    >
                      {riskMutation.isPending
                        ? 'Profiling…'
                        : 'Start patient risk profiling'}
                    </button>
                  </div>
                ) : (
                  <div className="mt-5 space-y-6">
                    {(riskMutation.data?.warnings || []).length ? (
                      <ul className="space-y-1 text-sm text-amber-800 dark:text-amber-200">
                        {(riskMutation.data?.warnings || []).map((w) => (
                          <li key={w}>{w}</li>
                        ))}
                      </ul>
                    ) : null}

                    {/* Overall risk + gauge */}
                    <div className="grid gap-4 lg:grid-cols-[1fr_220px]">
                      <div className="rounded-xl border border-[var(--border-color)] p-4">
                        <p className="text-xs uppercase tracking-wide text-[var(--text-secondary)]">
                          Overall health risk
                        </p>
                        <div className="mt-2 flex flex-wrap items-end gap-3">
                          <p className="text-3xl font-semibold text-[var(--text-primary)]">
                            {overallRiskLevel || '—'}
                          </p>
                          <p className="pb-1 text-sm text-[var(--text-secondary)]">
                            Score {overallRiskScore != null ? overallRiskScore.toFixed(0) : '—'} / 100
                          </p>
                        </div>
                        <div className="mt-4 h-3 overflow-hidden rounded-full bg-black/5 dark:bg-white/10">
                          <div
                            className={`h-full rounded-full transition-all ${
                              (overallRiskScore || 0) >= 76
                                ? 'bg-red-600'
                                : (overallRiskScore || 0) >= 51
                                  ? 'bg-orange-500'
                                  : (overallRiskScore || 0) >= 31
                                    ? 'bg-amber-500'
                                    : 'bg-emerald-500'
                            }`}
                            style={{
                              width: `${Math.min(100, Math.max(4, overallRiskScore || 0))}%`,
                            }}
                          />
                        </div>
                        <p className="mt-3 text-xs text-[var(--text-secondary)]">
                          {riskMutation.data?.disclaimer ||
                            riskResult?.disclaimer ||
                            'Clinical decision-support only.'}
                        </p>
                        <p className="mt-2 text-xs text-[var(--text-secondary)]">
                          {kgDone
                            ? 'Knowledge graph complete — Intake Agent finished.'
                            : 'Suggested next stage: Patient Knowledge Graph'}
                        </p>
                      </div>

                      <div className="rounded-xl border border-[var(--border-color)] p-4">
                        <p className="text-xs uppercase tracking-wide text-[var(--text-secondary)]">
                          Risk distribution
                        </p>
                        <ul className="mt-3 space-y-2 text-sm">
                          {['Critical', 'High', 'Moderate', 'Low', 'Very Low'].map(
                            (lvl) => (
                              <li
                                key={lvl}
                                className="flex items-center justify-between"
                              >
                                <span>{lvl}</span>
                                <span className="font-medium">
                                  {riskDistribution[lvl] ?? 0}
                                </span>
                              </li>
                            ),
                          )}
                        </ul>
                      </div>
                    </div>

                    {/* Risk cards */}
                    <div>
                      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                        Risk breakdown
                      </p>
                      <div className="mt-3 grid gap-3 sm:grid-cols-2">
                        {riskCategories.map((cat) => (
                          <div
                            key={cat.name}
                            className="rounded-xl border border-[var(--border-color)] p-4"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <p className="text-sm font-semibold">{cat.name}</p>
                              <Badge tone={riskTone(cat.level)}>{cat.level}</Badge>
                            </div>
                            <p className="mt-2 text-xs text-[var(--text-secondary)]">
                              Score {Number(cat.score).toFixed(0)} · Confidence{' '}
                              {(Number(cat.confidence) * 100).toFixed(0)}%
                            </p>
                            <p className="mt-2 text-sm leading-relaxed">
                              {cat.reason}
                            </p>
                            {cat.evidence?.length ? (
                              <ul className="mt-2 space-y-1 text-xs text-[var(--text-secondary)]">
                                {cat.evidence.slice(0, 3).map((ev) => (
                                  <li key={ev}>• {ev}</li>
                                ))}
                              </ul>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Top factors + findings */}
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                          Top risk factors
                        </p>
                        <ul className="mt-3 space-y-2 text-sm">
                          {riskFactors.length ? (
                            riskFactors.map((f) => (
                              <li
                                key={f}
                                className="rounded-lg border border-[var(--border-color)] px-3 py-2"
                              >
                                {f}
                              </li>
                            ))
                          ) : (
                            <li className="text-[var(--text-secondary)]">None</li>
                          )}
                        </ul>
                      </div>
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                          Most important findings
                        </p>
                        <ul className="mt-3 space-y-2 text-sm">
                          {riskFindings.length ? (
                            riskFindings.map((f) => (
                              <li
                                key={f}
                                className="rounded-lg border border-[var(--border-color)] px-3 py-2"
                              >
                                {f}
                              </li>
                            ))
                          ) : (
                            <li className="text-[var(--text-secondary)]">None</li>
                          )}
                        </ul>
                      </div>
                    </div>

                    {/* Alerts */}
                    <div>
                      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                        Alerts
                      </p>
                      <ul className="mt-3 space-y-2">
                        {riskAlerts.map((a, i) => (
                          <li
                            key={`${a.message}-${i}`}
                            className={`rounded-xl border px-3 py-2 text-sm ${
                              a.severity === 'critical'
                                ? 'border-red-500/40 bg-red-500/10 text-red-800 dark:text-red-200'
                                : a.severity === 'warning'
                                  ? 'border-amber-500/40 bg-amber-500/10 text-amber-900 dark:text-amber-100'
                                  : 'border-[var(--border-color)] text-[var(--text-secondary)]'
                            }`}
                          >
                            {a.message}
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Timeline */}
                    <div>
                      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
                        Risk timeline
                      </p>
                      <ol className="mt-3 space-y-3">
                        {riskTimeline.length ? (
                          riskTimeline.map((ev, i) => (
                            <li
                              key={`${String(ev.label)}-${i}`}
                              className="flex gap-3 text-sm"
                            >
                              <span className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full bg-primary-600" />
                              <div>
                                <p className="font-medium">
                                  {String(ev.label || 'Event')}
                                  {ev.level ? (
                                    <span className="ml-2 text-xs text-[var(--text-secondary)]">
                                      {String(ev.level)}
                                    </span>
                                  ) : null}
                                </p>
                                <p className="text-xs text-[var(--text-secondary)]">
                                  {String(ev.detail || '')}
                                </p>
                              </div>
                            </li>
                          ))
                        ) : (
                          <li className="text-sm text-[var(--text-secondary)]">
                            No timeline events.
                          </li>
                        )}
                      </ol>
                    </div>
                  </div>
                )}
              </Card>
            ) : null}

            {/* Patient Knowledge Graph — final stage */}
            {riskDone ? (
              <Card>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                      Patient Knowledge Graph
                    </h2>
                    <p className="mt-1 text-sm text-[var(--text-secondary)]">
                      Unified structured knowledge for every downstream AI agent.
                    </p>
                  </div>
                  {kgDone ? (
                    <Badge tone="green">Completed</Badge>
                  ) : (
                    <Badge tone="amber">Pending</Badge>
                  )}
                </div>

                {!kgDone ? (
                  <div className="mt-4">
                    <p className="text-sm text-[var(--text-secondary)]">
                      Build the patient knowledge graph from context, entities,
                      medications, allergies, vitals, labs, procedures, and risk
                      profile.
                    </p>
                    <button
                      type="button"
                      disabled={kgMutation.isPending || !activeJobId}
                      onClick={() => activeJobId && kgMutation.mutate(activeJobId)}
                      className="mt-4 rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
                    >
                      {kgMutation.isPending
                        ? 'Building graph…'
                        : 'Build patient knowledge graph'}
                    </button>
                  </div>
                ) : (
                  <div className="mt-5 space-y-6">
                    <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-4">
                      <p className="text-base font-semibold text-emerald-800 dark:text-emerald-200">
                        🎉 Intake Agent Completed Successfully
                      </p>
                      <ul className="mt-3 space-y-1 text-sm text-emerald-900/90 dark:text-emerald-100/90">
                        <li>✓ Registration Complete</li>
                        <li>✓ History Extraction Complete</li>
                        <li>✓ Patient Context Complete</li>
                        <li>✓ Document Processing Complete</li>
                        <li>✓ Medical Entity Recognition Complete</li>
                        <li>✓ Risk Profiling Complete</li>
                        <li>✓ Knowledge Graph Complete</li>
                      </ul>
                      <p className="mt-3 text-xs text-emerald-800/80 dark:text-emerald-200/80">
                        The Patient Knowledge Graph is now the primary structured
                        knowledge source for Diagnosis, Research, and other agents.
                      </p>
                    </div>

                    {(kgMutation.data?.warnings || []).length ? (
                      <ul className="space-y-1 text-sm text-amber-800 dark:text-amber-200">
                        {(kgMutation.data?.warnings || []).map((w) => (
                          <li key={w}>{w}</li>
                        ))}
                      </ul>
                    ) : null}

                    <PatientKnowledgeGraphViewer
                      nodes={kgNodes}
                      relationships={kgRels}
                      statistics={kgStats}
                      patientSummary={kgPatientSummary}
                      summary={kgSummaryText}
                      graphVersion={
                        kgMutation.data?.graph_version ||
                        kgResult?.graph_version ||
                        1
                      }
                      nodeCount={
                        kgMutation.data?.node_count ||
                        kgResult?.node_count ||
                        kgNodes.length
                      }
                      relationshipCount={
                        kgMutation.data?.relationship_count ||
                        kgResult?.relationship_count ||
                        kgRels.length
                      }
                    />
                  </div>
                )}
              </Card>
            ) : null}

            {/* Patient context — clinical */}
            <Card>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                Patient summary
              </h2>
              {!patientId ? (
                <p className="mt-3 text-sm text-[var(--text-secondary)]">
                  Select a patient to view their clinical summary.
                </p>
              ) : !history ? (
                <p className="mt-3 text-sm text-[var(--text-secondary)]">
                  Run medical history extraction to build the patient summary.
                </p>
              ) : (
                <div className="mt-5 space-y-5 text-sm">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[var(--text-secondary)]">
                      Patient information
                    </p>
                    <p className="mt-1 font-medium text-[var(--text-primary)]">
                      {patientInfo?.full_name || '—'}
                      {patientInfo?.patient_number
                        ? ` · ${patientInfo.patient_number}`
                        : ''}
                    </p>
                    <p className="mt-1 text-[var(--text-secondary)]">
                      {[patientInfo?.gender, patientInfo?.blood_group, patientInfo?.date_of_birth]
                        .filter(Boolean)
                        .join(' · ') || '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[var(--text-secondary)]">
                      Allergies
                    </p>
                    <p className="mt-1">
                      {history.allergies?.length
                        ? history.allergies.join(', ')
                        : 'None recorded'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[var(--text-secondary)]">
                      Current medications
                    </p>
                    <p className="mt-1">
                      {history.medications?.length
                        ? history.medications.join(', ')
                        : 'None recorded'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[var(--text-secondary)]">
                      Previous diagnoses
                    </p>
                    <p className="mt-1">
                      {history.previous_diagnoses?.length
                        ? history.previous_diagnoses.join(', ')
                        : history.conditions?.slice(0, 5).join(', ') ||
                          'None recorded'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[var(--text-secondary)]">
                      Medical history
                    </p>
                    <p className="mt-1 leading-relaxed text-[var(--text-secondary)]">
                      {history.latest_summary || '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[var(--text-secondary)]">
                      Recent reports
                    </p>
                    <ul className="mt-2 space-y-1">
                      {(history.reports || []).slice(0, 5).map((r) => (
                        <li key={String(r.id)} className="text-[var(--text-primary)]">
                          {String(r.file_name || 'Report')}
                        </li>
                      ))}
                      {!history.reports?.length ? (
                        <li className="text-[var(--text-secondary)]">No prior reports</li>
                      ) : null}
                    </ul>
                  </div>
                </div>
              )}
            </Card>

            {/* Patient timeline */}
            <Card>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                Patient timeline
              </h2>
              {!timelineItems.length ? (
                <p className="mt-3 text-sm text-[var(--text-secondary)]">
                  Timeline updates as intake progresses.
                </p>
              ) : (
                <ol className="mt-5 space-y-0">
                  {timelineItems.map((item, idx) => (
                    <li key={`${item.title}-${idx}`} className="relative flex gap-3 pb-5 last:pb-0">
                      {idx < timelineItems.length - 1 ? (
                        <span className="absolute left-[7px] top-4 h-[calc(100%-8px)] w-px bg-[var(--border-color)]" />
                      ) : null}
                      <span className="relative z-10 mt-1 h-3.5 w-3.5 shrink-0 rounded-full bg-primary-600" />
                      <div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">
                          {item.title}
                        </p>
                        <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                          {item.when} · {item.status}
                        </p>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </Card>
          </div>
        </div>

        {/* Developer Mode — technical only */}
        <Card className="border-dashed">
          <button
            type="button"
            onClick={() => setDevOpen((v) => !v)}
            className="flex w-full items-center justify-between text-left"
          >
            <div>
              <p className="text-sm font-semibold text-[var(--text-primary)]">
                Developer Mode
              </p>
              <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                OCR logs, graph JSON, validation, and builder details. Hidden from clinical use.
              </p>
            </div>
            <span className="text-xs text-primary-600">
              {devOpen ? 'Collapse' : 'Expand'}
            </span>
          </button>
          {devOpen ? (
            <div className="mt-5 space-y-4 border-t border-[var(--border-color)] pt-5 text-xs">
              <div className="grid gap-2 sm:grid-cols-2">
                <p>
                  <span className="text-[var(--text-secondary)]">Provider: </span>
                  {ocrResult?.ocr_provider ||
                    ocrMutation.data?.ocr_provider ||
                    ocrResult?.provider ||
                    '—'}
                </p>
                <p>
                  <span className="text-[var(--text-secondary)]">
                    Extraction method:{' '}
                  </span>
                  {methodLabel(processingMethod)}
                </p>
                <p>
                  <span className="text-[var(--text-secondary)]">Library used: </span>
                  {ocrResult?.library_used ||
                    ocrMutation.data?.library_used ||
                    '—'}
                </p>
                <p>
                  <span className="text-[var(--text-secondary)]">Fallback used: </span>
                  {String(
                    ocrResult?.fallback_used ??
                      ocrMutation.data?.fallback_used ??
                      '—',
                  )}
                </p>
                <p>
                  <span className="text-[var(--text-secondary)]">
                    Confidence:{' '}
                  </span>
                  {ocrResult?.confidence != null
                    ? `${(Number(ocrResult.confidence) * 100).toFixed(1)}%`
                    : '—'}
                </p>
                <p>
                  <span className="text-[var(--text-secondary)]">
                    Processing time:{' '}
                  </span>
                  {ocrResult?.processing_time_ms != null
                    ? `${ocrResult.processing_time_ms} ms`
                    : '—'}
                </p>
                <p>
                  <span className="text-[var(--text-secondary)]">Chars / words: </span>
                  {ocrResult?.character_count ?? '—'} /{' '}
                  {ocrResult?.word_count ?? '—'}
                </p>
                <p>
                  <span className="text-[var(--text-secondary)]">Error: </span>
                  {ocrResult?.error_message || selectedJob?.error_message || '—'}
                </p>
              </div>
              <div>
                <p className="mb-1 font-medium">OCR / processing logs</p>
                <pre className="max-h-40 overflow-auto rounded-xl bg-black/5 p-3 dark:bg-white/5">
                  {JSON.stringify(
                    ocrResult?.processing_logs ||
                      ocrResult?.provenance_json?.logs ||
                      [],
                    null,
                    2,
                  )}
                </pre>
              </div>
              <div>
                <p className="mb-1 font-medium">Exceptions / warnings</p>
                <pre className="max-h-32 overflow-auto rounded-xl bg-black/5 p-3 dark:bg-white/5">
                  {JSON.stringify(
                    {
                      error_message:
                        ocrResult?.error_message || selectedJob?.error_message,
                      warnings: ocrWarnings,
                      kg_warnings: kgMutation.data?.warnings || [],
                    },
                    null,
                    2,
                  )}
                </pre>
              </div>
              <div>
                <p className="mb-1 font-medium">Raw Graph JSON</p>
                <pre className="max-h-48 overflow-auto rounded-xl bg-black/5 p-3 dark:bg-white/5">
                  {JSON.stringify(
                    {
                      nodes: kgNodes,
                      relationships: kgRels,
                      statistics: kgStats,
                      patient_summary: kgPatientSummary,
                      graph_version:
                        kgResult?.graph_version || kgMutation.data?.graph_version,
                    },
                    null,
                    2,
                  )}
                </pre>
              </div>
              <div>
                <p className="mb-1 font-medium">Node JSON</p>
                <pre className="max-h-40 overflow-auto rounded-xl bg-black/5 p-3 dark:bg-white/5">
                  {JSON.stringify(kgNodes, null, 2)}
                </pre>
              </div>
              <div>
                <p className="mb-1 font-medium">Relationship JSON</p>
                <pre className="max-h-40 overflow-auto rounded-xl bg-black/5 p-3 dark:bg-white/5">
                  {JSON.stringify(kgRels, null, 2)}
                </pre>
              </div>
              <div>
                <p className="mb-1 font-medium">Builder Logs</p>
                <pre className="max-h-40 overflow-auto rounded-xl bg-black/5 p-3 dark:bg-white/5">
                  {JSON.stringify(
                    kgResult?.builder_logs_json || [],
                    null,
                    2,
                  )}
                </pre>
              </div>
              <div>
                <p className="mb-1 font-medium">Graph Validation</p>
                <pre className="max-h-40 overflow-auto rounded-xl bg-black/5 p-3 dark:bg-white/5">
                  {JSON.stringify(
                    kgResult?.validation_json || {},
                    null,
                    2,
                  )}
                </pre>
              </div>
            </div>
          ) : null}
        </Card>

        {/* Full medical report modal */}
        {fullReportOpen ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="max-h-[85vh] w-full max-w-2xl overflow-auto rounded-2xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-6 shadow-xl">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-semibold text-[var(--text-primary)]">
                    Medical report
                  </h3>
                  <p className="mt-1 text-sm text-[var(--text-secondary)]">
                    {selectedJob?.document_name || 'Document'} ·{' '}
                    {docTypeLabel(
                      ocrResult?.document_type,
                      selectedJob?.document_type,
                    )}{' '}
                    · {methodLabel(processingMethod)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setFullReportOpen(false)}
                  className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-sm"
                >
                  Close
                </button>
              </div>
              <div className="mt-6 rounded-xl border border-[var(--border-color)] bg-white p-6 shadow-sm dark:bg-black/20">
                <p className="whitespace-pre-wrap font-serif text-[15px] leading-7 text-[var(--text-primary)]">
                  {reportText ||
                    'No readable text was extracted from this document.'}
                </p>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </ErrorBoundary>
  );
}
