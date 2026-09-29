export interface DigitalTwinScenario {
  horizon_hours: number;
  emergency_arrivals: number;
  planned_admissions: number;
  expected_discharges: number;
  icu_admissions: number;
  icu_discharges: number;
  ventilator_demand: number;
  additional_theatre_demand: number;
  staff_absent: number;
  additional_appointments: number;
}

export interface ResourceTwinState {
  resource_type: string;
  total_quantity: number;
  available_quantity: number;
  in_use_quantity: number;
  maintenance_quantity: number;
  out_of_service_quantity: number;
  utilization_percent: number;
}

export interface StaffTwinState {
  total_doctors: number;
  available_doctors: number;
  busy_doctors: number;
  on_leave_doctors: number;
  utilization_percent: number;
}

export interface FlowTwinState {
  appointments_next_24h: number;
  appointments_next_7d: number;
  emergency_results_last_24h: number;
  high_or_critical_emergencies: number;
  icu_signals_last_24h: number;
  scheduling_runs_last_24h: number;
  allocation_runs_last_24h: number;
  allocation_conflicts_last_24h: number;
}

export interface HospitalTwinState {
  captured_at: string;
  resources: ResourceTwinState[];
  staff: StaffTwinState;
  flow: FlowTwinState;
  operational_pressure: number;
  source_status: Record<string, boolean>;
  source_timestamps: Record<string, string>;
}

export interface ProjectionMetric {
  resource_type: string;
  baseline_available: number;
  projected_available: number;
  projected_utilization_percent: number;
  shortage: number;
  status: string;
}

export interface FlowProjection {
  projected_appointments: number;
  projected_emergency_arrivals: number;
  net_admissions: number;
  projected_operational_pressure: number;
}

export interface BottleneckSignal {
  resource_type: string;
  severity: string;
  message: string;
  current_utilization_percent: number;
  projected_utilization_percent: number;
  shortage: number;
}

export interface TwinFeedbackSignal {
  target_agent: string;
  signal: string;
  recommended_action: string;
  severity: string;
}

export interface DigitalTwinSimulation {
  scenario: DigitalTwinScenario;
  resource_projections: ProjectionMetric[];
  flow_projection: FlowProjection;
  bottlenecks: BottleneckSignal[];
  feedback_signals: TwinFeedbackSignal[];
  summary: string;
  safety_notes: string[];
  generated_at: string;
}

export interface DigitalTwinRun {
  id: string;
  created_at: string;
  status: string;
  engine: string;
  baseline_state: HospitalTwinState;
  simulation: DigitalTwinSimulation;
  processing_time_ms: number;
}

export interface DigitalTwinStateResponse {
  state: HospitalTwinState;
}

export interface DigitalTwinHistoryItem {
  id: string;
  created_at: string;
  status: string;
  engine: string;
  horizon_hours: number;
  processing_time_ms: number | null;
  summary: string;
}
