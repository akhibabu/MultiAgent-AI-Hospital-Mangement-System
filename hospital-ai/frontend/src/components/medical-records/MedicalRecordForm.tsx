import { useEffect, useMemo, useState } from 'react';
import { TextInput, TextSelect, TextTextarea } from '@/components/ui/FormFields';
import { useAppointments } from '@/hooks/useAppointments';
import { useDoctors } from '@/hooks/useDoctors';
import { usePatients } from '@/hooks/usePatients';
import {
  EMPTY_MEDICAL_RECORD_FORM,
  MEDICAL_RECORD_TYPES,
  type MedicalRecord,
  type MedicalRecordFormValues,
} from '@/types/medicalRecord';

interface MedicalRecordFormProps {
  initial?: MedicalRecord | null;
  defaultPatientId?: string;
  submitting?: boolean;
  submitLabel?: string;
  onSubmit: (values: MedicalRecordFormValues) => Promise<void> | void;
  onCancel: () => void;
}

function toForm(initial?: MedicalRecord | null): MedicalRecordFormValues {
  if (!initial) return { ...EMPTY_MEDICAL_RECORD_FORM };
  return {
    patient_id: initial.patient_id,
    appointment_id: initial.appointment_id || '',
    doctor_id: initial.doctor_id || '',
    record_type: initial.record_type,
    title: initial.title,
    description: initial.description || '',
    diagnosis: initial.diagnosis || '',
    treatment: initial.treatment || '',
    notes: initial.notes || '',
  };
}

export default function MedicalRecordForm({
  initial,
  defaultPatientId,
  submitting,
  submitLabel = 'Save record',
  onSubmit,
  onCancel,
}: MedicalRecordFormProps) {
  const [values, setValues] = useState<MedicalRecordFormValues>(() => {
    const base = toForm(initial);
    if (!initial && defaultPatientId) base.patient_id = defaultPatientId;
    return base;
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const { data: patientsData } = usePatients({ page: 1, page_size: 100 });
  const { data: doctorsData } = useDoctors({ page: 1, page_size: 100 });
  const { data: appointmentsData } = useAppointments({
    page: 1,
    page_size: 50,
    patient_id: values.patient_id || undefined,
    sort_by: 'appointment_date',
    sort_order: 'desc',
  });

  useEffect(() => {
    if (!values.doctor_id && values.appointment_id) {
      const appt = appointmentsData?.items.find(
        (a) => a.id === values.appointment_id,
      );
      if (appt?.doctor_id) {
        setValues((p) => ({ ...p, doctor_id: appt.doctor_id }));
      }
    }
  }, [values.appointment_id, values.doctor_id, appointmentsData?.items]);

  const patientOptions = useMemo(
    () =>
      (patientsData?.items ?? []).map((p) => ({
        value: p.id,
        label: `${p.first_name} ${p.last_name} (${p.patient_number})`,
      })),
    [patientsData?.items],
  );

  function setField<K extends keyof MedicalRecordFormValues>(
    key: K,
    value: MedicalRecordFormValues[K],
  ) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const next: Record<string, string> = {};
    if (!values.patient_id) next.patient_id = 'Patient is required';
    if (!values.title.trim()) next.title = 'Title is required';
    if (!values.record_type) next.record_type = 'Record type is required';
    setErrors(next);
    if (Object.keys(next).length) return;
    await onSubmit(values);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <TextSelect
          label="Patient"
          name="patient_id"
          required
          value={values.patient_id}
          error={errors.patient_id}
          placeholder="Select patient"
          options={patientOptions}
          onChange={(e) => {
            setField('patient_id', e.target.value);
            setField('appointment_id', '');
          }}
        />
        <TextSelect
          label="Doctor"
          name="doctor_id"
          value={values.doctor_id}
          placeholder="Optional"
          options={(doctorsData?.items ?? []).map((d) => ({
            value: d.id,
            label: `Dr. ${d.first_name} ${d.last_name}`,
          }))}
          onChange={(e) => setField('doctor_id', e.target.value)}
        />
        <TextSelect
          label="Appointment"
          name="appointment_id"
          value={values.appointment_id}
          placeholder="Optional"
          options={(appointmentsData?.items ?? []).map((a) => ({
            value: a.id,
            label: `${a.appointment_number} · ${a.appointment_date}`,
          }))}
          onChange={(e) => setField('appointment_id', e.target.value)}
        />
        <TextSelect
          label="Record type"
          name="record_type"
          required
          value={values.record_type}
          error={errors.record_type}
          options={MEDICAL_RECORD_TYPES.map((t) => ({ value: t, label: t }))}
          onChange={(e) =>
            setField(
              'record_type',
              e.target.value as MedicalRecordFormValues['record_type'],
            )
          }
        />
      </div>

      <TextInput
        label="Title"
        name="title"
        required
        value={values.title}
        error={errors.title}
        onChange={(e) => setField('title', e.target.value)}
      />
      <TextInput
        label="Diagnosis"
        name="diagnosis"
        value={values.diagnosis}
        onChange={(e) => setField('diagnosis', e.target.value)}
      />
      <TextTextarea
        label="Treatment"
        name="treatment"
        rows={2}
        value={values.treatment}
        onChange={(e) => setField('treatment', e.target.value)}
      />
      <TextTextarea
        label="Description"
        name="description"
        rows={2}
        value={values.description}
        onChange={(e) => setField('description', e.target.value)}
      />
      <TextTextarea
        label="Notes"
        name="notes"
        rows={3}
        value={values.notes}
        onChange={(e) => setField('notes', e.target.value)}
      />

      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)]"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-60"
        >
          {submitting ? 'Saving…' : submitLabel}
        </button>
      </div>
    </form>
  );
}
