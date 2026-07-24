import apiClient from '@/services/apiClient';
import type {
  AvailabilityFormValues,
  Department,
  DepartmentFormValues,
  DepartmentListResponse,
  Doctor,
  DoctorAvailability,
  DoctorFormValues,
  DoctorListParams,
  DoctorListResponse,
} from '@/types/doctor';

function cleanDoctorPayload(values: DoctorFormValues) {
  return {
    first_name: values.first_name.trim(),
    last_name: values.last_name.trim(),
    email: values.email.trim(),
    phone: values.phone.trim(),
    gender: values.gender,
    date_of_birth: values.date_of_birth || null,
    department_id: values.department_id || null,
    specialization: values.specialization.trim(),
    qualification: values.qualification.trim() || null,
    experience_years: Number(values.experience_years) || 0,
    license_number: values.license_number.trim() || null,
    consultation_fee: Number(values.consultation_fee) || 0,
    availability_status: values.availability_status,
    profile_photo_url: values.profile_photo_url.trim() || null,
    bio: values.bio.trim() || null,
  };
}

function cleanDepartmentPayload(values: DepartmentFormValues) {
  return {
    name: values.name.trim(),
    description: values.description.trim() || null,
    floor_number: values.floor_number ? Number(values.floor_number) : null,
    head_doctor_id: values.head_doctor_id || null,
  };
}

export const doctorService = {
  async list(params: DoctorListParams = {}): Promise<DoctorListResponse> {
    const { data } = await apiClient.get<DoctorListResponse>('/doctors', {
      params: {
        page: params.page ?? 1,
        page_size: params.page_size ?? 10,
        search: params.search || undefined,
        department_id: params.department_id || undefined,
        availability_status: params.availability_status || undefined,
        min_experience:
          params.min_experience === '' || params.min_experience == null
            ? undefined
            : params.min_experience,
        sort_by: params.sort_by ?? 'created_at',
        sort_order: params.sort_order ?? 'desc',
      },
    });
    return data;
  },

  async getById(id: string): Promise<Doctor> {
    const { data } = await apiClient.get<Doctor>(`/doctors/${id}`);
    return data;
  },

  async create(values: DoctorFormValues): Promise<Doctor> {
    const { data } = await apiClient.post<Doctor>(
      '/doctors',
      cleanDoctorPayload(values),
    );
    return data;
  },

  async update(id: string, values: DoctorFormValues): Promise<Doctor> {
    const { data } = await apiClient.put<Doctor>(
      `/doctors/${id}`,
      cleanDoctorPayload(values),
    );
    return data;
  },

  async remove(id: string): Promise<void> {
    await apiClient.delete(`/doctors/${id}`);
  },

  async listAvailability(doctorId: string): Promise<DoctorAvailability[]> {
    const { data } = await apiClient.get<{ items: DoctorAvailability[] }>(
      `/doctors/${doctorId}/availability`,
    );
    return data.items;
  },

  async addAvailability(
    doctorId: string,
    values: AvailabilityFormValues,
  ): Promise<DoctorAvailability> {
    const { data } = await apiClient.post<DoctorAvailability>(
      `/doctors/${doctorId}/availability`,
      {
        day_of_week: values.day_of_week,
        start_time: values.start_time.length === 5
          ? `${values.start_time}:00`
          : values.start_time,
        end_time: values.end_time.length === 5
          ? `${values.end_time}:00`
          : values.end_time,
        slot_duration: Number(values.slot_duration) || 30,
        is_available: values.is_available,
      },
    );
    return data;
  },

  async updateAvailability(
    slotId: string,
    values: Partial<AvailabilityFormValues>,
  ): Promise<DoctorAvailability> {
    const body: Record<string, unknown> = {};
    if (values.day_of_week != null) body.day_of_week = values.day_of_week;
    if (values.start_time) {
      body.start_time =
        values.start_time.length === 5
          ? `${values.start_time}:00`
          : values.start_time;
    }
    if (values.end_time) {
      body.end_time =
        values.end_time.length === 5 ? `${values.end_time}:00` : values.end_time;
    }
    if (values.slot_duration != null) {
      body.slot_duration = Number(values.slot_duration);
    }
    if (values.is_available != null) body.is_available = values.is_available;
    const { data } = await apiClient.put<DoctorAvailability>(
      `/availability/${slotId}`,
      body,
    );
    return data;
  },

  async removeAvailability(slotId: string): Promise<void> {
    await apiClient.delete(`/availability/${slotId}`);
  },
};

export const departmentService = {
  async list(search?: string): Promise<DepartmentListResponse> {
    const { data } = await apiClient.get<DepartmentListResponse>('/departments', {
      params: { search: search || undefined },
    });
    return data;
  },

  async getById(id: string): Promise<Department> {
    const { data } = await apiClient.get<Department>(`/departments/${id}`);
    return data;
  },

  async create(values: DepartmentFormValues): Promise<Department> {
    const { data } = await apiClient.post<Department>(
      '/departments',
      cleanDepartmentPayload(values),
    );
    return data;
  },

  async update(id: string, values: DepartmentFormValues): Promise<Department> {
    const { data } = await apiClient.put<Department>(
      `/departments/${id}`,
      cleanDepartmentPayload(values),
    );
    return data;
  },

  async remove(id: string): Promise<void> {
    await apiClient.delete(`/departments/${id}`);
  },
};
