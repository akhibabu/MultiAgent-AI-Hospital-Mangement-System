import type { PatientFormValues } from '@/types/patient';

export type PatientFormErrors = Partial<Record<keyof PatientFormValues, string>>;

export function validatePatientForm(
  values: PatientFormValues,
): PatientFormErrors {
  const errors: PatientFormErrors = {};

  if (!values.first_name.trim()) errors.first_name = 'First name is required';
  if (!values.last_name.trim()) errors.last_name = 'Last name is required';

  if (!values.date_of_birth) {
    errors.date_of_birth = 'Date of birth is required';
  } else {
    const dob = new Date(values.date_of_birth);
    const today = new Date();
    if (Number.isNaN(dob.getTime())) {
      errors.date_of_birth = 'Enter a valid date';
    } else if (dob > today) {
      errors.date_of_birth = 'Date of birth cannot be in the future';
    } else if (dob.getFullYear() < 1900) {
      errors.date_of_birth = 'Date of birth is unrealistically old';
    }
  }

  if (!values.gender) errors.gender = 'Gender is required';

  if (!values.phone.trim()) {
    errors.phone = 'Phone is required';
  } else if (!/^[+\d][\d\s()-]{6,18}$/.test(values.phone.trim())) {
    errors.phone = 'Enter a valid phone number';
  }

  if (values.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())) {
    errors.email = 'Enter a valid email address';
  }

  if (
    values.emergency_contact_phone.trim() &&
    !/^[+\d][\d\s()-]{6,18}$/.test(values.emergency_contact_phone.trim())
  ) {
    errors.emergency_contact_phone = 'Enter a valid phone number';
  }

  return errors;
}

export function patientToFormValues(
  patient: {
    first_name: string;
    last_name: string;
    date_of_birth: string;
    gender: string;
    blood_group: string | null;
    phone: string;
    email: string | null;
    address: string | null;
    city: string | null;
    state: string | null;
    country: string | null;
    emergency_contact_name: string | null;
    emergency_contact_phone: string | null;
    allergies: string | null;
    medical_history: string | null;
    current_medications: string | null;
    insurance_provider: string | null;
    insurance_number: string | null;
  },
): PatientFormValues {
  return {
    first_name: patient.first_name,
    last_name: patient.last_name,
    date_of_birth: patient.date_of_birth.slice(0, 10),
    gender: patient.gender as PatientFormValues['gender'],
    blood_group: (patient.blood_group || '') as PatientFormValues['blood_group'],
    phone: patient.phone,
    email: patient.email || '',
    address: patient.address || '',
    city: patient.city || '',
    state: patient.state || '',
    country: patient.country || 'India',
    emergency_contact_name: patient.emergency_contact_name || '',
    emergency_contact_phone: patient.emergency_contact_phone || '',
    allergies: patient.allergies || '',
    medical_history: patient.medical_history || '',
    current_medications: patient.current_medications || '',
    insurance_provider: patient.insurance_provider || '',
    insurance_number: patient.insurance_number || '',
  };
}
