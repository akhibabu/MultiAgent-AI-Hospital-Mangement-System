import { useState } from 'react';
import { Link } from 'react-router-dom';
import Badge, { type BadgeTone } from '@/components/common/Badge';
import Card from '@/components/common/Card';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import Loading from '@/components/ui/Loading';
import { usePatients } from '@/hooks/usePatients';
import {
  useResourceAllocationResult,
  useStartResourceAllocation,
} from '@/hooks/useResourceAllocation';
import { getApiErrorMessage } from '@/services/apiClient';
import type { ResourceAllocationResult, ResourceAllocationStartResult } from '@/types/resourceAllocation';

const STAGES = [
  'Requirement Detection',
  'Availability Assessment',
  'Priority-Based Allocation',
  'Bed / ICU Allocation',
  'Staff / Theatre / Equipment',
  'Conflict Detection',
];

function tone(level?: string | null): BadgeTone {
  if (!level) return 'gray';
  if (level === 'Critical' || level === 'High' || level === 'Unavailable') return 'red';
  if (level === 'Urgent' || level === 'Moderate' || level === 'Partially Allocated') return 'amber';
  if (level === 'Semi-Urgent') return 'blue';
  return 'green';
}

function buildView(live?: ResourceAllocationStartResult, saved?: ResourceAllocationResult) {
  return live
    ? {
        summary: live.summary,
        priorityLevel: live.priority_level,
        priorityScore: live.priority_score,
        requirements: live.requirements,
        allocations: live.allocations,
        conflicts: live.conflicts,
        score: live.allocation_score,
        sourceAvailability: live.source_availability,
        warnings: live.warnings,
        planningOnly: live.planning_only,
      }
    : {
        summary: saved?.summary || '',
        priorityLevel: saved?.priority_level || 'Routine',
        priorityScore: Number(saved?.priority_score || 0),
        requirements: saved?.requirements_json || [],
        allocations: saved?.allocations_json || [],
        conflicts: saved?.conflicts_json || [],
        score: Number(saved?.allocation_score || 0),
        sourceAvailability: saved?.source_availability_json || {},
        warnings: saved?.warnings_json || [],
        planningOnly: saved?.planning_only ?? true,
      };
}

