/** Intake Agent types — Patient Context is the sole downstream input. */

export type DocumentJobStatus =
  | 'Queued'
  | 'Validating'
  | 'OCR'
  | 'EntityExtraction'
  | 'RiskProfiling'
  | 'KnowledgeGraph'
  | 'ContextBuild'
  | 'Completed'
  | 'Failed';

export interface TimelineStep {
  step: string;
  detail: string;
  at: string;
}

export interface DocumentProcessingJob {
  id: string;
  patient_id: string;
  medical_record_id?: string | null;
  document_id?: string | null;
  appointment_id?: string | null;
  doctor_id?: string | null;
  status: DocumentJobStatus | string;
  current_step?: string | null;
  progress_pct: number;
  ocr_provider?: string | null;
  ocr_text?: string | null;
  ocr_confidence?: number | null;
  extracted_entities?: Record<string, unknown> | null;
  risk_profile?: Record<string, unknown> | null;
  knowledge_graph_refs?: Record<string, unknown> | null;
  patient_context?: Record<string, unknown> | null;
  timeline?: TimelineStep[] | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
}

export interface PatientAIContext {
  id: string;
  patient_id: string;
  context_version: number;
  context_json: Record<string, unknown>;
  medical_history_summary?: string | null;
  risk_level?: string | null;
  risk_profile?: Record<string, unknown> | null;
  confidence_score?: number | null;
  knowledge_graph_id?: string | null;
  source_job_ids?: string[] | null;
  source_document_ids?: string[] | null;
  built_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeGraphPreview {
  id: string;
  patient_id: string;
  graph_version: number;
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
  summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface IntakeDocumentMeta {
  id: string;
  medical_record_id: string;
  file_name: string;
  file_type?: string;
  file_size?: number;
  created_at: string;
}

export interface IntakeDashboard {
  patient_id: string;
  context: PatientAIContext | null;
  knowledge_graph: KnowledgeGraphPreview | null;
  jobs: DocumentProcessingJob[];
  documents: IntakeDocumentMeta[];
}

export interface IntakeProcessResult {
  job_id: string;
  patient_id: string;
  document_id: string;
  status: string;
  patient_context: Record<string, unknown>;
  entities: Record<string, unknown>;
  risk_profile: Record<string, unknown>;
  knowledge_graph: Record<string, unknown>;
  ocr: Record<string, unknown>;
  timeline: TimelineStep[];
  confidence_score: number;
  diagnosis_request_preview?: Record<string, unknown> | null;
}
