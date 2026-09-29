import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Badge, { type BadgeTone } from '@/components/common/Badge';
import Card from '@/components/common/Card';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import Loading from '@/components/ui/Loading';
import {
  useDigitalTwinHistory,
  useDigitalTwinLatest,
  useDigitalTwinState,
  useSimulateDigitalTwin,
} from '@/hooks/useDigitalTwin';
import { getApiErrorMessage } from '@/services/apiClient';
import type { DigitalTwinScenario, HospitalTwinState, DigitalTwinRun } from '@/types/digitalTwin';

const INITIAL_SCENARIO: DigitalTwinScenario = {
  horizon_hours: 24,
  emergency_arrivals: 5,
  planned_admissions: 5,
  expected_discharges: 2,
  icu_admissions: 1,
  icu_discharges: 0,
  ventilator_demand: 1,
  additional_theatre_demand: 1,
  staff_absent: 1,
  additional_appointments: 5,
};

function tone(value: string | number): BadgeTone {
  const text = String(value).toLowerCase();
  if (text.includes('critical') || text.includes('shortage') || (typeof value === 'number' && value >= 90)) return 'red';
  if (text.includes('high') || text.includes('elevated') || (typeof value === 'number' && value >= 75)) return 'amber';
  if (text.includes('moderate')) return 'blue';
  return 'green';
}

function percent(value: number) {
  return Number(value || 0).toFixed(1) + '%';
}

function formatAgent(value: string) {
  return value.replace(/_/g, ' ').replace(/\\b\\w/g, (char) => char.toUpperCase());
}

function StateCards({ state }: { state: HospitalTwinState }) {
  const important = ['Bed', 'ICU Bed', 'Ventilator', 'Operation Theatre'];
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {important.map((kind) => {
        const resource = state.resources.find((item) => item.resource_type === kind);
        return (
          <Card key={kind}>
            <p className="text-xs text-[var(--text-secondary)]">{kind}</p>
            <div className="mt-1 flex items-center justify-between gap-2">
              <p className="text-2xl font-semibold">{resource?.available_quantity ?? 0}</p>
              <Badge tone={tone(resource?.utilization_percent ?? 0)}>
                {percent(resource?.utilization_percent ?? 0)} used
              </Badge>
            </div>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              {resource?.total_quantity ?? 0} total · {resource?.maintenance_quantity ?? 0} maintenance
            </p>
          </Card>
        );
      })}
    </div>
  );
}

