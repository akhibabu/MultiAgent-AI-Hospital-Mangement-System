import { useEffect, useMemo, useState } from 'react';
import { TextInput, TextSelect, TextTextarea } from '@/components/ui/FormFields';
import { useAvailableSlots } from '@/hooks/useAppointments';
import { useDepartments, useDoctors } from '@/hooks/useDoctors';
import { usePatients } from '@/hooks/usePatients';
import {
  DAY_LABELS,
  EMPTY_APPOINTMENT_FORM,
  VISIT_TYPES,
  type Appointment,
  type AppointmentFormValues,
} from '@/types/appointment';
import { validateAppointmentForm } from '@/utils/appointmentValidation';

interface AppointmentFormProps {
  initial?: Appointment | null;
  defaultPatientId?: string;
  defaultDoctorId?: string;
  submitting?: boolean;
  submitLabel?: string;
  onSubmit: (values: AppointmentFormValues) => Promise<void> | void;
  onCancel: () => void;
}

function toFormValues(appt?: Appointment | null): AppointmentFormValues {
  if (!appt) return { ...EMPTY_APPOINTMENT_FORM };
  return {
    patient_id: appt.patient_id,
    doctor_id: appt.doctor_id,
    department_id: appt.department_id || '',
    appointment_date: appt.appointment_date,
    start_time: appt.start_time.slice(0, 5),
    end_time: appt.end_time.slice(0, 5),
    visit_type: appt.visit_type,
    reason_for_visit: appt.reason_for_visit || '',
    notes: appt.notes || '',
    status: appt.status,
  };
}

