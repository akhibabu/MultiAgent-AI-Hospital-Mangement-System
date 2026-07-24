import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import Loading from '@/components/ui/Loading';
import {
  useAddAvailability,
  useDeleteAvailability,
  useDoctorAvailability,
  useDoctors,
} from '@/hooks/useDoctors';
import {
  DAYS_OF_WEEK,
  type AvailabilityFormValues,
} from '@/types/doctor';

export default function AvailabilityPage() {
  const [params, setParams] = useSearchParams();
  const [doctorId, setDoctorId] = useState(params.get('doctorId') || '');
  const { data: doctorsData, isLoading: doctorsLoading } = useDoctors({
    page: 1,
    page_size: 100,
    sort_by: 'last_name',
    sort_order: 'asc',
  });
  const { data: slots = [], isLoading: slotsLoading } =
    useDoctorAvailability(doctorId || undefined);
  const addSlot = useAddAvailability(doctorId);
  const removeSlot = useDeleteAvailability(doctorId);

  const [form, setForm] = useState<AvailabilityFormValues>({
    day_of_week: 0,
    start_time: '09:00',
    end_time: '17:00',
    slot_duration: '30',
    is_available: true,
  });

  useEffect(() => {
    const fromUrl = params.get('doctorId') || '';
    if (fromUrl && fromUrl !== doctorId) setDoctorId(fromUrl);
  }, [params, doctorId]);

  useEffect(() => {
    if (doctorId) setParams({ doctorId });
  }, [doctorId, setParams]);

  const selectedDoctor = useMemo(
    () => doctorsData?.items.find((d) => d.id === doctorId),
    [doctorsData, doctorId],
  );

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!doctorId) return;
    await addSlot.mutateAsync(form);
  }

  const byDay = DAYS_OF_WEEK.map((day, index) => ({
    day,
    index,
    slots: slots.filter((s) => s.day_of_week === index),
  }));

  return (
    <ErrorBoundary title="Availability module error">
      <section className="space-y-6">
        <header>
          <h2 className="text-2xl font-semibold text-[var(--text-primary)]">
            Doctor Availability
          </h2>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Weekly schedules for the future Appointment Scheduling Agent.
          </p>
        </header>

        <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4">
          <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
            Select doctor
          </label>
          {doctorsLoading ? (
            <Loading message="Loading doctors…" />
          ) : (
            <select
              value={doctorId}
              onChange={(e) => setDoctorId(e.target.value)}
              className="w-full max-w-lg rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm"
            >
              <option value="">Choose a doctor</option>
              {(doctorsData?.items ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  Dr. {d.first_name} {d.last_name} ({d.doctor_number})
                </option>
              ))}
            </select>
          )}
          {selectedDoctor ? (
            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              {selectedDoctor.specialization}
              {selectedDoctor.department
                ? ` · ${selectedDoctor.department.name}`
                : ''}{' '}
              ·{' '}
              <Link
                to={`/doctors/${selectedDoctor.id}`}
                className="text-primary-600 hover:underline"
              >
                Open profile
              </Link>
            </p>
          ) : null}
        </div>

        {!doctorId ? (
          <div className="rounded-xl border border-dashed border-[var(--border-color)] p-10 text-center text-sm text-[var(--text-secondary)]">
            Select a doctor to view and manage availability slots.
          </div>
        ) : (
          <>
            <form
              onSubmit={handleSubmit}
              className="grid gap-3 rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4 sm:grid-cols-6"
            >
              <select
                value={form.day_of_week}
                onChange={(e) =>
                  setForm((p) => ({
                    ...p,
                    day_of_week: Number(e.target.value),
                  }))
                }
                className="rounded-lg border border-[var(--border-color)] bg-transparent px-2 py-2 text-sm sm:col-span-1"
              >
                {DAYS_OF_WEEK.map((d, i) => (
                  <option key={d} value={i}>
                    {d}
                  </option>
                ))}
              </select>
              <input
                type="time"
                value={form.start_time}
                onChange={(e) =>
                  setForm((p) => ({ ...p, start_time: e.target.value }))
                }
                className="rounded-lg border border-[var(--border-color)] bg-transparent px-2 py-2 text-sm"
              />
              <input
                type="time"
                value={form.end_time}
                onChange={(e) =>
                  setForm((p) => ({ ...p, end_time: e.target.value }))
                }
                className="rounded-lg border border-[var(--border-color)] bg-transparent px-2 py-2 text-sm"
              />
              <input
                type="number"
                min={5}
                value={form.slot_duration}
                onChange={(e) =>
                  setForm((p) => ({ ...p, slot_duration: e.target.value }))
                }
                className="rounded-lg border border-[var(--border-color)] bg-transparent px-2 py-2 text-sm"
                placeholder="Slot mins"
              />
              <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                <input
                  type="checkbox"
                  checked={form.is_available}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, is_available: e.target.checked }))
                  }
                />
                Available
              </label>
              <button
                type="submit"
                disabled={addSlot.isPending}
                className="rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white"
              >
                {addSlot.isPending ? 'Adding…' : 'Add slot'}
              </button>
            </form>

            {slotsLoading ? (
              <Loading message="Loading availability…" />
            ) : (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {byDay.map(({ day, slots: daySlots }) => (
                  <div
                    key={day}
                    className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4"
                  >
                    <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                      {day}
                    </h3>
                    {daySlots.length === 0 ? (
                      <p className="mt-2 text-xs text-[var(--text-secondary)]">
                        No slots
                      </p>
                    ) : (
                      <ul className="mt-2 space-y-2">
                        {daySlots.map((slot) => (
                          <li
                            key={slot.id}
                            className="flex items-center justify-between rounded-lg bg-surface-50 px-3 py-2 text-sm dark:bg-surface-900/40"
                          >
                            <span>
                              {slot.start_time.slice(0, 5)}–
                              {slot.end_time.slice(0, 5)} · {slot.slot_duration}
                              m
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
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </section>
    </ErrorBoundary>
  );
}