export default function ResourceAllocationAgentPage() {
  const [patientId, setPatientId] = useState('');
  const patients = usePatients({ page: 1, page_size: 100, sort_by: 'created_at', sort_order: 'desc' });
  const saved = useResourceAllocationResult(patientId || undefined);
  const run = useStartResourceAllocation();
  const data = buildView(run.data, saved.data);
  const hasResult = Boolean(run.data || saved.data);

  async function runAgent() {
    if (!patientId) return;
    await run.mutateAsync({ patient_id: patientId });
  }

  return (
    <ErrorBoundary title="Resource Allocation Agent error">
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary-600">
                AI Center · Hospital Operations
              </p>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[var(--text-primary)]">
                Resource Allocation Agent
              </h1>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[var(--text-secondary)]">
                Resource needs are derived from the latest Scheduling and Emergency
                outputs. The patient does not choose beds, theatres, staff, or equipment.
              </p>
            </div>
            <Link
              to="/ai"
              className="rounded-xl border border-[var(--border-color)] px-3 py-2 text-sm text-[var(--text-secondary)]"
            >
              Back to AI Center
            </Link>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Status</p>
              <p className="mt-1 text-sm font-semibold">{run.isPending ? 'Running' : hasResult ? 'Completed' : 'Not started'}</p>
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Priority</p>
              {hasResult ? (
                <Badge tone={tone(data.priorityLevel)}>{data.priorityLevel} · {data.priorityScore}/100</Badge>
              ) : <p className="mt-1 text-sm font-semibold">—</p>}
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Allocation score</p>
              <p className="mt-1 text-sm font-semibold">{hasResult ? data.score + '/100' : '—'}</p>
            </Card>
            <Card>
              <p className="text-xs text-[var(--text-secondary)]">Mode</p>
              <p className="mt-1 text-sm font-semibold">Planning only</p>
            </Card>
          </div>
        </header>

        <Card>
          <div className="flex flex-wrap items-end gap-3">
            <label className="min-w-[280px] flex-1 text-sm">
              <span className="mb-1.5 block text-[var(--text-secondary)]">Patient</span>
              {patients.isLoading ? (
                <Loading message="Loading patients…" />
              ) : (
                <select
                  value={patientId}
                  onChange={(event) => setPatientId(event.target.value)}
                  className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5"
                >
                  <option value="">Select a patient…</option>
                  {(patients.data?.items ?? []).map((patient) => (
                    <option key={patient.id} value={patient.id}>
                      {patient.first_name} {patient.last_name}
                      {patient.patient_number ? ' (' + patient.patient_number + ')' : ''}
                    </option>
                  ))}
                </select>
              )}
            </label>
            <button
              type="button"
              disabled={!patientId || run.isPending}
              onClick={runAgent}
              className="rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {run.isPending ? 'Running Resource Allocation…' : 'Run Resource Allocation Agent'}
            </button>
          </div>
          <p className="mt-3 text-xs text-[var(--text-secondary)]">
            Clinical and operational inputs are collected automatically from prior agents and current hospital inventory.
          </p>
          {run.isError ? (
            <p className="mt-3 text-sm text-red-600">{getApiErrorMessage(run.error, 'Resource Allocation Agent failed')}</p>
          ) : null}
        </Card>

        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          <Card>
            <h2 className="text-sm font-semibold">Workflow</h2>
            <ol className="mt-5 space-y-3">
              {STAGES.map((stage, index) => (
                <li key={stage} className="flex gap-3">
                  <span className={hasResult
                    ? 'flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-[10px] font-bold text-white'
                    : 'flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[var(--border-color)] text-[10px] text-[var(--text-secondary)]'}
                  >
                    {hasResult ? '✓' : index + 1}
                  </span>
                  <span className="text-sm">{stage}</span>
                </li>
              ))}
            </ol>
          </Card>

          <div className="space-y-6">
            {!patientId ? (
              <Card>
                <p className="text-sm text-[var(--text-secondary)]">
                  Select a patient. The agent will automatically consume the latest Scheduling and Emergency context.
                </p>
              </Card>
            ) : null}

            {hasResult ? (
              <>
                <Card>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="text-sm font-semibold">Cross-Agent Inputs</h2>
                      <p className="mt-1 text-xs text-[var(--text-secondary)]">
                        Read-only operational inputs from upstream agents.
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(data.sourceAvailability).map(([source, available]) => (
                        <span key={source} className="rounded-md border border-[var(--border-color)] px-2 py-1 text-[10px] uppercase tracking-wider">
                          {source}: {available ? 'ready' : 'missing'}
                        </span>
                      ))}
                    </div>
                  </div>
                  <p className="mt-4 text-sm leading-relaxed">{data.summary}</p>
                  <p className="mt-3 rounded-lg border border-amber-500/30 px-3 py-2 text-xs text-[var(--text-secondary)]">
                    Planning-only result: the agent does not decrement, reserve, or mutate hospital inventory.
                  </p>
                </Card>

                <Card>
                  <h2 className="text-sm font-semibold">Allocation Plan</h2>
                  <div className="mt-4 overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead className="border-b border-[var(--border-color)] text-left text-xs uppercase text-[var(--text-secondary)]">
                        <tr>
                          <th className="px-3 py-2">Requirement</th>
                          <th className="px-3 py-2">Required</th>
                          <th className="px-3 py-2">Available</th>
                          <th className="px-3 py-2">Allocated</th>
                          <th className="px-3 py-2">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.allocations.map((item) => (
                          <tr key={item.requirement + '-' + (item.resource_type || 'staff')} className="border-b border-[var(--border-color)] last:border-0">
                            <td className="px-3 py-3">
                              <p className="font-medium">{item.requirement}</p>
                              <p className="text-xs text-[var(--text-secondary)]">{item.rationale}</p>
                              {item.matched_resources.length ? (
                                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                                  Matches: {item.matched_resources.map((r) => r.resource_name).join(', ')}
                                </p>
                              ) : null}
                            </td>
                            <td className="px-3 py-3">{item.required_quantity}</td>
                            <td className="px-3 py-3">{item.available_quantity}</td>
                            <td className="px-3 py-3">{item.allocated_quantity}</td>
                            <td className="px-3 py-3"><Badge tone={tone(item.status)}>{item.status}</Badge></td>
                          </tr>
                        ))}
                        {!data.allocations.length ? (
                          <tr><td colSpan={5} className="px-3 py-6 text-center text-sm text-[var(--text-secondary)]">No resource requirements were derived.</td></tr>
                        ) : null}
                      </tbody>
                    </table>
                  </div>
                </Card>

                <div className="grid gap-6 lg:grid-cols-2">
                  <Card>
                    <h2 className="text-sm font-semibold">Conflicts</h2>
                    <div className="mt-3 space-y-2">
                      {data.conflicts.map((conflict) => (
                        <div key={conflict.code + '-' + (conflict.requirement || '')} className="rounded-lg border border-[var(--border-color)] p-3">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-medium">{conflict.message}</p>
                            <Badge tone={tone(conflict.severity)}>{conflict.severity}</Badge>
                          </div>
                          <p className="mt-2 text-xs text-[var(--text-secondary)]">{conflict.recommended_action}</p>
                        </div>
                      ))}
                      {!data.conflicts.length ? <p className="text-sm text-[var(--text-secondary)]">No allocation conflicts detected.</p> : null}
                    </div>
                  </Card>

                  <Card>
                    <h2 className="text-sm font-semibold">Warnings</h2>
                    <div className="mt-3 space-y-2 text-sm text-[var(--text-secondary)]">
                      {data.warnings.map((warning) => <p key={warning}>• {warning}</p>)}
                      {!data.warnings.length ? <p>No warnings.</p> : null}
                    </div>
                  </Card>
                </div>
              </>
            ) : null}
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}
