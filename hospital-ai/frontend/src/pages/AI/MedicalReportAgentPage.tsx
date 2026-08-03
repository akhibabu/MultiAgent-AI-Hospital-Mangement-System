/**
 * Medical Report Agent — professional hospital documentation.
 *
 * Generates Clinical Summary, Doctor Notes, Discharge Summary, Referral
 * Letter, Insurance Documentation, and a plain-language Patient Report from
 * every previous AI Agent's output. Assists — never replaces — clinician
 * review and sign-off.
 */
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import Badge from '@/components/common/Badge';
import Card from '@/components/common/Card';
import { usePatients } from '@/hooks/usePatients';
import {
  useMedicalReportHistory,
  useMedicalReportResult,
  useStartMedicalReport,
} from '@/hooks/useMedicalReport';
import type {
  ClinicalSummary,
  DischargeSummary,
  DoctorNotes,
  GeneratedMedicalReport,
  InsuranceDocumentation,
  MedicalReportStartResult,
  PatientReport,
  ReferralLetter,
} from '@/types/medicalReport';

const WORKFLOW_STAGES = [
  { id: 'clinical', label: 'Clinical Summary', description: 'Patient overview, chief complaint, history, and key findings.' },
  { id: 'notes', label: 'Doctor Notes Generation', description: 'Structured SOAP consultation notes with clinical reasoning.' },
  { id: 'discharge', label: 'Discharge Summary', description: 'Admission reason, hospital course, medications, follow-up.' },
  { id: 'referral', label: 'Referral Letter Creation', description: 'Formal referral letter to the recommended specialist.' },
  { id: 'insurance', label: 'Insurance Documentation', description: 'Diagnosis/procedure codes, medical necessity, claim summary.' },
  { id: 'patient', label: 'Patient Report Generation', description: 'Plain-language report for the patient — no medical jargon.' },
] as const;

type ReportTabId = (typeof WORKFLOW_STAGES)[number]['id'];

function formatWhen(iso?: string | null) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return `${d.toLocaleDateString()} · ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  } catch {
    return iso;
  }
}

function buildPrintableHtml(title: string, bodyHtml: string): string {
  return `<!DOCTYPE html><html><head><meta charset="utf-8" /><title>${title}</title>
