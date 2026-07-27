/**
 * Interactive Patient Knowledge Graph viewer (Intake Stage 6).
 * Zoom, pan, drag, search highlight, node inspector.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  MarkerType,
  Handle,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  NODE_COLORS,
  type GraphNode,
  type GraphRelationship,
  type GraphStatistics,
  type PatientGraphSummary,
} from '@/types/knowledgeGraph';

type KgNodeData = {
  label: string;
  nodeType: string;
  properties: Record<string, unknown>;
  dimmed: boolean;
  highlighted: boolean;
  selected: boolean;
};

function layoutNodes(
  nodes: GraphNode[],
  highlighted: Set<string>,
  selectedId: string | null,
  dimOthers: boolean,
): Node<KgNodeData>[] {
  const patient = nodes.find((n) => n.type === 'Patient');
  const others = nodes.filter((n) => n.id !== patient?.id);
  const cx = 420;
  const cy = 280;
  const radius = Math.max(180, Math.min(360, 40 + others.length * 18));

  const placed: GraphNode[] = patient ? [patient, ...others] : [...nodes];

  return placed.map((n, i) => {
    let x = cx;
    let y = cy;
    if (!(patient && n.id === patient.id)) {
      const ringIndex = patient ? i - 1 : i;
      const count = Math.max(1, others.length || nodes.length);
      const a = (ringIndex / count) * Math.PI * 2 - Math.PI / 2;
      x = cx + Math.cos(a) * radius;
      y = cy + Math.sin(a) * radius;
    }

    const isHl = highlighted.size === 0 || highlighted.has(n.id);
    return {
      id: n.id,
      type: 'kg',
      position: { x, y },
      data: {
        label: n.label,
        nodeType: n.type,
        properties: n.properties || {},
        dimmed: dimOthers && highlighted.size > 0 && !isHl,
        highlighted: highlighted.has(n.id),
        selected: selectedId === n.id,
      },
      draggable: true,
    };
  });
}

function KgNode({ data }: NodeProps<Node<KgNodeData>>) {
  const color = NODE_COLORS[data.nodeType] || '#64748b';
  return (
    <div
      className="relative min-w-[100px] max-w-[160px] rounded-xl border-2 px-3 py-2 text-center shadow-sm transition"
      style={{
        borderColor: data.selected || data.highlighted ? color : `${color}99`,
        background: data.dimmed ? 'var(--bg-navbar)' : `${color}18`,
        opacity: data.dimmed ? 0.28 : 1,
        boxShadow: data.selected ? `0 0 0 3px ${color}55` : undefined,
      }}
    >
      <Handle type="target" position={Position.Top} className="!h-2 !w-2 !bg-slate-400" />
      <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color }}>
        {data.nodeType}
      </p>
      <p className="mt-0.5 text-xs font-semibold leading-snug text-[var(--text-primary)]">
        {data.label}
      </p>
      <Handle type="source" position={Position.Bottom} className="!h-2 !w-2 !bg-slate-400" />
    </div>
  );
}

const nodeTypes = { kg: KgNode };

const STAT_KEYS: { key: keyof GraphStatistics; label: string }[] = [
  { key: 'total_nodes', label: 'Total Nodes' },
  { key: 'total_relationships', label: 'Total Relationships' },
  { key: 'diseases', label: 'Diseases' },
  { key: 'symptoms', label: 'Symptoms' },
  { key: 'medications', label: 'Medications' },
  { key: 'doctors', label: 'Doctors' },
  { key: 'reports', label: 'Reports' },
  { key: 'hospitals', label: 'Hospitals' },
  { key: 'appointments', label: 'Appointments' },
  { key: 'procedures', label: 'Procedures' },
];

export interface PatientKnowledgeGraphViewerProps {
  nodes: GraphNode[];
  relationships: GraphRelationship[];
  statistics?: GraphStatistics | null;
  patientSummary?: PatientGraphSummary | null;
  summary?: string | null;
  graphVersion?: number;
  nodeCount?: number;
  relationshipCount?: number;
}

export default function PatientKnowledgeGraphViewer({
  nodes,
  relationships,
  statistics,
  patientSummary,
  summary,
  graphVersion,
  nodeCount,
  relationshipCount,
}: PatientKnowledgeGraphViewerProps) {
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [relFilter, setRelFilter] = useState('');

  const nodeById = useMemo(() => {
    const m = new Map<string, GraphNode>();
    nodes.forEach((n) => m.set(n.id, n));
    return m;
  }, [nodes]);

  const adjacency = useMemo(() => {
    const m = new Map<string, Set<string>>();
    relationships.forEach((r) => {
      if (!m.has(r.source)) m.set(r.source, new Set());
      if (!m.has(r.target)) m.set(r.target, new Set());
      m.get(r.source)!.add(r.target);
      m.get(r.target)!.add(r.source);
    });
    return m;
  }, [relationships]);

  const highlighted = useMemo(() => {
    const q = search.trim().toLowerCase();
    const set = new Set<string>();
    if (!q) return set;
    const seeds = nodes.filter(
      (n) =>
        n.label.toLowerCase().includes(q) ||
        n.type.toLowerCase().includes(q) ||
        n.id.toLowerCase().includes(q),
    );
    seeds.forEach((s) => {
      set.add(s.id);
      adjacency.get(s.id)?.forEach((nbr) => set.add(nbr));
    });
    return set;
  }, [search, nodes, adjacency]);

  const flowNodes = useMemo(
    () => layoutNodes(nodes, highlighted, selectedId, Boolean(search.trim())),
    [nodes, highlighted, selectedId, search],
  );

  const flowEdges: Edge[] = useMemo(() => {
    const dim = Boolean(search.trim()) && highlighted.size > 0;
    return relationships.map((r) => {
      const active =
        !dim || (highlighted.has(r.source) && highlighted.has(r.target));
      return {
        id: r.id,
        source: r.source,
        target: r.target,
        label: r.type.replace(/_/g, ' '),
        animated: active && (highlighted.has(r.source) || highlighted.has(r.target)),
        style: {
          stroke: active ? '#0f766e' : '#94a3b8',
          strokeOpacity: active ? 0.85 : 0.15,
          strokeWidth: active ? 1.5 : 1,
        },
        labelStyle: {
          fill: 'var(--text-secondary)',
          fontSize: 9,
          opacity: active ? 1 : 0.2,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: active ? '#0f766e' : '#94a3b8',
          width: 16,
          height: 16,
        },
      };
    });
  }, [relationships, highlighted, search]);

  const selected = selectedId ? nodeById.get(selectedId) : null;
  const selectedRels = useMemo(() => {
    if (!selectedId) return [];
    return relationships.filter(
      (r) => r.source === selectedId || r.target === selectedId,
    );
  }, [relationships, selectedId]);

  const filteredRels = useMemo(() => {
    const q = relFilter.trim().toLowerCase();
    if (!q) return relationships.slice(0, 40);
    return relationships
      .filter((r) => {
        const src = nodeById.get(r.source)?.label || '';
        const tgt = nodeById.get(r.target)?.label || '';
        return (
          r.type.toLowerCase().includes(q) ||
          src.toLowerCase().includes(q) ||
          tgt.toLowerCase().includes(q)
        );
      })
      .slice(0, 40);
  }, [relationships, relFilter, nodeById]);

  const onNodeClick = useCallback((_: unknown, node: Node) => {
    setSelectedId(node.id);
  }, []);

  useEffect(() => {
    if (!selectedId && nodes.length) {
      const patient = nodes.find((n) => n.type === 'Patient');
      setSelectedId(patient?.id || nodes[0].id);
    }
  }, [nodes, selectedId]);

  const stats = statistics || {};
  const summaryCard = patientSummary || {};

  return (
    <div className="space-y-6">
      {/* Overview */}
      <div className="rounded-xl border border-[var(--border-color)] p-4">
        <p className="text-xs uppercase tracking-wide text-[var(--text-secondary)]">
          Knowledge Graph Overview
        </p>
        <p className="mt-2 text-sm leading-relaxed text-[var(--text-primary)]">
          {summary ||
            'Structured patient knowledge graph ready for downstream AI agents.'}
        </p>
        <div className="mt-3 flex flex-wrap gap-3 text-xs text-[var(--text-secondary)]">
          <span>
            Version <strong className="text-[var(--text-primary)]">{graphVersion ?? 1}</strong>
          </span>
          <span>
            Nodes{' '}
            <strong className="text-[var(--text-primary)]">
              {nodeCount ?? nodes.length}
            </strong>
          </span>
          <span>
            Relationships{' '}
            <strong className="text-[var(--text-primary)]">
              {relationshipCount ?? relationships.length}
            </strong>
          </span>
        </div>
      </div>

      {/* Patient summary + stats */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-[var(--border-color)] p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
            Patient Summary
          </p>
          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between gap-2">
              <dt className="text-[var(--text-secondary)]">Name</dt>
              <dd className="font-medium">{summaryCard.patient_name || '—'}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-[var(--text-secondary)]">Age</dt>
              <dd className="font-medium">
                {summaryCard.age != null ? summaryCard.age : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-[var(--text-secondary)]">Conditions</dt>
              <dd className="mt-1">
                {summaryCard.conditions?.length
                  ? summaryCard.conditions.join(', ')
                  : 'None'}
              </dd>
            </div>
            <div>
              <dt className="text-[var(--text-secondary)]">Medications</dt>
              <dd className="mt-1">
                {summaryCard.current_medications?.length
                  ? summaryCard.current_medications.join(', ')
                  : 'None'}
              </dd>
            </div>
            <div>
              <dt className="text-[var(--text-secondary)]">Allergies</dt>
              <dd className="mt-1">
                {summaryCard.allergies?.length
                  ? summaryCard.allergies.join(', ')
                  : 'None'}
              </dd>
            </div>
            <div>
              <dt className="text-[var(--text-secondary)]">Recent procedures</dt>
              <dd className="mt-1">
                {summaryCard.recent_procedures?.length
                  ? summaryCard.recent_procedures.join(', ')
                  : 'None'}
              </dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-[var(--text-secondary)]">Risk level</dt>
              <dd className="font-medium">{summaryCard.risk_level || '—'}</dd>
            </div>
            <div>
              <dt className="text-[var(--text-secondary)]">Recent visits</dt>
              <dd className="mt-1">
                {summaryCard.recent_visits?.length
                  ? summaryCard.recent_visits.join(', ')
                  : 'None'}
              </dd>
            </div>
          </dl>
        </div>

        <div className="rounded-xl border border-[var(--border-color)] p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
            Graph Statistics
          </p>
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
            {STAT_KEYS.map(({ key, label }) => (
              <div
                key={key}
                className="rounded-lg border border-[var(--border-color)] px-3 py-2"
              >
                <p className="text-[10px] uppercase tracking-wide text-[var(--text-secondary)]">
                  {label}
                </p>
                <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">
                  {stats[key] ?? (key === 'total_nodes' ? nodes.length : key === 'total_relationships' ? relationships.length : 0)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Search + interactive graph */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex-1 min-w-[200px]">
            <span className="sr-only">Search graph</span>
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search nodes (e.g. Diabetes, Metformin)…"
              className="w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2.5 text-sm outline-none focus:border-primary-500"
            />
          </label>
          {search ? (
            <button
              type="button"
              onClick={() => setSearch('')}
              className="rounded-xl border border-[var(--border-color)] px-3 py-2 text-sm"
            >
              Clear highlight
            </button>
          ) : null}
        </div>

        <div className="h-[420px] overflow-hidden rounded-xl border border-[var(--border-color)] bg-[var(--bg-body,#f8fafc)] dark:bg-black/20">
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
            onNodeClick={onNodeClick}
            onPaneClick={() => setSelectedId(null)}
            fitView
            minZoom={0.2}
            maxZoom={2}
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={18} size={1} />
            <Controls showInteractive={false} />
            <MiniMap
              nodeStrokeWidth={2}
              zoomable
              pannable
              className="!bg-[var(--bg-navbar)]"
            />
          </ReactFlow>
        </div>
        <p className="text-xs text-[var(--text-secondary)]">
          Drag nodes · scroll to zoom · pan the canvas · click a node to inspect.
        </p>
      </div>

      {/* Inspector + relationship explorer */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-[var(--border-color)] p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
            Node Inspector
          </p>
          {!selected ? (
            <p className="mt-3 text-sm text-[var(--text-secondary)]">
              Click a node on the graph.
            </p>
          ) : (
            <div className="mt-3 space-y-3 text-sm">
              <div>
                <p className="text-xs text-[var(--text-secondary)]">Type</p>
                <p className="font-semibold">{selected.type}</p>
              </div>
              <div>
                <p className="text-xs text-[var(--text-secondary)]">Label</p>
                <p className="font-medium">{selected.label}</p>
              </div>
              <div>
                <p className="text-xs text-[var(--text-secondary)]">Properties</p>
                <ul className="mt-1 space-y-1 text-[var(--text-secondary)]">
                  {Object.entries(selected.properties || {}).length ? (
                    Object.entries(selected.properties || {}).map(([k, v]) => (
                      <li key={k}>
                        <span className="text-[var(--text-primary)]">{k}</span>: {String(v)}
                      </li>
                    ))
                  ) : (
                    <li>No extra properties</li>
                  )}
                </ul>
              </div>
              <div>
                <p className="text-xs text-[var(--text-secondary)]">
                  Source report / confidence
                </p>
                <p className="mt-1">
                  {String(
                    selected.properties?.source_report ||
                      selected.properties?.source ||
                      '—',
                  )}
                  {selected.properties?.confidence != null
                    ? ` · ${Math.round(Number(selected.properties.confidence) * (Number(selected.properties.confidence) <= 1 ? 100 : 1))}%`
                    : ''}
                </p>
              </div>
              <div>
                <p className="text-xs text-[var(--text-secondary)]">Relationships</p>
                <ul className="mt-1 max-h-36 space-y-1 overflow-auto">
                  {selectedRels.length ? (
                    selectedRels.map((r) => {
                      const otherId = r.source === selected.id ? r.target : r.source;
                      const other = nodeById.get(otherId);
                      const dir = r.source === selected.id ? '→' : '←';
                      return (
                        <li key={r.id}>
                          <button
                            type="button"
                            className="text-left text-primary-600 hover:underline"
                            onClick={() => setSelectedId(otherId)}
                          >
                            {r.type} {dir} {other?.label || otherId}
                          </button>
                        </li>
                      );
                    })
                  ) : (
                    <li className="text-[var(--text-secondary)]">None</li>
                  )}
                </ul>
              </div>
            </div>
          )}
        </div>

        <div className="rounded-xl border border-[var(--border-color)] p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
            Relationship Explorer
          </p>
          <input
            type="search"
            value={relFilter}
            onChange={(e) => setRelFilter(e.target.value)}
            placeholder="Filter relationships…"
            className="mt-3 w-full rounded-xl border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-500"
          />
          <ul className="mt-3 max-h-64 space-y-2 overflow-auto text-sm">
            {filteredRels.map((r) => (
              <li
                key={r.id}
                className="rounded-lg border border-[var(--border-color)] px-3 py-2"
              >
                <p className="text-[10px] uppercase tracking-wide text-[var(--text-secondary)]">
                  {r.type}
                </p>
                <p className="mt-0.5">
                  <button
                    type="button"
                    className="font-medium text-primary-600 hover:underline"
                    onClick={() => setSelectedId(r.source)}
                  >
                    {nodeById.get(r.source)?.label || r.source}
                  </button>
                  <span className="mx-1.5 text-[var(--text-secondary)]">→</span>
                  <button
                    type="button"
                    className="font-medium text-primary-600 hover:underline"
                    onClick={() => setSelectedId(r.target)}
                  >
                    {nodeById.get(r.target)?.label || r.target}
                  </button>
                </p>
              </li>
            ))}
            {!filteredRels.length ? (
              <li className="text-[var(--text-secondary)]">No relationships match.</li>
            ) : null}
          </ul>
        </div>
      </div>
    </div>
  );
}
