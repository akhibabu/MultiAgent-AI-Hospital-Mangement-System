import { type FormEvent, useEffect, useState } from 'react';
import { TextInput, TextSelect, TextTextarea } from '@/components/ui/FormFields';
import {
  BLOOD_GROUP_OPTIONS,
  EMPTY_PATIENT_FORM,
  GENDER_OPTIONS,
  type Patient,
  type PatientFormValues,
} from '@/types/patient';
import {
  patientToFormValues,
  validatePatientForm,
  type PatientFormErrors,
} from '@/utils/patientValidation';

interface PatientFormProps {
  initialPatient?: Patient | null;
  submitting?: boolean;
  submitLabel?: string;
  onSubmit: (values: PatientFormValues) => Promise<void> | void;
  onCancel: () => void;
}

export default function PatientForm({
  initialPatient,
  submitting = false,
  submitLabel = 'Save patient',
  onSubmit,
  onCancel,
}: PatientFormProps) {
  const [values, setValues] = useState<PatientFormValues>(EMPTY_PATIENT_FORM);
  const [errors, setErrors] = useState<PatientFormErrors>({});

  useEffect(() => {
    if (initialPatient) {
      setValues(patientToFormValues(initialPatient));
    } else {
      setValues(EMPTY_PATIENT_FORM);
    }
    setErrors({});
  }, [initialPatient]);

  function update<K extends keyof PatientFormValues>(
    key: K,
    value: PatientFormValues[K],
  ) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const nextErrors = validatePatientForm(values);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    await onSubmit(values);
  }

  return (
    <form className="space-y-6" onSubmit={handleSubmit} noValidate>
      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Basic information
        </h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextInput
            label="First name"
            name="first_name"
            required
            value={values.first_name}
            onChange={(e) => update('first_name', e.target.value)}
            error={errors.first_name}
            disabled={submitting}
          />
          <TextInput
            label="Last name"
            name="last_name"
            required
            value={values.last_name}
            onChange={(e) => update('last_name', e.target.value)}
            error={errors.last_name}
            disabled={submitting}
          />
          <TextInput
            label="Date of birth"
            name="date_of_birth"
            type="date"
            required
            value={values.date_of_birth}
            onChange={(e) => update('date_of_birth', e.target.value)}
            error={errors.date_of_birth}
            disabled={submitting}
          />
          <TextSelect
            label="Gender"
            name="gender"
            required
            value={values.gender}
            onChange={(e) =>
              update('gender', e.target.value as PatientFormValues['gender'])
            }
            error={errors.gender}
            disabled={submitting}
            placeholder="Select gender"
            options={GENDER_OPTIONS.map((g) => ({ value: g, label: g }))}
          />
          <TextSelect
            label="Blood group"
            name="blood_group"
            value={values.blood_group}
            onChange={(e) =>
              update(
                'blood_group',
                e.target.value as PatientFormValues['blood_group'],
              )
            }
            disabled={submitting}
            placeholder="Select blood group"
            options={BLOOD_GROUP_OPTIONS.map((g) => ({ value: g, label: g }))}
          />
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Contact
        </h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextInput
            label="Phone"
            name="phone"
            required
            value={values.phone}
            onChange={(e) => update('phone', e.target.value)}
            error={errors.phone}
            disabled={submitting}
          />
          <TextInput
            label="Email"
            name="email"
            type="email"
            value={values.email}
            onChange={(e) => update('email', e.target.value)}
            error={errors.email}
            disabled={submitting}
          />
          <div className="sm:col-span-2">
            <TextInput
              label="Address"
              name="address"
              value={values.address}
              onChange={(e) => update('address', e.target.value)}
              disabled={submitting}
            />
          </div>
          <TextInput
            label="City"
            name="city"
            value={values.city}
            onChange={(e) => update('city', e.target.value)}
            disabled={submitting}
          />
          <TextInput
            label="State"
            name="state"
            value={values.state}
            onChange={(e) => update('state', e.target.value)}
            disabled={submitting}
          />
          <TextInput
            label="Country"
            name="country"
            value={values.country}
            onChange={(e) => update('country', e.target.value)}
            disabled={submitting}
          />
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Emergency contact
        </h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextInput
            label="Contact name"
            name="emergency_contact_name"
            value={values.emergency_contact_name}
            onChange={(e) => update('emergency_contact_name', e.target.value)}
            disabled={submitting}
          />
          <TextInput
            label="Contact phone"
            name="emergency_contact_phone"
            value={values.emergency_contact_phone}
            onChange={(e) => update('emergency_contact_phone', e.target.value)}
            error={errors.emergency_contact_phone}
            disabled={submitting}
          />
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Medical information
        </h3>
        <div className="grid gap-4">
          <TextTextarea
            label="Allergies"
            name="allergies"
            value={values.allergies}
            onChange={(e) => update('allergies', e.target.value)}
            disabled={submitting}
          />
          <TextTextarea
            label="Medical history"
            name="medical_history"
            value={values.medical_history}
            onChange={(e) => update('medical_history', e.target.value)}
            disabled={submitting}
          />
          <TextTextarea
            label="Current medications"
            name="current_medications"
            value={values.current_medications}
            onChange={(e) => update('current_medications', e.target.value)}
            disabled={submitting}
          />
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Insurance
        </h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextInput
            label="Insurance provider"
            name="insurance_provider"
            value={values.insurance_provider}
            onChange={(e) => update('insurance_provider', e.target.value)}
            disabled={submitting}
          />
          <TextInput
            label="Insurance number"
            name="insurance_number"
            value={values.insurance_number}
            onChange={(e) => update('insurance_number', e.target.value)}
            disabled={submitting}
          />
        </div>
      </section>

      <div className="flex flex-col-reverse gap-2 border-t border-[var(--border-color)] pt-4 sm:flex-row sm:justify-end">
        <button
          type="button"
          onClick={onCancel}
          disabled={submitting}
          className="rounded-lg border border-[var(--border-color)] px-4 py-2.5 text-sm font-medium text-[var(--text-secondary)] hover:bg-surface-100 dark:hover:bg-surface-800"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-70"
        >
          {submitting ? 'Saving…' : submitLabel}
        </button>
      </div>
    </form>
  );
}
