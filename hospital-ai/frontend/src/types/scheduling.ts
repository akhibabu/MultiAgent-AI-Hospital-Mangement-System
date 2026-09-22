export interface DoctorCandidate {
  doctor_id: string;
  doctor_name: string;
  specialization: string;
  department_id: string | null;
  department_name: string | null;
  availability_status: string;
  workload_count: number;
  score: number;
  reasons: string[];
}

export interface DoctorAssignmentResult {
  selected_doctor_id: string | null;
  selected_doctor_name: string | null;
  selection_score: number;
  candidates: DoctorCandidate[];
  rationale: string[];
}

export interface SlotRecommendation {
  doctor_id: string;
  doctor_name: string;
  appointment_date: string;
  start_time: string;
  end_time: string;
  score: number;
  reasons: string[];
}

export interface AppointmentSchedulingResult {
  recommended_slot: SlotRecommendation | null;
  alternatives: SlotRecommendation[];
  booking_status: string;
  rationale: string[];
}

export interface SurgerySchedulingResult {
  required: boolean;
  procedure_names: string[];
  duration_minutes: number | null;
  recommended_slot: SlotRecommendation | null;
  operation_theatre_status: string;
  resource_allocation_required: boolean;
  notes: string[];
}

export interface FollowUpPlan {
  recommended_date: string | null;
  interval_days: number | null;
  reason: string;
  planning_only: boolean;
}

export interface QueueItem {
  appointment_id: string;
  patient_id: string;
  patient_name: string;
  start_time: string;
  end_time: string;
  priority_level: string;
  priority_score: number;
  position: number;
}

export interface QueueOptimizationResult {
  doctor_id: string | null;
  appointment_date: string | null;
  ordered_queue: QueueItem[];
  changed_order_count: number;
  rationale: string[];
}

export interface DoctorWorkload {
  doctor_id: string;
  doctor_name: string;
  active_appointments: number;
  workload_score: number;
  availability_status: string;
}

export interface WorkloadBalancingResult {
  horizon_days: number;
  doctor_loads: DoctorWorkload[];
  balance_gap: number;
  recommendation: string;
}

export interface SchedulingResult {
  id: string;
  patient_id: string;
  processing_job_id: string | null;
  doctor_assignment_json: DoctorAssignmentResult;
  appointment_scheduling_json: AppointmentSchedulingResult;
  surgery_scheduling_json: SurgerySchedulingResult;
  follow_up_planning_json: FollowUpPlan;
  queue_optimization_json: QueueOptimizationResult;
  workload_balancing_json: WorkloadBalancingResult;
  summary: string | null;
  engine: string;
  emergency_priority_level: string;
  emergency_priority_score: number;
  visit_type: string;
  derived_department: string | null;
  derived_specialists_json: string[];
  procedures_json: string[];
  surgery_recommendation_json: string[];
  surgery_sources_json: Record<string, boolean>;
  surgery_conflict: boolean;
  source_result_ids_json: Record<string, string | null>;
  source_availability_json: Record<string, boolean>;
  recommended_tests_json: string[];
  recommended_imaging_json: string[];
  recommended_medications_json: string[];
  treatment_modes_json: string[];
  resource_requirements_json: string[];
  treatment_validation_status: string | null;
  status: string;
  warnings_json: string[];
  processing_time_ms: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface SchedulingStartResult {
  patient_id: string;
  status: string;
  processing_time_ms: number;
  summary: string;
  engine: string;
  emergency_priority_level: string;
  emergency_priority_score: number;
  visit_type: string;
  derived_department: string | null;
  derived_specialists: string[];
  procedures: string[];
  surgery_recommendation: string[];
  surgery_sources: Record<string, boolean>;
  surgery_conflict: boolean;
  source_result_ids: Record<string, string | null>;
  source_availability: Record<string, boolean>;
  recommended_tests: string[];
  recommended_imaging: string[];
  recommended_medications: string[];
  treatment_modes: string[];
  resource_requirements: string[];
  treatment_validation_status: string | null;
  warnings: string[];
  doctor_assignment: DoctorAssignmentResult;
  appointment_scheduling: AppointmentSchedulingResult;
  surgery_scheduling: SurgerySchedulingResult;
  follow_up_planning: FollowUpPlan;
  queue_optimization: QueueOptimizationResult;
  workload_balancing: WorkloadBalancingResult;
  scheduling_result: SchedulingResult;
}