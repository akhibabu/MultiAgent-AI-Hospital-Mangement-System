export type ResourceType =
  | 'Bed'
  | 'ICU Bed'
  | 'Operation Theatre'
  | 'Ventilator'
  | 'Ambulance'
  | 'Wheelchair'
  | 'Medical Equipment'
  | 'Laboratory'
  | 'Pharmacy';

export type ResourceStatus =
  | 'Available'
  | 'In Use'
  | 'Maintenance'
  | 'Out of Service';

export interface HospitalResource {
  id: string;
  resource_name: string;
  resource_type: ResourceType;
  quantity: number;
  available_quantity: number;
  status: ResourceStatus;
  location: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResourceFormValues {
  resource_name: string;
  resource_type: ResourceType;
  quantity: string;
  available_quantity: string;
  status: ResourceStatus;
  location: string;
  notes: string;
}

export interface ResourceListParams {
  page?: number;
  page_size?: number;
  search?: string;
  resource_type?: ResourceType | '';
  status?: ResourceStatus | '';
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface ResourceListResponse {
  items: HospitalResource[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const RESOURCE_TYPES: ResourceType[] = [
  'Bed',
  'ICU Bed',
  'Operation Theatre',
  'Ventilator',
  'Ambulance',
  'Wheelchair',
  'Medical Equipment',
  'Laboratory',
  'Pharmacy',
];

export const RESOURCE_STATUSES: ResourceStatus[] = [
  'Available',
  'In Use',
  'Maintenance',
  'Out of Service',
];

export const EMPTY_RESOURCE_FORM: ResourceFormValues = {
  resource_name: '',
  resource_type: 'Bed',
  quantity: '1',
  available_quantity: '1',
  status: 'Available',
  location: '',
  notes: '',
};