export default function AppointmentForm({
  initial,
  defaultPatientId,
  defaultDoctorId,
  submitting,
  submitLabel = 'Book appointment',
  onSubmit,
  onCancel,
}: AppointmentFormProps) {
  const [values, setValues] = useState<AppointmentFormValues>(() => {
    const base = toFormValues(initial);
    if (!initial) {
      if (defaultPatientId) base.patient_id = defaultPatientId;
      if (defaultDoctorId) base.doctor_id = defaultDoctorId;
    }
    return base;
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [slotLocked, setSlotLocked] = useState(true);

  const { data: patientsData } = usePatients({ page: 1, page_size: 100 });
  const { data: doctorsData } = useDoctors({ page: 1, page_size: 100 });
  const { data: deptData } = useDepartments();
  const { data: slotsData, isFetching: slotsLoading } = useAvailableSlots(
    values.doctor_id || undefined,
    values.appointment_date || undefined,
  );

  const doctors = doctorsData?.items ?? [];
  const patients = patientsData?.items ?? [];
  const departments = deptData?.items ?? [];

  useEffect(() => {
    if (!values.doctor_id) return;
    const doctor = doctors.find((d) => d.id === values.doctor_id);
    if (doctor?.department_id && !values.department_id) {
      setValues((prev) => ({
        ...prev,
        department_id: doctor.department_id || '',
      }));
    }
  }, [values.doctor_id, values.department_id, doctors]);

  const availableDayLabels = useMemo(() => {
    const days = slotsData?.available_days ?? [];
    if (!days.length) return 'No availability configured';
    return days.map((d) => DAY_LABELS[d] ?? `Day ${d}`).join(', ');
  }, [slotsData?.available_days]);

  function setField<K extends keyof AppointmentFormValues>(
    key: K,
    value: AppointmentFormValues[K],
  ) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  function applySlot(start: string, end: string) {
    setValues((prev) => ({
      ...prev,
      start_time: start.slice(0, 5),
      end_time: end.slice(0, 5),
    }));
    setSlotLocked(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const nextErrors = validateAppointmentForm(values);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    if (
      values.visit_type !== 'Emergency' &&
      slotsData &&
      slotsData.slots.length > 0 &&
      slotLocked
    ) {
      const match = slotsData.slots.some(
        (s) =>
          s.start_time.slice(0, 5) === values.start_time &&
          s.end_time.slice(0, 5) === values.end_time,
      );
      if (!match) {
        setErrors({
          start_time: 'Select an available slot or unlock custom times',
        });
        return;
      }
    }

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
          options={patients.map((p) => ({
            value: p.id,
            label: `${p.first_name} ${p.last_name} (${p.patient_number})`,
          }))}
          onChange={(e) => setField('patient_id', e.target.value)}
        />

        <TextSelect
          label="Doctor"
          name="doctor_id"
          required
          value={values.doctor_id}
          error={errors.doctor_id}
          placeholder="Select doctor"
          options={doctors.map((d) => ({
            value: d.id,
            label: `Dr. ${d.first_name} ${d.last_name} — ${d.specialization}`,
          }))}
          onChange={(e) => {
            setField('doctor_id', e.target.value);
            setField('start_time', '');
            setField('end_time', '');
          }}
        />

        <TextSelect
          label="Department"
          name="department_id"
          value={values.department_id}
          placeholder="Auto / none"
          options={departments.map((d) => ({
            value: d.id,
            label: d.name,
          }))}
          onChange={(e) => setField('department_id', e.target.value)}
        />

        <TextSelect
          label="Visit type"
          name="visit_type"
          required
          value={values.visit_type}
          error={errors.visit_type}
          options={VISIT_TYPES.map((t) => ({ value: t, label: t }))}
          onChange={(e) =>
            setField(
              'visit_type',
              e.target.value as AppointmentFormValues['visit_type'],
            )
          }
        />

        <TextInput
          label="Appointment date"
          name="appointment_date"
          type="date"
          required
          value={values.appointment_date}
          error={errors.appointment_date}
          onChange={(e) => {
            setField('appointment_date', e.target.value);
            setField('start_time', '');
            setField('end_time', '');
          }}
        />

        <div className="rounded-lg border border-dashed border-[var(--border-color)] px-3 py-2 text-xs text-[var(--text-secondary)]">
          <p className="font-medium text-[var(--text-primary)]">Available days</p>
          <p className="mt-1">
            {values.doctor_id ? availableDayLabels : 'Select a doctor'}
          </p>
        </div>
      </div>

      {values.doctor_id && values.appointment_date ? (
        <div className="rounded-xl border border-[var(--border-color)] p-3">
          <div className="mb-2 flex items-center justify-between gap-2">
            <p className="text-sm font-medium text-[var(--text-primary)]">
              Available slots
              {slotsLoading ? ' …' : ''}
            </p>
            <button
              type="button"
              className="text-xs text-primary-600 hover:underline"
              onClick={() => setSlotLocked((v) => !v)}
            >
              {slotLocked ? 'Enter custom time' : 'Use slot list'}
            </button>
          </div>
          {slotsData?.message && !(slotsData.slots.length > 0) ? (
            <p className="text-xs text-amber-700 dark:text-amber-300">
              {slotsData.message}
              {values.visit_type === 'Emergency'
                ? ' Emergency visits can still book outside hours.'
                : ''}
            </p>
          ) : null}
          <div className="mt-2 flex flex-wrap gap-2">
            {(slotsData?.slots ?? []).map((slot) => {
              const selected =
                values.start_time === slot.start_time.slice(0, 5) &&
                values.end_time === slot.end_time.slice(0, 5);
              return (
                <button
                  key={`${slot.start_time}-${slot.end_time}`}
                  type="button"
                  onClick={() => applySlot(slot.start_time, slot.end_time)}
                  className={`rounded-lg border px-2.5 py-1.5 text-xs font-medium ${
                    selected
                      ? 'border-primary-600 bg-primary-600 text-white'
                      : 'border-[var(--border-color)] text-[var(--text-primary)] hover:border-primary-500'
                  }`}
                >
                  {slot.start_time.slice(0, 5)} – {slot.end_time.slice(0, 5)}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <TextInput
          label="Start time"
          name="start_time"
          type="time"
          required
          value={values.start_time}
          error={errors.start_time}
          disabled={slotLocked && values.visit_type !== 'Emergency'}
          onChange={(e) => setField('start_time', e.target.value)}
        />
        <TextInput
          label="End time"
          name="end_time"
          type="time"
          required
          value={values.end_time}
          error={errors.end_time}
          disabled={slotLocked && values.visit_type !== 'Emergency'}
          onChange={(e) => setField('end_time', e.target.value)}
        />
      </div>

      <TextInput
        label="Reason for visit"
        name="reason_for_visit"
        value={values.reason_for_visit}
        onChange={(e) => setField('reason_for_visit', e.target.value)}
        placeholder="Brief reason"
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
          className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] hover:bg-surface-100 dark:hover:bg-surface-800"
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
