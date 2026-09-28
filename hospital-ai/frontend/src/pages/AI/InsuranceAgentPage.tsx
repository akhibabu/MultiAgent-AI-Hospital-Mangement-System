import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Card from '@/components/common/Card';
import Badge from '@/components/common/Badge';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import { usePatients } from '@/hooks/usePatients';
import { useInsuranceResult, useStartInsurance } from '@/hooks/useInsurance';
import type {
  InsurancePolicy,
  InsuranceStartResponse,
  InsuranceResult,
} from '@/types/insurance';

const today = new Date().toISOString().slice(0, 10);

const WORKFLOW = [
  ['1. Policy Verification', 'Checks policy identity, status, dates, and exclusions using only the supplied policy terms.'],
  ['2. Coverage Estimation', 'Calculates an auditable estimate from coverage, deductible, and copay values.'],
  ['3. Claim Generation', 'Builds a conservative draft claim using available clinical context.'],
  ['4. Fraud Detection', 'Screens for possible anomalies. A flag is not a fraud determination.'],
  ['5. Preauthorization', 'Checks whether the supplied policy lists authorization requirements and prepares a review draft.'],
] as const;

function fieldClass() {
  return 'w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5 text-sm';
}

function normalizeResult(
  output: InsuranceStartResponse | undefined,
  persisted: InsuranceResult | undefined,
): InsuranceStartResponse | null {
  if (output) return output;
  if (!persisted) return null;
  return {
    patient_id: persisted.patient_id,
    service_name: persisted.service_name,
    service_date: persisted.service_date,
    billed_amount: persisted.billed_amount,
    status: persisted.status,
    processing_time_ms: persisted.processing_time_ms ?? 0,
    summary: persisted.summary,
    policy: persisted.policy_json,
    policy_verification: persisted.policy_verification_json,
    coverage_estimate: persisted.coverage_estimate_json,
    claim_draft: persisted.claim_draft_json,
    fraud_screening: persisted.fraud_screening_json,
    preauthorization: persisted.preauthorization_json,
    warnings: persisted.warnings_json,
    insurance_result: persisted,
    ai_debug: [],
  };
}

function toneForStatus(value: string): 'green' | 'blue' | 'amber' | 'red' | 'gray' {
  const v = value.toLowerCase();
  if (v.includes('verified') || v.includes('active') || v.includes('ready') || v === 'low' || v === 'not_required') return 'green';
  if (v.includes('review') || v.includes('incomplete') || v.includes('unknown') || v === 'medium') return 'amber';
  if (v.includes('expired') || v.includes('inactive') || v === 'high') return 'red';
  return 'blue';
}

