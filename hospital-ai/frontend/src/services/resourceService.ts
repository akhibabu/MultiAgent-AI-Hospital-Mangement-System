import apiClient from '@/services/apiClient';
import type {
  ResourceFormValues,
  ResourceListParams,
  ResourceListResponse,
  HospitalResource,
} from '@/types/resource';

function clean(values: ResourceFormValues) {
  return {
    resource_name: values.resource_name.trim(),
    resource_type: values.resource_type,
    quantity: Number(values.quantity) || 0,
    available_quantity: Number(values.available_quantity) || 0,
    status: values.status,
    location: values.location.trim() || null,
    notes: values.notes.trim() || null,
  };
}

export const resourceService = {
  async list(params: ResourceListParams = {}): Promise<ResourceListResponse> {
    const { data } = await apiClient.get<ResourceListResponse>('/resources', {
      params: {
        page: params.page ?? 1,
        page_size: params.page_size ?? 10,
        search: params.search || undefined,
        resource_type: params.resource_type || undefined,
        status: params.status || undefined,
        sort_by: params.sort_by ?? 'created_at',
        sort_order: params.sort_order ?? 'desc',
      },
    });
    return data;
  },
  async create(values: ResourceFormValues): Promise<HospitalResource> {
    const { data } = await apiClient.post<HospitalResource>(
      '/resources',
      clean(values),
    );
    return data;
  },
  async update(
    id: string,
    values: ResourceFormValues,
  ): Promise<HospitalResource> {
    const { data } = await apiClient.put<HospitalResource>(
      `/resources/${id}`,
      clean(values),
    );
    return data;
  },
  async remove(id: string): Promise<void> {
    await apiClient.delete(`/resources/${id}`);
  },
};
