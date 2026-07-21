import apiClient from '@/services/apiClient';
import type {
  Patient,
  PatientFormValues,
  PatientListParams,
  PatientListResponse,
} from '@/types/patient';

function cleanPayload(values: PatientFormValues) {
  return {
    first_name: values.first_name.trim(),
    last_name: values.last_name.trim(),
    date_of_birth: values.date_of_birth,
    gender: values.gender,
    blood_group: values.blood_group || null,
    phone: values.phone.trim(),
    email: values.email.trim() || null,
    address: values.address.trim() || null,
    city: values.city.trim() || null,
    state: values.state.trim() || null,
    country: values.country.trim() || null,
    emergency_contact_name: values.emergency_contact_name.trim() || null,
    emergency_contact_phone: values.emergency_contact_phone.trim() || null,
    allergies: values.allergies.trim() || null,
    medical_history: values.medical_history.trim() || null,
    current_medications: values.current_medications.trim() || null,
    insurance_provider: values.insurance_provider.trim() || null,
    insurance_number: values.insurance_number.trim() || null,
  };
}

export const patientService = {
  async list(params: PatientListParams = {}): Promise<PatientListResponse> {
    const { data } = await apiClient.get<PatientListResponse>('/patients', {
      params: {
        page: params.page ?? 1,
        page_size: params.page_size ?? 10,
        search: params.search || undefined,
        gender: params.gender || undefined,
        blood_group: params.blood_group || undefined,
        sort_by: params.sort_by ?? 'created_at',
        sort_order: params.sort_order ?? 'desc',
      },
    });
    return data;
  },

  async getById(id: string): Promise<Patient> {
    const { data } = await apiClient.get<Patient>(`/patients/${id}`);
    return data;
  },

  async create(values: PatientFormValues): Promise<Patient> {
    const { data } = await apiClient.post<Patient>(
      '/patients',
      cleanPayload(values),
    );
    return data;
  },

  async update(id: string, values: PatientFormValues): Promise<Patient> {
    const { data } = await apiClient.put<Patient>(
      `/patients/${id}`,
      cleanPayload(values),
    );
    return data;
  },

  async remove(id: string): Promise<void> {
    await apiClient.delete(`/patients/${id}`);
  },
};

export default patientService;
