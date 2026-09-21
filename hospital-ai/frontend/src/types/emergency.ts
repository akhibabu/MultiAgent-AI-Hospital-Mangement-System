export interface VitalObservation {
  name: string;
  value: string;
  unit: string;
  status: string;
  severity: string;
  message: string;
}
export interface VitalMonitoringResult {
  observed_at: string;
  observations: VitalObservation[];
  abnormal_count: number;
  critical_count: number;
  monitoring_status: string;
  data_source: string;
  limitations: string[];
}
export interface CriticalEvent {
  event_type: string;
  severity: string;
  detected: boolean;
  evidence: string[];
  message: string;
}
export interface CriticalEventDetectionResult {
  events: CriticalEvent[];
  detected_event_count: number;
  critical_event_count: number;
  detection_mode: string;
}
export interface TriageClassification {
  category: string;
  score: number;
  escalation_required: boolean;
  reasons: string[];
  evidence: string[];
  disclaimer: string;
}
export interface ICURequirementResult {
  signal: string;
  score: number;
  confidence: number;
  reasons: string[];
  evidence: string[];
  limitation: string;
}
export interface EmergencyAlert {
  code: string;
  severity: string;
  title: string;
  message: string;
  recommended_next_step: string;
  requires_acknowledgement: boolean;
}
export interface EmergencyAlertGenerationResult {
  alerts: EmergencyAlert[];
  alert_count: number;
  highest_severity: string;
  delivery_mode: string;
}
export interface PatientPriorityRanking {
  priority_score: number;
  priority_level: string;
  rank_basis: string;
  factors: string[];
  disclaimer: string;
}
export interface EmergencyResult {
  id: string;
  patient_id: string;
  processing_job_id?: string | null;
  vital_monitoring_json: VitalMonitoringResult;
  triage_classification_json: TriageClassification;
  critical_event_detection_json: CriticalEventDetectionResult;
  icu_requirement_json: ICURequirementResult;
  emergency_alerts_json: EmergencyAlertGenerationResult;
  patient_priority_json: PatientPriorityRanking;
  summary?: string | null;
  engine: string;
  status: string;
  warnings_json: string[];
  processing_time_ms?: number | null;
  created_at: string;
  updated_at?: string | null;
}
export interface EmergencyStartResult {
  patient_id: string;
  status: string;
  processing_time_ms: number;
  summary: string;
  engine: string;
  warnings: string[];
  vital_monitoring: VitalMonitoringResult;
  triage_classification: TriageClassification;
  critical_event_detection: CriticalEventDetectionResult;
  icu_requirement: ICURequirementResult;
  emergency_alerts: EmergencyAlertGenerationResult;
  patient_priority: PatientPriorityRanking;
  emergency_result: EmergencyResult;
}