export default function DigitalTwinPage() {
  const stateQuery = useDigitalTwinState();
  const latestQuery = useDigitalTwinLatest();
  const historyQuery = useDigitalTwinHistory();
  const simulate = useSimulateDigitalTwin();
  const [scenario, setScenario] = useState<DigitalTwinScenario>(INITIAL_SCENARIO);
  const [localRun, setLocalRun] = useState<DigitalTwinRun | null>(null);
  const run = localRun || latestQuery.data || null;
  const state = stateQuery.data?.state || run?.baseline_state || null;

  const fields = useMemo(() => [
    ['emergency_arrivals', 'Emergency arrivals'],
    ['planned_admissions', 'Planned admissions'],
    ['expected_discharges', 'Expected discharges'],
    ['icu_admissions', 'ICU admissions'],
    ['icu_discharges', 'ICU discharges'],
    ['ventilator_demand', 'Ventilator demand'],
    ['additional_theatre_demand', 'Additional theatre demand'],
    ['staff_absent', 'Staff absent'],
    ['additional_appointments', 'Additional appointments'],
  ] as const, []);

  async function runSimulation() {
    const data = await simulate.mutateAsync(scenario);
    setLocalRun(data);
  }

  return (
    <ErrorBoundary title="Digital Twin error">
      <div className="mx-auto max-w-7xl space-y-8">
        <header className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary-600">
                AI Center · Hospital Operations
              </p>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[var(--text-primary)]">
                Hospital Digital Twin
              </h1>
              <p className="mt-2 max-w-4xl text-sm leading-relaxed text-[var(--text-secondary)]">
                A read-only operational replica of hospital capacity and flow. It consumes live
                Resources plus Emergency, Scheduling, and Resource Allocation outputs, then models
                what-if changes and sends advisory feedback back to those operations agents.
              </p>
            </div>
            <Link to="/ai" className="rounded-xl border border-[var(--border-color)] px-3 py-2 text-sm text-[var(--text-secondary)]">
              Back to AI Center
            </Link>
          </div>
        </header>

        {stateQuery.isLoading && !state ? <Loading message="Building the live hospital twin…" /> : null}
        {stateQuery.isError ? (
          <Card><p className="text-sm text-red-600">{getApiErrorMessage(stateQuery.error, 'Unable to build the live Digital Twin state')}</p></Card>
        ) : null}

        {state ? (
          <>
            <StateCards state={state} />

            <div className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
              <Card>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-semibold">Live Hospital State</h2>
                    <p className="mt-1 text-xs text-[var(--text-secondary)]">
                      Captured {new Date(state.captured_at).toLocaleString()}
                    </p>
                  </div>
                  <Badge tone={tone(state.operational_pressure)}>
                    Operational pressure {state.operational_pressure}/100
                  </Badge>
                </div>
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead className="border-b border-[var(--border-color)] text-left text-xs uppercase text-[var(--text-secondary)]">
                      <tr><th className="px-3 py-2">Resource</th><th className="px-3 py-2">Total</th><th className="px-3 py-2">Available</th><th className="px-3 py-2">In use</th><th className="px-3 py-2">Utilization</th></tr>
                    </thead>
                    <tbody>
                      {state.resources.map((resource) => (
                        <tr key={resource.resource_type} className="border-b border-[var(--border-color)] last:border-0">
                          <td className="px-3 py-3 font-medium">{resource.resource_type}</td>
                          <td className="px-3 py-3">{resource.total_quantity}</td>
                          <td className="px-3 py-3">{resource.available_quantity}</td>
                          <td className="px-3 py-3">{resource.in_use_quantity}</td>
                          <td className="px-3 py-3"><Badge tone={tone(resource.utilization_percent)}>{percent(resource.utilization_percent)}</Badge></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="rounded-lg border border-[var(--border-color)] p-3"><p className="text-xs text-[var(--text-secondary)]">Doctors</p><p className="mt-1 font-semibold">{state.staff.available_doctors}/{state.staff.total_doctors} available</p></div>
                  <div className="rounded-lg border border-[var(--border-color)] p-3"><p className="text-xs text-[var(--text-secondary)]">Appointments 24h</p><p className="mt-1 font-semibold">{state.flow.appointments_next_24h}</p></div>
                  <div className="rounded-lg border border-[var(--border-color)] p-3"><p className="text-xs text-[var(--text-secondary)]">High/Critical emergency signals</p><p className="mt-1 font-semibold">{state.flow.high_or_critical_emergencies}</p></div>
                  <div className="rounded-lg border border-[var(--border-color)] p-3"><p className="text-xs text-[var(--text-secondary)]">Allocation conflicts 24h</p><p className="mt-1 font-semibold">{state.flow.allocation_conflicts_last_24h}</p></div>
                </div>
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {Object.entries(state.source_status).map(([source, available]) => (
                    <span key={source} className="rounded-md border border-[var(--border-color)] px-2 py-1 text-[10px] uppercase tracking-wider">
                      {source.replace(/_/g, ' ')}: {available ? 'ready' : 'unavailable'}
                    </span>
                  ))}
                </div>
              </Card>

              <Card>
                <h2 className="text-sm font-semibold">Cross-Agent Loop</h2>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">The Digital Twin models state; it never silently changes the upstream agents.</p>
                <div className="mt-5 space-y-3">
                  <div className="rounded-xl border border-[var(--border-color)] p-3"><p className="text-xs uppercase tracking-wide text-primary-600">Resource Allocation → Twin</p><p className="mt-1 text-sm">Latest allocation conflicts and operational requirements feed the hospital state.</p></div>
                  <div className="rounded-xl border border-[var(--border-color)] p-3"><p className="text-xs uppercase tracking-wide text-primary-600">Emergency → Twin</p><p className="mt-1 text-sm">Emergency priority and ICU acuity signals contribute to operational pressure.</p></div>
                  <div className="rounded-xl border border-[var(--border-color)] p-3"><p className="text-xs uppercase tracking-wide text-primary-600">Scheduling → Twin</p><p className="mt-1 text-sm">Upcoming appointments and scheduling activity contribute to flow demand.</p></div>
                  <div className="rounded-xl border border-[var(--border-color)] p-3"><p className="text-xs uppercase tracking-wide text-primary-600">Twin → Operations</p><p className="mt-1 text-sm">Projected bottlenecks become advisory feedback for Emergency, Scheduling, and Resource Allocation.</p></div>
                </div>
              </Card>
            </div>

            <Card>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-sm font-semibold">What-If Hospital Simulation</h2>
                  <p className="mt-1 text-xs text-[var(--text-secondary)]">Change the assumptions below and model the next horizon without touching live inventory or appointments.</p>
                </div>
                <button type="button" onClick={runSimulation} disabled={simulate.isPending} className="rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50">
                  {simulate.isPending ? 'Simulating…' : 'Run Digital Twin Simulation'}
                </button>
              </div>
              <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <label className="text-sm"><span className="mb-1.5 block text-[var(--text-secondary)]">Horizon (hours)</span><input type="number" min={1} max={168} value={scenario.horizon_hours} onChange={(e) => setScenario({ ...scenario, horizon_hours: Number(e.target.value) })} className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5" /></label>
                {fields.map(([key, label]) => (
                  <label key={key} className="text-sm"><span className="mb-1.5 block text-[var(--text-secondary)]">{label}</span><input type="number" min={0} value={scenario[key]} onChange={(e) => setScenario({ ...scenario, [key]: Number(e.target.value) })} className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5" /></label>
                ))}
              </div>
              {simulate.isError ? <p className="mt-3 text-sm text-red-600">{getApiErrorMessage(simulate.error, 'Digital Twin simulation failed')}</p> : null}
            </Card>

            {run ? (
              <>
                <Card>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div><h2 className="text-sm font-semibold">Simulation Summary</h2><p className="mt-2 text-sm leading-relaxed">{run.simulation.summary}</p></div>
                    <Badge tone={tone(run.simulation.flow_projection.projected_operational_pressure)}>{run.simulation.flow_projection.projected_operational_pressure}/100 pressure</Badge>
                  </div>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="rounded-lg border border-[var(--border-color)] p-3"><p className="text-xs text-[var(--text-secondary)]">Projected appointments</p><p className="mt-1 text-lg font-semibold">{run.simulation.flow_projection.projected_appointments}</p></div>
                    <div className="rounded-lg border border-[var(--border-color)] p-3"><p className="text-xs text-[var(--text-secondary)]">Emergency arrivals</p><p className="mt-1 text-lg font-semibold">{run.simulation.flow_projection.projected_emergency_arrivals}</p></div>
                    <div className="rounded-lg border border-[var(--border-color)] p-3"><p className="text-xs text-[var(--text-secondary)]">Net admissions</p><p className="mt-1 text-lg font-semibold">{run.simulation.flow_projection.net_admissions}</p></div>
                    <div className="rounded-lg border border-[var(--border-color)] p-3"><p className="text-xs text-[var(--text-secondary)]">Processing</p><p className="mt-1 text-lg font-semibold">{run.processing_time_ms} ms</p></div>
                  </div>
                </Card>

                <div className="grid gap-6 lg:grid-cols-2">
                  <Card>
                    <h2 className="text-sm font-semibold">Projected Capacity</h2>
                    <div className="mt-4 space-y-2">
                      {run.simulation.resource_projections.map((item) => (
                        <div key={item.resource_type} className="rounded-xl border border-[var(--border-color)] p-3">
                          <div className="flex flex-wrap items-center justify-between gap-2"><p className="text-sm font-medium">{item.resource_type}</p><Badge tone={tone(item.status)}>{item.status}</Badge></div>
                          <div className="mt-2 grid grid-cols-3 gap-2 text-xs"><span>Baseline: <strong>{item.baseline_available}</strong></span><span>Projected: <strong>{item.projected_available}</strong></span><span>Utilization: <strong>{percent(item.projected_utilization_percent)}</strong></span></div>
                          {item.shortage ? <p className="mt-2 text-xs text-red-600">Modeled shortage: {item.shortage}</p> : null}
                        </div>
                      ))}
                    </div>
                  </Card>

                  <Card>
                    <h2 className="text-sm font-semibold">Bottleneck Detection</h2>
                    <div className="mt-4 space-y-2">
                      {run.simulation.bottlenecks.map((item) => (
                        <div key={item.resource_type + item.message} className="rounded-xl border border-[var(--border-color)] p-3">
                          <div className="flex items-center justify-between gap-2"><p className="text-sm font-medium">{item.resource_type}</p><Badge tone={tone(item.severity)}>{item.severity}</Badge></div>
                          <p className="mt-2 text-xs text-[var(--text-secondary)]">{item.message}</p>
                        </div>
                      ))}
                      {!run.simulation.bottlenecks.length ? <p className="text-sm text-[var(--text-secondary)]">No modeled bottlenecks detected.</p> : null}
                    </div>
                  </Card>
                </div>

                <Card>
                  <h2 className="text-sm font-semibold">Twin → Agent Feedback</h2>
                  <div className="mt-4 grid gap-3 lg:grid-cols-3">
                    {run.simulation.feedback_signals.map((signal, index) => (
                      <div key={signal.target_agent + signal.signal + index} className="rounded-xl border border-[var(--border-color)] p-4">
                        <div className="flex items-center justify-between gap-2"><p className="text-xs font-medium uppercase tracking-wide text-primary-600">{formatAgent(signal.target_agent)}</p><Badge tone={tone(signal.severity)}>{signal.severity}</Badge></div>
                        <p className="mt-2 text-sm">{signal.signal}</p>
                        <p className="mt-2 text-xs text-[var(--text-secondary)]"><strong>Action:</strong> {signal.recommended_action}</p>
                      </div>
                    ))}
                    {!run.simulation.feedback_signals.length ? <p className="text-sm text-[var(--text-secondary)]">No feedback signals generated for this scenario.</p> : null}
                  </div>
                </Card>

                <Card>
                  <h2 className="text-sm font-semibold">Safety / Scope</h2>
                  <div className="mt-3 space-y-1 text-xs text-[var(--text-secondary)]">
                    {run.simulation.safety_notes.map((note) => <p key={note}>• {note}</p>)}
                  </div>
                </Card>
              </>
            ) : null}

            <Card>
              <h2 className="text-sm font-semibold">Recent Simulations</h2>
              <div className="mt-4 space-y-2">
                {(historyQuery.data || []).map((item) => (
                  <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--border-color)] p-3">
                    <div><p className="text-sm font-medium">{new Date(item.created_at).toLocaleString()}</p><p className="mt-1 text-xs text-[var(--text-secondary)]">{item.horizon_hours}h · {item.summary}</p></div>
                    <Badge tone={item.status === 'Completed' ? 'green' : 'gray'}>{item.status}</Badge>
                  </div>
                ))}
                {!historyQuery.data?.length ? <p className="text-sm text-[var(--text-secondary)]">No Digital Twin simulations saved yet.</p> : null}
              </div>
            </Card>
          </>
        ) : null}
      </div>
    </ErrorBoundary>
  );
}
