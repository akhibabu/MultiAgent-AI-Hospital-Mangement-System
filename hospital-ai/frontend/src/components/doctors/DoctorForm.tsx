import { type ChangeEvent, type FormEvent, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { TextInput, TextSelect, TextTextarea } from '@/components/ui/FormFields';
import { useDepartments } from '@/hooks/useDoctors';
import { uploadDoctorPhoto } from '@/services/storageService';
import {
  AVAILABILITY_STATUSES,
  EMPTY_DOCTOR_FORM,
  GENDER_OPTIONS,
  type Doctor,
  type DoctorFormValues,
} from '@/types/doctor';
import {
  doctorToFormValues,
  validateDoctorForm,
  type DoctorFormErrors,
} from '@/utils/doctorValidation';

interface DoctorFormProps {
  initialDoctor?: Doctor | null;
  submitting?: boolean;
  submitLabel?: string;
  onSubmit: (values: DoctorFormValues) => Promise<void> | void;
  onCancel: () => void;
}

export default function DoctorForm({
  initialDoctor,
  submitting = false,
  submitLabel = 'Save doctor',
  onSubmit,
  onCancel,
}: DoctorFormProps) {
  const [values, setValues] = useState<DoctorFormValues>(EMPTY_DOCTOR_FORM);
  const [errors, setErrors] = useState<DoctorFormErrors>({});
  const [uploading, setUploading] = useState(false);
  const { data: deptData } = useDepartments();

  useEffect(() => {
    if (initialDoctor) setValues(doctorToFormValues(initialDoctor));
    else setValues(EMPTY_DOCTOR_FORM);
    setErrors({});
  }, [initialDoctor]);

  function update<K extends keyof DoctorFormValues>(
    key: K,
    value: DoctorFormValues[K],
  ) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  async function handlePhoto(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const url = await uploadDoctorPhoto(file);
      update('profile_photo_url', url);
      toast.success('Photo uploaded');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const next = validateDoctorForm(values);
    setErrors(next);
    if (Object.keys(next).length > 0) return;
    await onSubmit(values);
  }

  const busy = submitting || uploading;

  return (
    <form className="space-y-6" onSubmit={handleSubmit} noValidate>
      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Basic information
        </h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextInput
            label="First name"
            required
            value={values.first_name}
            onChange={(e) => update('first_name', e.target.value)}
            error={errors.first_name}
            disabled={busy}
          />
          <TextInput
            label="Last name"
            required
            value={values.last_name}
            onChange={(e) => update('last_name', e.target.value)}
            error={errors.last_name}
            disabled={busy}
          />
          <TextInput
            label="Email"
            type="email"
            required
            value={values.email}
            onChange={(e) => update('email', e.target.value)}
            error={errors.email}
            disabled={busy}
          />
          <TextInput
            label="Phone"
            required
            value={values.phone}
            onChange={(e) => update('phone', e.target.value)}
            error={errors.phone}
            disabled={busy}
          />
          <TextSelect
            label="Gender"
            required
            value={values.gender}
            onChange={(e) =>
              update('gender', e.target.value as DoctorFormValues['gender'])
            }
            error={errors.gender}
            disabled={busy}
            placeholder="Select gender"
            options={GENDER_OPTIONS.map((g) => ({ value: g, label: g }))}
          />
          <TextInput
            label="Date of birth"
            type="date"
            value={values.date_of_birth}
            onChange={(e) => update('date_of_birth', e.target.value)}
            error={errors.date_of_birth}
            disabled={busy}
          />
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Professional details
        </h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextSelect
            label="Department"
            value={values.department_id}
            onChange={(e) => update('department_id', e.target.value)}
            disabled={busy}
            placeholder="Select department"
            options={(deptData?.items ?? []).map((d) => ({
              value: d.id,
              label: d.name,
            }))}
          />
          <TextInput
            label="Specialization"
            required
            value={values.specialization}
            onChange={(e) => update('specialization', e.target.value)}
            error={errors.specialization}
            disabled={busy}
          />
          <TextInput
            label="Qualification"
            value={values.qualification}
            onChange={(e) => update('qualification', e.target.value)}
            disabled={busy}
          />
          <TextInput
            label="Experience (years)"
            type="number"
            min={0}
            value={values.experience_years}
            onChange={(e) => update('experience_years', e.target.value)}
            error={errors.experience_years}
            disabled={busy}
          />
          <TextInput
            label="License number"
            value={values.license_number}
            onChange={(e) => update('license_number', e.target.value)}
            disabled={busy}
          />
          <TextInput
            label="Consultation fee"
            type="number"
            min={0}
            step="0.01"
            value={values.consultation_fee}
            onChange={(e) => update('consultation_fee', e.target.value)}
            error={errors.consultation_fee}
            disabled={busy}
          />
          <TextSelect
            label="Availability status"
            value={values.availability_status}
            onChange={(e) =>
              update(
                'availability_status',
                e.target.value as DoctorFormValues['availability_status'],
              )
            }
            disabled={busy}
            options={AVAILABILITY_STATUSES.map((s) => ({
              value: s,
              label: s,
            }))}
          />
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Profile photo
        </h3>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          {values.profile_photo_url ? (
            <img
              src={values.profile_photo_url}
              alt="Doctor profile"
              className="h-20 w-20 rounded-full object-cover ring-2 ring-[var(--border-color)]"
            />
          ) : (
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-surface-100 text-xs text-[var(--text-secondary)] dark:bg-surface-800">
              No photo
            </div>
          )}
          <div>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              onChange={handlePhoto}
              disabled={busy}
              className="block w-full text-sm text-[var(--text-secondary)]"
            />
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              JPEG/PNG/WEBP/GIF · max 5MB · stored in Supabase Storage
            </p>
          </div>
        </div>
      </section>

      <TextTextarea
        label="Bio"
        value={values.bio}
        onChange={(e) => update('bio', e.target.value)}
        disabled={busy}
      />

      <div className="flex flex-col-reverse gap-2 border-t border-[var(--border-color)] pt-4 sm:flex-row sm:justify-end">
        <button
          type="button"
          onClick={onCancel}
          disabled={busy}
          className="rounded-lg border border-[var(--border-color)] px-4 py-2.5 text-sm"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={busy}
          className="rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-70"
        >
          {uploading ? 'Uploading…' : submitting ? 'Saving…' : submitLabel}
        </button>
      </div>
    </form>
  );
}
