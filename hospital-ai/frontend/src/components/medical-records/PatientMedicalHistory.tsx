import { Link } from 'react-router-dom';
import RecordTypeChip from '@/components/medical-records/RecordTypeChip';
import Loading from '@/components/ui/Loading';
import { useMedicalRecords } from '@/hooks/useMedicalRecords';
import {
  IMAGING_TYPES,
  type MedicalRecord,
  type MedicalRecordType,
} from '@/types/medicalRecord';

export default function PatientMedicalHistory({
  patientId,
}: {
  patientId: string;
}) {
  const { data, isLoading } = useMedicalRecords({
    page: 1,
    page_size: 100,
    patient_id: patientId,
    sort_by: 'created_at',
    sort_order: 'desc',
  });

  const items = data?.items ?? [];
  const prescriptions = items.filter((r) => r.record_type === 'Prescription');
  const labs = items.filter((r) => r.record_type === 'Lab Report');
  const imaging = items.filter((r) =>
    IMAGING_TYPES.includes(r.record_type),
  );
  const reports = items.flatMap((r) =>
    r.documents.map((d) => ({ record: r, document: d })),
  );

  if (isLoading) return <Loading message="Loading medical history…" />;

  return (
    <div className="space-y-6 lg:col-span-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Medical history
        </h3>
        <Link
          to={`/medical-records?patientId=${patientId}`}
          className="text-xs font-medium text-primary-600 hover:underline"
        >
          Open medical records
        </Link>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="Medical records" count={items.length}>
          <RecordList items={items} empty="No medical records yet" />
        </Section>
        <Section title="Uploaded reports" count={reports.length}>
          {!reports.length ? (
            <p className="text-sm text-[var(--text-secondary)]">No files uploaded</p>
          ) : (
            <ul className="space-y-2">
              {reports.slice(0, 8).map(({ record, document }) => (
                <li key={document.id} className="text-sm">
                  <Link
                    to={`/medical-records/files/${document.id}`}
                    className="font-medium text-primary-600 hover:underline"
                  >
                    {document.file_name}
                  </Link>
                  <span className="text-[var(--text-secondary)]">
                    {' '}
                    · {record.title}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Section>
        <Section title="Prescriptions" count={prescriptions.length}>
          <RecordList items={prescriptions} empty="No prescriptions" />
        </Section>
        <Section title="Lab reports" count={labs.length}>
          <RecordList items={labs} empty="No lab reports" />
        </Section>
        <Section title="Imaging" count={imaging.length}>
          <RecordList items={imaging} empty="No imaging studies" />
        </Section>
        <Section title="Timeline" count={items.length}>
          <Timeline items={items} />
        </Section>
      </div>
    </div>
  );
}

function Section({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          {title}
        </h4>
        <span className="text-xs text-[var(--text-secondary)]">{count}</span>
      </div>
      {children}
    </section>
  );
}

function RecordList({
  items,
  empty,
}: {
  items: MedicalRecord[];
  empty: string;
}) {
  if (!items.length) {
    return <p className="text-sm text-[var(--text-secondary)]">{empty}</p>;
  }
  return (
    <ul className="space-y-2">
      {items.slice(0, 6).map((r) => (
        <li key={r.id} className="flex items-start justify-between gap-2">
          <Link
            to={`/medical-records/${r.id}`}
            className="text-sm font-medium text-primary-600 hover:underline"
          >
            {r.title}
          </Link>
          <RecordTypeChip type={r.record_type as MedicalRecordType} />
        </li>
      ))}
    </ul>
  );
}

function Timeline({ items }: { items: MedicalRecord[] }) {
  if (!items.length) {
    return (
      <p className="text-sm text-[var(--text-secondary)]">No timeline events</p>
    );
  }
  return (
    <ol className="relative space-y-0 border-l border-[var(--border-color)] pl-5">
      {items.map((r) => (
        <li key={r.id} className="relative pb-5 last:pb-0">
          <span className="absolute -left-[1.4rem] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-primary-500 bg-[var(--bg-navbar)]" />
          <Link
            to={`/medical-records/${r.id}`}
            className="text-sm font-medium text-primary-600 hover:underline"
          >
            {r.title}
          </Link>
          <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
            {new Date(r.created_at).toLocaleString()} · {r.record_type}
            {r.documents.length ? ` · ${r.documents.length} file(s)` : ''}
          </p>
        </li>
      ))}
    </ol>
  );
}
