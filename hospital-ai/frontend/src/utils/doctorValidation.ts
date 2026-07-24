import type { DoctorFormValues } from '@/types/doctor';

export type DoctorFormErrors = Partial<Record<keyof DoctorFormValues, string>>;

export function validateDoctorForm(values: DoctorFormValues): DoctorFormErrors {
  const errors: DoctorFormErrors = {};
  if (!values.first_name.trim()) errors.first_name = 'First name is required';
  if (!values.last_name.trim()) errors.last_name = 'Last name is required';
  if (!values.email.trim()) errors.email = 'Email is required';
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())) {
    errors.email = 'Enter a valid email';
  }
  if (!values.phone.trim()) errors.phone = 'Phone is required';
  else if (!/^[+\d][\d\s()-]{6,18}$/.test(values.phone.trim())) {
    errors.phone = 'Enter a valid phone number';
  }
  if (!values.gender) errors.gender = 'Gender is required';
  if (!values.specialization.trim()) {
    errors.specialization = 'Specialization is required';
  }
  if (values.date_of_birth) {
    const dob = new Date(values.date_of_birth);
    if (Number.isNaN(dob.getTime()) || dob > new Date()) {
      errors.date_of_birth = 'Enter a valid date of birth';
    }
  }
  const exp = Number(values.experience_years);
  if (Number.isNaN(exp) || exp < 0 || exp > 80) {
    errors.experience_years = 'Experience must be between 0 and 80';
  }
  const fee = Number(values.consultation_fee);
  if (Number.isNaN(fee) || fee < 0) {
    errors.consultation_fee = 'Consultation fee must be 0 or greater';
  }
  return errors;
}

export function doctorToFormValues(doctor: {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  gender: string;
  date_of_birth: string | null;
  department_id: string | null;
  specialization: string;
  qualification: string | null;
  experience_years: number;
  license_number: string | null;
  consultation_fee: number | string;
  availability_status: DoctorFormValues['availability_status'];
  profile_photo_url: string | null;
  bio: string | null;
}): DoctorFormValues {
  return {
    first_name: doctor.first_name,
    last_name: doctor.last_name,
    email: doctor.email,
    phone: doctor.phone,
    gender: doctor.gender as DoctorFormValues['gender'],
    date_of_birth: doctor.date_of_birth?.slice(0, 10) || '',
    department_id: doctor.department_id || '',
    specialization: doctor.specialization,
    qualification: doctor.qualification || '',
    experience_years: String(doctor.experience_years ?? 0),
    license_number: doctor.license_number || '',
    consultation_fee: String(doctor.consultation_fee ?? 0),
    availability_status: doctor.availability_status,
    profile_photo_url: doctor.profile_photo_url || '',
    bio: doctor.bio || '',
  };
}