function money(value: number) {
  return `₹${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
}

export default function InsuranceAgentPage() {
  const [patientId, setPatientId] = useState('');
  const [serviceName, setServiceName] = useState('');
  const [serviceDate, setServiceDate] = useState(today);
  const [billedAmount, setBilledAmount] = useState('0');
  const [documents, setDocuments] = useState('');
  const [providerName, setProviderName] = useState('');
  const [policyNumber, setPolicyNumber] = useState('');
  const [memberId, setMemberId] = useState('');
  const [planName, setPlanName] = useState('');
  const [policyStatus, setPolicyStatus] = useState<InsurancePolicy['status']>('active');
  const [effectiveFrom, setEffectiveFrom] = useState('');
  const [effectiveTo, setEffectiveTo] = useState('');
  const [coveragePercent, setCoveragePercent] = useState('80');
  const [deductible, setDeductible] = useState('0');
  const [copay, setCopay] = useState('0');
  const [coveredServices, setCoveredServices] = useState('');
  const [excludedServices, setExcludedServices] = useState('');
  const [preauthServices, setPreauthServices] = useState('');

  const patientsQuery = usePatients({
    page: 1,
    page_size: 100,
    sort_by: 'created_at',
    sort_order: 'desc',
  });
  const resultQuery = useInsuranceResult(patientId || undefined);
  const startMutation = useStartInsurance();
  const output = startMutation.data;
  const active = useMemo(
    () => normalizeResult(output, resultQuery.data),
    [output, resultQuery.data],
  );

  const selectedPatient = useMemo(
    () => (patientsQuery.data?.items ?? []).find((p) => p.id === patientId),
    [patientsQuery.data?.items, patientId],
  );

  function selectPatient(id: string) {
    setPatientId(id);
    const patient = (patientsQuery.data?.items ?? []).find((p) => p.id === id);
    setProviderName(patient?.insurance_provider ?? '');
    setPolicyNumber(patient?.insurance_number ?? '');
  }

  function csv(value: string) {
    return value.split(',').map((v) => v.trim()).filter(Boolean);
  }

  async function handleRun() {
    if (!patientId || !serviceName.trim()) return;

    const policy: InsurancePolicy = {
      provider_name: providerName.trim(),
      policy_number: policyNumber.trim(),
      member_id: memberId.trim() || null,
      plan_name: planName.trim(),
      status: policyStatus,
      effective_from: effectiveFrom || null,
      effective_to: effectiveTo || null,
      coverage_percent: Number(coveragePercent) || 0,
      deductible_remaining: Number(deductible) || 0,
      out_of_pocket_remaining: null,
      annual_limit_remaining: null,
      copay: Number(copay) || 0,
      covered_services: csv(coveredServices),
      excluded_services: csv(excludedServices),
      preauthorization_services: csv(preauthServices),
    };

    await startMutation.mutateAsync({
      patient_id: patientId,
      service_name: serviceName.trim(),
      service_date: serviceDate,
      billed_amount: Number(billedAmount) || 0,
      supporting_documents: csv(documents),
      policy,
    });
  }

  return (
    <ErrorBoundary title="Insurance Agent error">
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary-600">AI Center</p>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight">Insurance Agent</h1>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[var(--text-secondary)]">
                Policy verification, coverage estimation, claim drafting, anomaly screening,
                and preauthorization preparation. Human review remains mandatory.
              </p>
            </div>
            <Link to="/ai" className="rounded-xl border border-[var(--border-color)] px-3 py-2 text-sm text-[var(--text-secondary)]">
              Back to AI Center
            </Link>
          </div>
        </header>

        <Card>
          <div className="grid gap-4 md:grid-cols-3">
            <label className="text-sm md:col-span-2">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Patient</span>
              <select className={fieldClass()} value={patientId} onChange={(e) => selectPatient(e.target.value)}>
                <option value="">Select a patient…</option>
                {(patientsQuery.data?.items ?? []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.first_name} {p.last_name}{p.patient_number ? ` (${p.patient_number})` : ''}
                  </option>
                ))}
              </select>
              {selectedPatient ? (
                <span className="mt-1 block text-xs text-[var(--text-secondary)]">
                  Existing insurance: {selectedPatient.insurance_provider || '—'} / {selectedPatient.insurance_number || '—'}
                </span>
              ) : null}
            </label>
            <label className="text-sm">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Service date</span>
              <input className={fieldClass()} type="date" value={serviceDate} onChange={(e) => setServiceDate(e.target.value)} />
            </label>
            <label className="text-sm md:col-span-2">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Service / Procedure</span>
              <input className={fieldClass()} placeholder="e.g. MRI Brain" value={serviceName} onChange={(e) => setServiceName(e.target.value)} />
            </label>
            <label className="text-sm">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Billed amount (₹)</span>
              <input className={fieldClass()} type="number" min="0" value={billedAmount} onChange={(e) => setBilledAmount(e.target.value)} />
            </label>
            <label className="text-sm md:col-span-3">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Supporting documents</span>
              <input className={fieldClass()} placeholder="Clinical Summary, Discharge Summary, Authorization Letter" value={documents} onChange={(e) => setDocuments(e.target.value)} />
            </label>
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold">Policy Terms</h2>
            <Badge tone="gray">Supplied evidence</Badge>
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <label className="text-sm"><span className="mb-1.5 block text-[var(--text-secondary)]">Provider</span><input className={fieldClass()} value={providerName} onChange={(e) => setProviderName(e.target.value)} /></label>
            <label className="text-sm"><span className="mb-1.5 block text-[var(--text-secondary)]">Policy number</span><input className={fieldClass()} value={policyNumber} onChange={(e) => setPolicyNumber(e.target.value)} /></label>
            <label className="text-sm"><span className="mb-1.5 block text-[var(--text-secondary)]">Member ID</span><input className={fieldClass()} value={memberId} onChange={(e) => setMemberId(e.target.value)} /></label>
            <label className="text-sm"><span className="mb-1.5 block text-[var(--text-secondary)]">Plan name</span><input className={fieldClass()} value={planName} onChange={(e) => setPlanName(e.target.value)} /></label>
            <label className="text-sm"><span className="mb-1.5 block text-[var(--text-secondary)]">Effective from</span><input className={fieldClass()} type="date" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} /></label>
            <label className="text-sm"><span className="mb-1.5 block text-[var(--text-secondary)]">Effective to</span><input className={fieldClass()} type="date" value={effectiveTo} onChange={(e) => setEffectiveTo(e.target.value)} /></label>
            <label className="text-sm"><span className="mb-1.5 block text-[var(--text-secondary)]">Coverage %</span><input className={fieldClass()} type="number" min="0" max="100" value={coveragePercent} onChange={(e) => setCoveragePercent(e.target.value)} /></label>
            <label className="text-sm"><span className="mb-1.5 block text-[var(--text-secondary)]">Deductible remaining</span><input className={fieldClass()} type="number" min="0" value={deductible} onChange={(e) => setDeductible(e.target.value)} /></label>
            <label className="text-sm"><span className="mb-1.5 block text-[var(--text-secondary)]">Copay</span><input className={fieldClass()} type="number" min="0" value={copay} onChange={(e) => setCopay(e.target.value)} /></label>
            <label className="text-sm"><span className="mb-1.5 block text-[var(--text-secondary)]">Policy status</span><select className={fieldClass()} value={policyStatus} onChange={(e) => setPolicyStatus(e.target.value as InsurancePolicy['status'])}><option value="active">Active</option><option value="inactive">Inactive</option><option value="expired">Expired</option><option value="unknown">Unknown</option></select></label>
            <label className="text-sm md:col-span-3"><span className="mb-1.5 block text-[var(--text-secondary)]">Covered services <span className="text-xs">(comma separated)</span></span><input className={fieldClass()} placeholder="MRI, Surgery, Consultation" value={coveredServices} onChange={(e) => setCoveredServices(e.target.value)} /></label>
            <label className="text-sm md:col-span-3"><span className="mb-1.5 block text-[var(--text-secondary)]">Excluded services <span className="text-xs">(comma separated)</span></span><input className={fieldClass()} placeholder="Cosmetic Surgery" value={excludedServices} onChange={(e) => setExcludedServices(e.target.value)} /></label>
            <label className="text-sm md:col-span-3"><span className="mb-1.5 block text-[var(--text-secondary)]">Preauthorization services <span className="text-xs">(comma separated)</span></span><input className={fieldClass()} placeholder="MRI, ICU Admission, Surgery" value={preauthServices} onChange={(e) => setPreauthServices(e.target.value)} /></label>
          </div>
          <button type="button" className="mt-5 rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50" disabled={!patientId || !serviceName.trim() || startMutation.isPending} onClick={handleRun}>
            {startMutation.isPending ? 'Running Insurance Agent…' : 'Run Insurance Agent'}
          </button>
          <p className="mt-2 text-xs text-[var(--text-secondary)]">
            The policy snapshot is stored with the run for auditability. No live carrier system is queried.
          </p>
        </Card>

        {active ? (
          <>
            <Card>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-sm font-semibold">Run Summary</h2>
                  <p className="mt-2 text-sm leading-relaxed">{active.summary}</p>
                </div>
                <Badge tone="amber">Human review required</Badge>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                {WORKFLOW.map(([label]) => {
                  let value = 'Ready';
                  if (label.startsWith('1.')) value = active.policy_verification.verified ? 'Verified' : 'Issues found';
                  if (label.startsWith('2.')) value = money(active.coverage_estimate.insurer_estimate);
                  if (label.startsWith('4.')) value = active.fraud_screening.risk_level;
                  if (label.startsWith('5.')) value = active.preauthorization.status.replace(/_/g, ' ');
                  return <div key={label} className="rounded-xl border border-[var(--border-color)] p-3"><p className="text-xs text-[var(--text-secondary)]">{label}</p><p className="mt-1 text-sm font-semibold">{value}</p></div>;
                })}
              </div>
            </Card>

            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <h2 className="text-sm font-semibold">1. Policy Verification</h2>
                <div className="mt-3"><Badge tone={toneForStatus(active.policy_verification.verified ? 'verified' : 'incomplete')}>{active.policy_verification.verified ? 'VERIFIED FROM SUPPLIED TERMS' : 'VERIFICATION INCOMPLETE'}</Badge></div>
                {active.policy_verification.issues.length ? <ul className="mt-3 space-y-1 text-sm text-red-700 dark:text-red-300">{active.policy_verification.issues.map((x) => <li key={x}>{x}</li>)}</ul> : <p className="mt-3 text-sm text-[var(--text-secondary)]">No policy consistency issues found in the supplied snapshot.</p>}
                {active.policy_verification.notes.length ? <p className="mt-3 text-xs text-[var(--text-secondary)]">{active.policy_verification.notes.join(' ')}</p> : null}
              </Card>

              <Card>
                <h2 className="text-sm font-semibold">2. Coverage Estimation</h2>
                <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                  <div><span className="text-[var(--text-secondary)]">Billed</span><p className="font-semibold">{money(active.coverage_estimate.billed_amount)}</p></div>
                  <div><span className="text-[var(--text-secondary)]">Eligible</span><p className="font-semibold">{money(active.coverage_estimate.eligible_amount)}</p></div>
                  <div><span className="text-[var(--text-secondary)]">Insurer estimate</span><p className="font-semibold">{money(active.coverage_estimate.insurer_estimate)}</p></div>
                  <div><span className="text-[var(--text-secondary)]">Patient estimate</span><p className="font-semibold">{money(active.coverage_estimate.patient_estimate)}</p></div>
                </div>
                <ul className="mt-3 space-y-1 text-xs text-[var(--text-secondary)]">{active.coverage_estimate.assumptions.map((x) => <li key={x}>• {x}</li>)}</ul>
              </Card>

              <Card>
                <h2 className="text-sm font-semibold">3. Claim Generation</h2>
                <Badge tone="amber">{active.claim_draft.claim_status}</Badge>
                <p className="mt-3 text-sm leading-relaxed">{active.claim_draft.claim_narrative || 'No narrative returned.'}</p>
                <p className="mt-3 text-xs text-[var(--text-secondary)]">Diagnosis codes: {active.claim_draft.diagnosis_codes.join(', ') || 'Coder verification required'}</p>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">Procedure codes: {active.claim_draft.procedure_codes.join(', ') || 'Coder verification required'}</p>
                {active.claim_draft.missing_documents.length ? <p className="mt-3 text-xs text-amber-800 dark:text-amber-200">Missing: {active.claim_draft.missing_documents.join(', ')}</p> : null}
              </Card>

              <Card>
                <h2 className="text-sm font-semibold">4. Fraud / Anomaly Screening</h2>
                <div className="mt-3 flex items-center gap-2"><Badge tone={toneForStatus(active.fraud_screening.risk_level)}>{active.fraud_screening.risk_level.toUpperCase()}</Badge><span className="text-xs text-[var(--text-secondary)]">Risk score {active.fraud_screening.risk_score.toFixed(0)}/100</span></div>
                <p className="mt-3 text-sm">{active.fraud_screening.rationale}</p>
                {active.fraud_screening.flags.length ? <ul className="mt-3 space-y-1 text-sm">{active.fraud_screening.flags.map((x) => <li key={x}>{x}</li>)}</ul> : <p className="mt-3 text-sm text-[var(--text-secondary)]">No anomaly flags returned.</p>}
                {active.fraud_screening.rule_findings.length ? <p className="mt-3 text-xs text-[var(--text-secondary)]">Rules: {active.fraud_screening.rule_findings.join(' · ')}</p> : null}
                <p className="mt-3 text-xs font-medium">{active.fraud_screening.recommendation}</p>
              </Card>

              <Card className="lg:col-span-2">
                <h2 className="text-sm font-semibold">5. Preauthorization</h2>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Badge tone={toneForStatus(active.preauthorization.status)}>{active.preauthorization.status.replace(/_/g, ' ')}</Badge>
                  <Badge tone={active.preauthorization.authorization_required ? 'amber' : 'green'}>{active.preauthorization.authorization_required ? 'Authorization listed as required' : 'No authorization requirement listed'}</Badge>
                </div>
                <p className="mt-3 text-sm">{active.preauthorization.clinical_necessity_summary}</p>
                {active.preauthorization.required_documents.length ? <p className="mt-3 text-sm">Required documents: {active.preauthorization.required_documents.join(', ')}</p> : null}
                <p className="mt-3 text-sm font-medium">{active.preauthorization.recommendation}</p>
              </Card>
            </div>

            <Card>
              <h2 className="text-sm font-semibold">Safety Notes</h2>
              <ul className="mt-3 space-y-1 text-sm text-amber-900 dark:text-amber-100">{active.warnings.map((x) => <li key={x}>• {x}</li>)}</ul>
            </Card>
          </>
        ) : (
          <Card>
            <p className="text-sm text-[var(--text-secondary)]">Select a patient, enter policy terms and a service, then run the Insurance Agent.</p>
          </Card>
        )}
      </div>
    </ErrorBoundary>
  );
}
