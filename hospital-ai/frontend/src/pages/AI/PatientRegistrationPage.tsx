import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import Loading from '@/components/ui/Loading';
import { usePatients } from '@/hooks/usePatients';
import { useDoctors } from '@/hooks/useDoctors';
import { useAppointments } from '@/hooks/useAppointments';
import {
  useProcessingJobs,
  useRegisterForProcessing,
} from '@/hooks/useRegistration';
import { validateMedicalFile, formatFileSize } from '@/services/medicalStorageService';
import type { PatientRegistrationResult } from '@/types/registration';

export default function PatientRegistrationPage() {
  const [patientId, setPatientId] = useState('');
  const [doctorId, setDoctorId] = useState('');
  const [appointmentId, setAppointmentId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [lastResult, setLastResult] =
    useState<PatientRegistrationResult | null>(null);

  const patientsQuery = usePatients({
    page: 1,
    page_size: 100,
    sort_by: 'created_at',
    sort_order: 'desc',
  });
  const doctorsQuery = useDoctors({
    page: 1,
    page_size: 100,
    sort_by: 'created_at',
    sort_order: 'desc',
  });
  const appointmentsQuery = useAppointments({
    page: 1,
    page_size: 100,
    patient_id: patientId || undefined,
    doctor_id: doctorId || undefined,
    sort_by: 'appointment_date',
    sort_order: 'desc',
  });
  const jobsQuery = useProcessingJobs(patientId || undefined);
  const registerMutation = useRegisterForProcessing();

  const patients = patientsQuery.data?.items ?? [];
  const doctors = doctorsQuery.data?.items ?? [];
  const appointments = useMemo(() => {
    const items = appointmentsQuery.data?.items ?? [];
    return items.filter((a) => {
      if (patientId && a.patient_id !== patientId) return false;
      if (doctorId && a.doctor_id !== doctorId) return false;
      return true;
    });
  }, [appointmentsQuery.data?.items, patientId, doctorId]);

  useEffect(() => {
    setAppointmentId('');
  }, [patientId, doctorId]);

  function onFileChange(selected: File | null) {
    setFile(selected);
    if (!selected) {
      setFileError(null);
      return;
    }
    setFileError(validateMedicalFile(selected));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!patientId || !appointmentId || !doctorId || !file) {
      setFileError('Select patient, appointment, doctor, and a document');
      return;
    }
    const err = validateMedicalFile(file);
    if (err) {
      setFileError(err);
      return;
    }
    const result = await registerMutation.mutateAsync({
      patient_id: patientId,
      appointment_id: appointmentId,
      doctor_id: doctorId,
      file,
    });
    setLastResult(result);
    setFile(null);
    jobsQuery.refetch();
  }

  const selectedAppointment = appointments.find((a) => a.id === appointmentId);

  return (
    <ErrorBoundary title="Patient Registration error">
      <section className="space-y-6">
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-primary-600">
              AI Center · Intake Agent
            </p>
            <h2 className="text-2xl font-semibold text-[var(--text-primary)]">
              Patient Registration
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">
              Validate patient, appointment, and doctor, then register an
              uploaded document for AI processing. Does not run OCR — next stage
              is Medical History Extraction.
            </p>
          </div>
          <Link
            to="/ai"
            className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-sm"
          >
            Back to AI Center
          </Link>
        </header>

        <div className="grid gap-4 lg:grid-cols-2">
          <form
            onSubmit={handleSubmit}
            className="space-y-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4"
          >
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">
              Register Document
            </h3>

            <label className="block text-sm">
              <span className="mb-1 block text-[var(--text-secondary)]">
                Patient
              </span>
              <select
                required
                className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
              >
                <option value="">Select patient…</option>
                {patients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.first_name} {p.last_name}
                    {p.patient_number ? ` (${p.patient_number})` : ''}
                  </option>
                ))}
              </select>
            </label>

            <label className="block text-sm">
              <span className="mb-1 block text-[var(--text-secondary)]">
                Doctor
              </span>
              <select
                required
                className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2"
                value={doctorId}
                onChange={(e) => setDoctorId(e.target.value)}
              >
                <option value="">Select doctor…</option>
                {doctors.map((d) => (
                  <option key={d.id} value={d.id}>
                    Dr. {d.first_name} {d.last_name}
                    {d.specialization ? ` — ${d.specialization}` : ''}
                  </option>
                ))}
              </select>
            </label>

            <label className="block text-sm">
              <span className="mb-1 block text-[var(--text-secondary)]">
                Appointment
              </span>
              <select
                required
                disabled={!patientId || !doctorId}
                className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 disabled:opacity-50"
                value={appointmentId}
                onChange={(e) => setAppointmentId(e.target.value)}
              >
                <option value="">
                  {!patientId || !doctorId
                    ? 'Select patient and doctor first…'
                    : appointmentsQuery.isLoading
                      ? 'Loading appointments…'
                      : appointments.length
                        ? 'Select appointment…'
                        : 'No matching appointments'}
                </option>
                {appointments.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.appointment_number} · {a.appointment_date} · {a.status}
                  </option>
                ))}
              </select>
              {selectedAppointment ? (
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  Linked to patient & doctor on this appointment
                </p>
              ) : null}
            </label>

            <label className="block text-sm">
              <span className="mb-1 block text-[var(--text-secondary)]">
                Upload Document
              </span>
              <input
                type="file"
                accept=".pdf,.png,.jpeg,.jpg,.webp,application/pdf,image/*"
                className="w-full text-sm"
                onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
              />
              {file ? (
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  {file.name} · {formatFileSize(file.size)}
                </p>
              ) : null}
              {fileError ? (
                <p className="mt-1 text-xs text-red-600">{fileError}</p>
              ) : (
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  PDF, PNG, JPEG, JPG, WEBP · max 20MB
                </p>
              )}
            </label>

            <button
              type="submit"
              disabled={registerMutation.isPending || Boolean(fileError)}
              className="w-full rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {registerMutation.isPending
                ? 'Registering…'
                : 'Register for Processing'}
            </button>
          </form>

          <div className="space-y-4">
            <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4">
              <h3 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
                Latest Registration Result
              </h3>
              {!lastResult ? (
                <p className="text-sm text-[var(--text-secondary)]">
                  Submit the form to see Job ID, status, and current stage.
                </p>
              ) : (
                <dl className="space-y-2 text-sm">
                  <div>
                    <dt className="text-[var(--text-secondary)]">Job ID</dt>
                    <dd className="break-all font-mono text-xs text-[var(--text-primary)]">
                      {lastResult.job_id}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--text-secondary)]">Status</dt>
                    <dd className="font-medium text-[var(--text-primary)]">
                      {lastResult.status}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--text-secondary)]">
                      Current Stage
                    </dt>
                    <dd className="font-medium text-[var(--text-primary)]">
                      {lastResult.current_stage}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--text-secondary)]">Next Stage</dt>
                    <dd className="text-[var(--text-primary)]">
                      {lastResult.next_stage}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--text-secondary)]">
                      AI Context Status
                    </dt>
                    <dd className="text-[var(--text-primary)]">
                      {lastResult.patient_ai_context.status}
                    </dd>
                  </div>
                  {lastResult.patient_ai_context.current_summary ? (
                    <div>
                      <dt className="text-[var(--text-secondary)]">Summary</dt>
                      <dd className="text-[var(--text-primary)]">
                        {lastResult.patient_ai_context.current_summary}
                      </dd>
                    </div>
                  ) : null}
                </dl>
              )}
            </div>

            <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4">
              <h3 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
                Recent Jobs
                {patientId ? ' (selected patient)' : ''}
              </h3>
              {jobsQuery.isLoading ? (
                <Loading message="Loading jobs…" />
              ) : !jobsQuery.data?.length ? (
                <p className="text-sm text-[var(--text-secondary)]">
                  No processing jobs yet.
                </p>
              ) : (
                <ul className="max-h-64 space-y-2 overflow-auto text-sm">
                  {jobsQuery.data.map((job) => (
                    <li
                      key={job.id}
                      className="rounded-lg border border-[var(--border-color)] px-3 py-2"
                    >
                      <p className="font-medium text-[var(--text-primary)]">
                        {job.document_name}
                      </p>
                      <p className="font-mono text-[10px] text-[var(--text-secondary)]">
                        {job.id}
                      </p>
                      <p className="mt-1 text-xs text-[var(--text-secondary)]">
                        {job.status} · {job.current_stage}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </section>
    </ErrorBoundary>
  );
}
