import { type FormEvent, useState, type ReactNode } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import AppointmentTimeline from '@/components/appointments/AppointmentTimeline';
import Loading from '@/components/ui/Loading';
import ErrorState from '@/components/ui/ErrorState';
import { useAppointments } from '@/hooks/useAppointments';
import {
  useAddAvailability,
  useDeleteAvailability,
  useDoctor,
  useDoctorAvailability,
} from '@/hooks/useDoctors';
import { DAYS_OF_WEEK, type AvailabilityFormValues } from '@/types/doctor';
import { toDateInputValue } from '@/utils/appointmentValidation';

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
        {title}
      </h3>
      {children}
    </section>
  );
}

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <dt className="text-xs text-[var(--text-secondary)]">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium text-[var(--text-primary)]">
        {value?.toString().trim() ? value : '—'}
      </dd>
    </div>
  );
}

function Placeholder({ label, hint }: { label: string; hint: string }) {
  return (
    <div className="rounded-lg border border-dashed border-[var(--border-color)] px-4 py-3">
      <p className="text-sm font-medium text-[var(--text-primary)]">{label}</p>
      <p className="mt-1 text-xs text-[var(--text-secondary)]">{hint}</p>
    </div>
  );
}

export default function DoctorProfilePage() {
  const { doctorId } = useParams<{ doctorId: string }>();
  const navigate = useNavigate();
  const { data: doctor, isLoading, isError, error, refetch } =
    useDoctor(doctorId);
  const { data: slots = [], isLoading: slotsLoading } =
    useDoctorAvailability(doctorId);
  const addSlot = useAddAvailability(doctorId || '');
  const removeSlot = useDeleteAvailability(doctorId || '');
  const today = toDateInputValue(new Date());
  const upcomingAppts = useAppointments({
    page: 1,
    page_size: 15,
    doctor_id: doctorId,
    date_from: today,
    status: 'Scheduled',
    sort_by: 'appointment_date',
    sort_order: 'asc',
  });

  const [slotForm, setSlotForm] = useState<AvailabilityFormValues>({
    day_of_week: 0,
    start_time: '09:00',
    end_time: '13:00',
    slot_duration: '30',
    is_available: true,
  });

  async function handleAddSlot(e: FormEvent) {
    e.preventDefault();
    if (!doctorId) return;
    await addSlot.mutateAsync(slotForm);
  }

  if (isLoading) return <Loading message="Loading doctor profile…" />;
  if (isError || !doctor) {
    return (
      <ErrorState
        title="Doctor not found"
        message={error instanceof Error ? error.message : 'Could not load doctor'}
        onRetry={() => (isError ? refetch() : navigate('/doctors'))}
      />
    );
  }

  return (
    <ErrorBoundary title="Doctor profile error">
      <div className="space-y-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-4">
            {doctor.profile_photo_url ? (
              <img
                src={doctor.profile_photo_url}
                alt=""
                className="h-16 w-16 rounded-full object-cover ring-2 ring-[var(--border-color)]"
              />
            ) : (
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary-600 text-lg font-semibold text-white">
                {doctor.first_name[0]}
                {doctor.last_name[0]}
              </div>
            )}
            <div>
              <p className="text-sm font-medium text-primary-600">
                {doctor.doctor_number}
              </p>
              <h2 className="text-2xl font-semibold text-[var(--text-primary)]">
                Dr. {doctor.first_name} {doctor.last_name}
              </h2>
              <p className="text-sm text-[var(--text-secondary)]">
                {doctor.specialization}
                {doctor.department ? ` · ${doctor.department.name}` : ''}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Link
              to={`/appointments/schedule?doctorId=${doctor.id}`}
              className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm"
            >
              Schedule
            </Link>
            <Link
              to={`/availability?doctorId=${doctor.id}`}
              className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm"
            >
              Manage availability
            </Link>
            <Link
              to="/doctors"
              className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm"
            >
              Back
            </Link>
          </div>
        </header>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Basic information">
            <dl className="grid gap-4 sm:grid-cols-2">
              <Field label="Email" value={doctor.email} />
              <Field label="Phone" value={doctor.phone} />
              <Field label="Gender" value={doctor.gender} />
              <Field
                label="Date of birth"
                value={doctor.date_of_birth?.slice(0, 10)}
              />
              <Field label="Status" value={doctor.availability_status} />
              <Field
                label="Consultation fee"
                value={String(doctor.consultation_fee)}
              />
            </dl>
          </Card>

          <Card title="Qualifications & experience">
            <dl className="grid gap-4 sm:grid-cols-2">
              <Field label="Qualification" value={doctor.qualification} />
              <Field label="License" value={doctor.license_number} />
              <Field
                label="Experience"
                value={`${doctor.experience_years} years`}
              />
              <Field label="Specialization" value={doctor.specialization} />
              <Field label="Department" value={doctor.department?.name} />
            </dl>
            {doctor.bio ? (
              <p className="mt-4 text-sm text-[var(--text-secondary)]">
                {doctor.bio}
              </p>
            ) : null}
          </Card>

          <Card title="Weekly availability">
            {slotsLoading ? (
              <Loading message="Loading slots…" />
            ) : slots.length === 0 ? (
              <p className="text-sm text-[var(--text-secondary)]">
                No availability slots yet.
              </p>
            ) : (
              <ul className="space-y-2">
                {slots.map((slot) => (
                  <li
                    key={slot.id}
                    className="flex items-center justify-between rounded-lg border border-[var(--border-color)] px-3 py-2 text-sm"
                  >
                    <span>
                      {DAYS_OF_WEEK[slot.day_of_week]} ·{' '}
                      {slot.start_time.slice(0, 5)}–{slot.end_time.slice(0, 5)}{' '}
                      ({slot.slot_duration} min)
                      {!slot.is_available ? ' · off' : ''}
                    </span>
                    <button
                      type="button"
                      className="text-xs text-red-600"
                      onClick={() => removeSlot.mutate(slot.id)}
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <form
              onSubmit={handleAddSlot}
              className="mt-4 grid gap-2 border-t border-[var(--border-color)] pt-4 sm:grid-cols-5"
            >
              <select
                value={slotForm.day_of_week}
                onChange={(e) =>
                  setSlotForm((p) => ({
                    ...p,
                    day_of_week: Number(e.target.value),
                  }))
                }
                className="rounded-lg border border-[var(--border-color)] bg-transparent px-2 py-2 text-sm"
              >
                {DAYS_OF_WEEK.map((d, i) => (
                  <option key={d} value={i}>
                    {d}
                  </option>
                ))}
              </select>
              <input
                type="time"
                value={slotForm.start_time}
                onChange={(e) =>
                  setSlotForm((p) => ({ ...p, start_time: e.target.value }))
                }
                className="rounded-lg border border-[var(--border-color)] bg-transparent px-2 py-2 text-sm"
              />
              <input
                type="time"
                value={slotForm.end_time}
                onChange={(e) =>
                  setSlotForm((p) => ({ ...p, end_time: e.target.value }))
                }
                className="rounded-lg border border-[var(--border-color)] bg-transparent px-2 py-2 text-sm"
              />
              <input
                type="number"
                min={5}
                value={slotForm.slot_duration}
                onChange={(e) =>
                  setSlotForm((p) => ({ ...p, slot_duration: e.target.value }))
                }
                className="rounded-lg border border-[var(--border-color)] bg-transparent px-2 py-2 text-sm"
                placeholder="mins"
              />
              <button
                type="submit"
                disabled={addSlot.isPending}
                className="rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white"
              >
                Add slot
              </button>
            </form>
          </Card>

          <Card title="Upcoming appointments">
            {upcomingAppts.isLoading ? (
              <Loading message="Loading appointments…" />
            ) : (
              <AppointmentTimeline
                items={upcomingAppts.data?.items ?? []}
                emptyLabel="No upcoming scheduled visits"
                showPatient
                showDoctor={false}
              />
            )}
            <Link
              to={`/appointments?doctorId=${doctor.id}`}
              className="mt-3 inline-block text-xs font-medium text-primary-600 hover:underline"
            >
              View all appointments
            </Link>
          </Card>

          <Card title="Future integrations">
            <div className="space-y-3">
              <Placeholder
                label="Assigned patients"
                hint="Patient assignments will appear here in a later module."
              />
              <Placeholder
                label="doctor.ai_summary"
                hint={
                  doctor.ai_summary ||
                  'AI-generated clinician summary (not implemented).'
                }
              />
              <Placeholder
                label="doctor.performance_metrics"
                hint="Future AI performance metrics payload."
              />
              <Placeholder
                label="doctor.predicted_workload"
                hint="Future workload prediction from Digital Twin / Resource Agent."
              />
              <Placeholder
                label="doctor.recommended_schedule"
                hint="Future recommended schedule from Scheduling Agent."
              />
              <Placeholder
                label="doctor.schedule_score"
                hint="Reserved for Scheduling Agent scoring — unused."
              />
            </div>
          </Card>
        </div>
      </div>
    </ErrorBoundary>
  );
}