<style>
  body { font-family: Arial, Helvetica, sans-serif; padding: 32px; color: #111827; line-height: 1.65; max-width: 780px; margin: 0 auto; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  h2 { font-size: 14px; margin: 20px 0 6px; text-transform: uppercase; letter-spacing: 0.04em; color: #374151; }
  p { margin: 4px 0; font-size: 13px; }
  ul { margin: 4px 0 8px 18px; font-size: 13px; }
  .meta { color: #6b7280; font-size: 12px; margin-bottom: 16px; }
  .disclaimer { margin-top: 28px; padding: 12px 14px; border: 1px solid #d97706; background: #fffbeb; font-size: 11px; color: #78350f; border-radius: 8px; }
</style>
</head><body>${bodyHtml}</body></html>`;
}

function openPrintWindow(html: string) {
  const win = window.open('', '_blank', 'noopener,noreferrer');
  if (!win) return;
  win.document.write(html);
  win.document.close();
  win.focus();
  setTimeout(() => win.print(), 300);
}

function downloadDocx(html: string, filename: string) {
  const blob = new Blob(['\ufeff', html], { type: 'application/msword' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

const DISCLAIMER_HTML =
  '<div class="disclaimer">Generated documentation synthesized from AI Agent output. Assists — never replaces — clinician review. Must be verified and signed off by a licensed physician before use in an official record, referral, or claim.</div>';

function clinicalSummaryHtml(patientName: string, s: ClinicalSummary): string {
  return `<h1>Clinical Summary</h1><p class="meta">${patientName}</p>
    <h2>Patient Overview</h2><p>${s.patient_overview}</p>
    <h2>Chief Complaint</h2><p>${s.chief_complaint}</p>
    <h2>History</h2><p>${s.history}</p>
    <h2>Diagnosis Summary</h2><p>${s.diagnosis_summary}</p>
    <h2>Current Status</h2><p>${s.current_status}</p>
    <h2>Key Findings</h2><ul>${s.key_findings.map((k) => `<li>${k}</li>`).join('')}</ul>
    ${DISCLAIMER_HTML}`;
}

function doctorNotesHtml(patientName: string, n: DoctorNotes): string {
  return `<h1>Doctor Notes (SOAP)</h1><p class="meta">${patientName}</p>
    <h2>Subjective</h2><p>${n.subjective}</p>
    <h2>Objective</h2><p>${n.objective}</p>
    <h2>Assessment</h2><p>${n.assessment}</p>
    <h2>Plan</h2><p>${n.plan}</p>
    <h2>Clinical Reasoning</h2><p>${n.clinical_reasoning}</p>
    ${DISCLAIMER_HTML}`;
}

function dischargeSummaryHtml(patientName: string, d: DischargeSummary): string {
  return `<h1>Discharge Summary</h1><p class="meta">${patientName}</p>
    <h2>Admission Reason</h2><p>${d.admission_reason}</p>
    <h2>Hospital Course</h2><p>${d.hospital_course}</p>
    <h2>Procedures</h2><ul>${d.procedures.map((p) => `<li>${p}</li>`).join('')}</ul>
    <h2>Medications</h2><ul>${d.medications.map((m) => `<li>${m}</li>`).join('')}</ul>
    <h2>Condition on Discharge</h2><p>${d.condition_on_discharge}</p>
    <h2>Follow-up</h2><p>${d.follow_up}</p>
    <h2>Emergency Instructions</h2><p>${d.emergency_instructions}</p>
    ${DISCLAIMER_HTML}`;
}

function referralLetterHtml(patientName: string, r: ReferralLetter): string {
  return `<h1>Referral Letter</h1><p class="meta">${patientName} → ${r.receiving_specialist}</p>
    <p style="white-space: pre-wrap;">${r.letter_body}</p>
    ${DISCLAIMER_HTML}`;
}

function insuranceDocumentationHtml(patientName: string, i: InsuranceDocumentation): string {
  return `<h1>Insurance Documentation</h1><p class="meta">${patientName}</p>
    <h2>Diagnosis Codes</h2><ul>${i.diagnosis_codes.map((c) => `<li>${c.condition}: ${c.code}</li>`).join('')}</ul>
    <h2>Procedure Codes</h2><ul>${i.procedure_codes.map((c) => `<li>${c.procedure}: ${c.code}</li>`).join('')}</ul>
    <h2>Supporting Documents</h2><ul>${i.supporting_documents.map((d) => `<li>${d}</li>`).join('')}</ul>
    <h2>Medical Necessity</h2><p>${i.medical_necessity}</p>
    <h2>Claim Summary</h2><p>${i.claim_summary}</p>
    <h2>Supporting Evidence</h2><ul>${i.supporting_evidence.map((e) => `<li>${e}</li>`).join('')}</ul>
    ${DISCLAIMER_HTML}`;
}

function patientReportHtml(patientName: string, p: PatientReport): string {
  return `<h1>Your Health Report</h1><p class="meta">${patientName}</p>
    <h2>Diagnosis Summary</h2><p>${p.diagnosis_summary}</p>
    <h2>Treatment Summary</h2><p>${p.treatment_summary}</p>
    <h2>Current Medicines</h2><ul>${p.current_medicines.map((m) => `<li>${m}</li>`).join('')}</ul>
    <h2>Lifestyle Advice</h2><ul>${p.lifestyle_advice.map((l) => `<li>${l}</li>`).join('')}</ul>
    <h2>Diet</h2><ul>${p.diet.map((d) => `<li>${d}</li>`).join('')}</ul>
    <h2>Exercise</h2><ul>${p.exercise.map((e) => `<li>${e}</li>`).join('')}</ul>
    <h2>Follow-up</h2><p>${p.follow_up}</p>
    <h2>Emergency Contact Instructions</h2><p>${p.emergency_contact_instructions}</p>
    <h2>Frequently Asked Questions</h2>${p.faq.map((f) => `<p><strong>${f.question}</strong><br/>${f.answer}</p>`).join('')}`;
}

export default function MedicalReportAgentPage() {
  const [patientId, setPatientId] = useState('');
  const [receivingSpecialist, setReceivingSpecialist] = useState('');
  const [activeTab, setActiveTab] = useState<ReportTabId>('clinical');
  const [devOpen, setDevOpen] = useState(false);

  const patientsQuery = usePatients({
    page: 1,
    page_size: 100,
    sort_by: 'created_at',
    sort_order: 'desc',
  });

  const resultQuery = useMedicalReportResult(patientId || undefined);
  const historyQuery = useMedicalReportHistory(patientId || undefined);
  const startMutation = useStartMedicalReport(patientId || undefined);

  const liveReport: MedicalReportStartResult | undefined = startMutation.data;
  const persisted: GeneratedMedicalReport | undefined = resultQuery.data;
  const hasResult = Boolean(liveReport || persisted);

  const clinicalSummary: ClinicalSummary | undefined =
    liveReport?.clinical_summary || persisted?.clinical_summary_json;
  const doctorNotes: DoctorNotes | undefined = liveReport?.doctor_notes || persisted?.doctor_notes_json;
  const dischargeSummary: DischargeSummary | undefined =
    liveReport?.discharge_summary || persisted?.discharge_summary_json;
  const referralLetter: ReferralLetter | undefined =
    liveReport?.referral_letter || persisted?.referral_letter_json;
  const insuranceDocumentation: InsuranceDocumentation | undefined =
    liveReport?.insurance_documentation || persisted?.insurance_documentation_json;
  const patientReport: PatientReport | undefined = liveReport?.patient_report || persisted?.patient_report_json;
  const summary = liveReport?.summary || persisted?.summary;
  const version = liveReport?.version ?? persisted?.version;
  const warnings = liveReport?.warnings || [];

  const patientName = useMemo(() => {
    const p = (patientsQuery.data?.items ?? []).find((item) => item.id === patientId);
    return p ? `${p.first_name} ${p.last_name}` : 'Patient';
  }, [patientsQuery.data, patientId]);

  const activeHtml = useMemo(() => {
    if (!hasResult) return '';
    switch (activeTab) {
      case 'clinical':
        return clinicalSummary ? clinicalSummaryHtml(patientName, clinicalSummary) : '';
      case 'notes':
        return doctorNotes ? doctorNotesHtml(patientName, doctorNotes) : '';
      case 'discharge':
        return dischargeSummary ? dischargeSummaryHtml(patientName, dischargeSummary) : '';
      case 'referral':
        return referralLetter ? referralLetterHtml(patientName, referralLetter) : '';
      case 'insurance':
        return insuranceDocumentation ? insuranceDocumentationHtml(patientName, insuranceDocumentation) : '';
      case 'patient':
        return patientReport ? patientReportHtml(patientName, patientReport) : '';
      default:
        return '';
    }
  }, [activeTab, hasResult, patientName, clinicalSummary, doctorNotes, dischargeSummary, referralLetter, insuranceDocumentation, patientReport]);

  const isRunning = startMutation.isPending;
  const isLoadingExisting = resultQuery.isLoading && !hasResult;

  async function handleRun() {
    if (!patientId) return;
    await startMutation.mutateAsync({ receiving_specialist: receivingSpecialist || undefined });
  }

  function handlePrint() {
    if (!activeHtml) return;
    openPrintWindow(buildPrintableHtml('Medical Report', activeHtml));
  }

  function handleDownloadPdf() {
    // Uses the browser print dialog — choose "Save as PDF" as the destination.
    if (!activeHtml) return;
    openPrintWindow(buildPrintableHtml('Medical Report', activeHtml));
  }

  function handleDownloadDocx() {
    if (!activeHtml) return;
    const stage = WORKFLOW_STAGES.find((s) => s.id === activeTab);
    downloadDocx(
      buildPrintableHtml(stage?.label || 'Medical Report', activeHtml),
      `${(stage?.label || 'medical-report').replace(/\s+/g, '_').toLowerCase()}.doc`,
    );
  }

  return (
    <ErrorBoundary title="Medical Report Agent error">
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary-600">AI Center</p>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[var(--text-primary)]">
                Medical Report Agent
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--text-secondary)]">
                Generates professional hospital documentation from every previous AI Agent's output.
                Assists — never replaces — clinician review and sign-off.
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
              <p className="text-xs text-[var(--text-secondary)]">Status</p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                {isRunning ? 'Running' : hasResult ? 'Completed' : 'Not started'}
              </p>
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Version</p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                {version != null ? `v${version}` : '—'}
              </p>
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Processing time</p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                {liveReport?.processing_time_ms != null
                  ? `${liveReport.processing_time_ms} ms`
                  : persisted?.processing_time_ms != null
                    ? `${persisted.processing_time_ms} ms`
                    : '—'}
              </p>
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Generated</p>
              <p className="mt-1 text-sm font-semibold text-[var(--text-primary)]">
                {formatWhen(persisted?.created_at)}
              </p>
            </Card>
          </div>
        </header>

        {/* Patient picker + run controls */}
        <Card>
          <div className="flex flex-wrap items-end gap-3">
            <label className="min-w-[220px] flex-1 text-sm">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Patient</span>
              <select
                className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
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
            <label className="min-w-[220px] flex-1 text-sm">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Receiving specialist (optional)</span>
              <input
                type="text"
                value={receivingSpecialist}
                onChange={(e) => setReceivingSpecialist(e.target.value)}
                placeholder="e.g. Cardiologist"
                className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5"
              />
            </label>
            <button
              type="button"
              disabled={!patientId || isRunning}
              onClick={handleRun}
              className="rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {isRunning ? 'Generating…' : 'Run Medical Report Agent'}
            </button>
          </div>
          {startMutation.isError ? (
            <p className="mt-3 text-sm text-red-600">
              Medical Report Agent failed. Ensure Intake Agent stages are complete for this patient.
            </p>
          ) : null}
        </Card>

        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          {/* Workflow */}
          <Card>
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">Workflow</h2>
            <ol className="mt-5 space-y-0">
              {WORKFLOW_STAGES.map((stage, i) => {
                const status = hasResult ? 'complete' : isRunning ? (i === 0 ? 'active' : 'future') : 'future';
                return (
                  <li key={stage.id} className="relative flex gap-3 pb-5 last:pb-0">
                    {i < WORKFLOW_STAGES.length - 1 ? (
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
                    <button
                      type="button"
                      onClick={() => setActiveTab(stage.id)}
                      className={`text-left ${status === 'future' && !hasResult ? 'opacity-70' : ''}`}
                    >
                      <p
                        className={`text-sm font-medium ${
                          activeTab === stage.id ? 'text-primary-600' : 'text-[var(--text-primary)]'
                        }`}
                      >
                        {stage.label}
                      </p>
                      <p className="mt-0.5 text-xs leading-relaxed text-[var(--text-secondary)]">
                        {stage.description}
                      </p>
                    </button>
                  </li>
                );
              })}
            </ol>
          </Card>

          <div className="space-y-6">
            {isLoadingExisting ? (
              <Card>
                <p className="text-sm text-[var(--text-secondary)]">Loading existing report…</p>
              </Card>
            ) : null}

            {resultQuery.isError && !hasResult && patientId ? (
              <Card>
                <p className="text-sm text-[var(--text-secondary)]">
                  No medical report on record for this patient yet. Run the Medical Report Agent to generate one.
                </p>
              </Card>
            ) : null}

            {!patientId ? (
              <Card>
                <p className="text-sm text-[var(--text-secondary)]">
                  Select a patient to view or generate documentation.
                </p>
              </Card>
            ) : null}

            {hasResult ? (
              <>
                <Card>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="text-sm font-semibold text-[var(--text-primary)]">Report Summary</h2>
                      <p className="mt-2 text-sm leading-relaxed text-[var(--text-primary)]">{summary}</p>
                    </div>
                    {version != null ? <Badge tone="blue">Version {version}</Badge> : null}
                  </div>
                  {warnings.length ? (
                    <ul className="mt-3 space-y-1 text-sm text-amber-800 dark:text-amber-200">
                      {warnings.map((w) => (
                        <li key={w}>{w}</li>
                      ))}
                    </ul>
                  ) : null}
                </Card>

                {/* Generated report preview + actions */}
                <Card>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                      {WORKFLOW_STAGES.find((s) => s.id === activeTab)?.label} — Preview
                    </h2>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={handlePrint}
                        className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)]"
                      >
                        Print
                      </button>
                      <button
                        type="button"
                        onClick={handleDownloadPdf}
                        className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)]"
                      >
                        Download PDF
                      </button>
                      <button
                        type="button"
                        onClick={handleDownloadDocx}
                        className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)]"
                      >
                        Download DOCX
                      </button>
                    </div>
                  </div>
                  <p className="mt-1 text-xs italic text-[var(--text-secondary)]">
                    "Download PDF" opens the browser print dialog — choose "Save as PDF" as the destination.
                  </p>
                  <div
                    className="prose prose-sm mt-4 max-h-[520px] overflow-auto rounded-xl border border-[var(--border-color)] bg-white p-5 text-sm text-black dark:bg-neutral-50"
                    // Preview content is generated locally from structured report data — not user-supplied HTML.
                    dangerouslySetInnerHTML={{ __html: activeHtml || '<p>No content generated yet.</p>' }}
                  />
                </Card>

                {/* Version History */}
                <Card>
                  <h2 className="text-sm font-semibold text-[var(--text-primary)]">Version history</h2>
                  {historyQuery.data?.length ? (
                    <ol className="mt-4 space-y-3">
                      {historyQuery.data.map((h) => (
                        <li
                          key={h.id}
                          className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[var(--border-color)] px-3 py-2 text-sm"
                        >
                          <div>
                            <p className="font-medium text-[var(--text-primary)]">
                              Version {h.version} — {h.summary || 'Generated report'}
                            </p>
                            <p className="text-xs text-[var(--text-secondary)]">{formatWhen(h.created_at)}</p>
                          </div>
                          <Badge tone="gray">{h.status}</Badge>
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="mt-3 text-sm text-[var(--text-secondary)]">No prior versions yet.</p>
                  )}
                </Card>

                {/* Developer Mode */}
                <Card className="border-dashed">
                  <button
                    type="button"
                    onClick={() => setDevOpen((v) => !v)}
                    className="flex w-full items-center justify-between text-left"
                  >
                    <div>
                      <p className="text-sm font-semibold text-[var(--text-primary)]">Developer Mode</p>
                      <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                        Raw report bundle JSON. Hidden from clinical use.
                      </p>
                    </div>
                    <span className="text-xs text-primary-600">{devOpen ? 'Collapse' : 'Expand'}</span>
                  </button>
                  {devOpen ? (
                    <pre className="mt-4 max-h-96 overflow-auto rounded-lg bg-black/5 p-3 text-[11px] leading-relaxed dark:bg-white/5">
                      {JSON.stringify(liveReport || persisted, null, 2)}
                    </pre>
                  ) : null}
                </Card>
              </>
            ) : null}
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}
