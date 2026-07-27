/** Intake Stage 6 — Patient Knowledge Graph types. */

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  properties?: Record<string, unknown>;
}

export interface GraphRelationship {
  id: string;
  type: string;
  source: string;
  target: string;
  properties?: Record<string, unknown>;
}

export interface GraphStatistics {
  total_nodes?: number;
  total_relationships?: number;
  diseases?: number;
  symptoms?: number;
  medications?: number;
  doctors?: number;
  reports?: number;
  hospitals?: number;
  appointments?: number;
  procedures?: number;
  allergies?: number;
  vitals?: number;
  lab_tests?: number;
  risk_factors?: number;
  [key: string]: number | undefined;
}

export interface PatientGraphSummary {
  patient_name?: string;
  age?: number | null;
  conditions?: string[];
  current_medications?: string[];
  allergies?: string[];
  recent_procedures?: string[];
  risk_level?: string | null;
  recent_visits?: string[];
  graph_statistics?: GraphStatistics;
}

export interface KnowledgeGraph {
  id: string;
  processing_job_id?: string | null;
  patient_id: string;
  nodes_json: GraphNode[];
  relationships_json: GraphRelationship[];
  statistics_json: GraphStatistics;
  patient_summary_json: PatientGraphSummary;
  summary?: string | null;
  graph_version: number;
  node_count: number;
  relationship_count: number;
  builder_logs_json?: unknown[];
  validation_json?: Record<string, unknown>;
  status: string;
  error_message?: string | null;
  processing_time_ms?: number | null;
  created_at: string;
  updated_at?: string | null;
}

export interface KnowledgeGraphStartResult {
  job_id: string;
  patient_id: string;
  status: string;
  current_stage: string;
  next_stage: string;
  intake_completed: boolean;
  node_count: number;
  relationship_count: number;
  graph_version: number;
  processing_time_ms: number;
  summary: string;
  statistics: GraphStatistics;
  patient_summary: PatientGraphSummary;
  nodes: GraphNode[];
  relationships: GraphRelationship[];
  warnings: string[];
  knowledge_graph: KnowledgeGraph;
  processing_job: { id: string; current_stage: string; status: string };
  patient_context_version: number;
}

export const NODE_COLORS: Record<string, string> = {
  Patient: '#0f766e',
  Disease: '#dc2626',
  Symptom: '#ea580c',
  Medication: '#2563eb',
  Allergy: '#ca8a04',
  Doctor: '#0891b2',
  Hospital: '#4f46e5',
  Department: '#6366f1',
  Appointment: '#7c3aed',
  Procedure: '#9333ea',
  LabTest: '#a21caf',
  VitalSign: '#db2777',
  MedicalReport: '#57534e',
  MedicalRecord: '#57534e',
  RiskFactor: '#b91c1c',
  Insurance: '#0d9488',
  EmergencyContact: '#64748b',
};
