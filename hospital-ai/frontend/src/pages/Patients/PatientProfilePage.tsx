import { type ReactNode } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import PatientAppointmentHistory from '@/components/appointments/PatientAppointmentHistory';
import PatientMedicalHistory from '@/components/medical-records/PatientMedicalHistory';
import Loading from '@/components/ui/Loading';
import ErrorState from '@/components/ui/ErrorState';
import { usePatient } from '@/hooks/usePatients';
import type { Patient } from '@/types/patient';

function InfoCard({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
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
        {value?.trim() ? value : '—'}
      </dd>
    </div>
  );
}

function AiPlaceholder({
  label,
  description,
}: {
  label: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border border-dashed border-[var(--border-color)] bg-surface-50/60 px-4 py-3 dark:bg-surface-900/30">
      <p className="text-sm font-medium text-[var(--text-primary)]">{label}</p>
      <p className="mt-1 text-xs text-[var(--text-secondary)]">{description}</p>
      <p className="mt-2 font-mono text-[10px] uppercase tracking-wider text-[var(--text-secondary)]">
        Coming soon · AI agent extension
      </p>
    </div>
  );
}

function ProfileContent({ patient }: { patient: Patient }) {
  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-primary-600">
            {patient.patient_number}
          </p>
          <h2 className="mt-1 text-2xl font-semibold text-[var(--text-primary)]">
            {patient.first_name} {patient.last_name}
          </h2>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Registered {new Date(patient.created_at).toLocaleString()}
          </p>
        </div>
        <Link
          to="/patients"
          className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] hover:bg-surface-100 dark:hover:bg-surface-800"
        >
          Back to patients
        </Link>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <InfoCard title="Basic information">
          <dl className="grid gap-4 sm:grid-cols-2">
            <Field label="First name" value={patient.first_name} />
            <Field label="Last name" value={patient.last_name} />
            <Field
              label="Date of birth"
              value={patient.date_of_birth.slice(0, 10)}
            />
            <Field label="Gender" value={patient.gender} />
            <Field label="Blood group" value={patient.blood_group} />
          </dl>
        </InfoCard>

        <InfoCard title="Contact information">
          <dl className="grid gap-4 sm:grid-cols-2">
            <Field label="Phone" value={patient.phone} />
            <Field label="Email" value={patient.email} />
            <Field label="Address" value={patient.address} />
            <Field label="City" value={patient.city} />
            <Field label="State" value={patient.state} />
            <Field label="Country" value={patient.country} />
          </dl>
        </InfoCard>

        <InfoCard title="Emergency contact">
          <dl className="grid gap-4 sm:grid-cols-2">
            <Field label="Name" value={patient.emergency_contact_name} />
            <Field label="Phone" value={patient.emergency_contact_phone} />
          </dl>
        </InfoCard>

        <InfoCard title="Insurance information">
          <dl className="grid gap-4 sm:grid-cols-2">
            <Field label="Provider" value={patient.insurance_provider} />
            <Field label="Policy number" value={patient.insurance_number} />
          </dl>
        </InfoCard>

        <InfoCard title="Medical information">
          <dl className="grid gap-4">
            <Field label="Allergies" value={patient.allergies} />
            <Field label="Medical history" value={patient.medical_history} />
            <Field
              label="Current medications"
              value={patient.current_medications}
            />
          </dl>
        </InfoCard>

        <PatientAppointmentHistory patientId={patient.id} />

        <PatientMedicalHistory patientId={patient.id} />

        <InfoCard title="Future AI activity">
          <div className="space-y-3">
            <AiPlaceholder
              label="patient.ai_context"
              description={
                patient.ai_context
                  ? JSON.stringify(patient.ai_context)
                  : 'Structured context for clinical AI agents will appear here.'
              }
            />
            <AiPlaceholder
              label="patient.latest_diagnosis"
              description={
                patient.latest_diagnosis ||
                'Latest AI-assisted diagnosis summary (not implemented yet).'
              }
            />
            <AiPlaceholder
              label="patient.latest_report"
              description={
                patient.latest_report
                  ? JSON.stringify(patient.latest_report)
                  : 'Latest AI report payload placeholder.'
              }
            />
            <AiPlaceholder
              label="patient.prediction_history"
              description={
                patient.prediction_history
                  ? JSON.stringify(patient.prediction_history)
                  : 'Historical predictions from risk / triage agents.'
              }
            />
          </div>
        </InfoCard>
      </div>
    </div>
  );
}

export default function PatientProfilePage() {
  const { patientId } = useParams<{ patientId: string }>();
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = usePatient(patientId);

  if (isLoading) {
    return <Loading message="Loading patient profile…" />;
  }

  if (isError || !data) {
    return (
      <ErrorState
        title="Patient not found"
        message={
          error instanceof Error
            ? error.message
            : 'This patient record could not be loaded.'
        }
        onRetry={() => {
          if (isError) refetch();
          else navigate('/patients');
        }}
      />
    );
  }

  return (
    <ErrorBoundary title="Patient profile error">
      <ProfileContent patient={data} />
    </ErrorBoundary>
  );
}
