export interface ResourceRequirement {
  requirement: string;
  resource_type: string | null;
  required_quantity: number;
  source: string;
  rationale: string;
  priority: number;
}

export interface MatchedResource {
  resource_id: string;
  resource_name: string;
  resource_type: string;
  available_quantity: number;
  location?: string | null;
}

export interface ResourceAllocationItem {
  requirement: string;
  resource_type: string | null;
  required_quantity: number;
  available_quantity: number;
  allocated_quantity: number;
  shortage_quantity: number;
  status: string;
  priority: number;
  source: string;
  rationale: string;
  matched_resources: MatchedResource[];
}

export interface AllocationConflict {
  code: string;
  severity: string;
  message: string;
  requirement?: string | null;
  recommended_action: string;
}

export interface ResourceAllocationResult {
  id: string;
  patient_id: string;
  status: string;
  engine: string;
  planning_only: boolean;
  priority_level: string;
  priority_score: number;
  requirements_json: ResourceRequirement[];
  allocations_json: ResourceAllocationItem[];
  conflicts_json: AllocationConflict[];
  allocation_score: number;
  source_result_ids_json: Record<string, string | null>;
  source_availability_json: Record<string, boolean>;
  summary: string | null;
  warnings_json: string[];
  processing_time_ms: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface ResourceAllocationStartResult {
  patient_id: string;
  status: string;
  processing_time_ms: number;
  summary: string;
  engine: string;
  planning_only: boolean;
  priority_level: string;
  priority_score: number;
  requirements: ResourceRequirement[];
  allocations: ResourceAllocationItem[];
  conflicts: AllocationConflict[];
  allocation_score: number;
  source_result_ids: Record<string, string | null>;
  source_availability: Record<string, boolean>;
  warnings: string[];
  resource_allocation_result: ResourceAllocationResult;
}
