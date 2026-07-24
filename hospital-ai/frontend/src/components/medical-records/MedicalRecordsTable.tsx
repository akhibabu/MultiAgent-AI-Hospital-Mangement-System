import { Link } from 'react-router-dom';
import RecordTypeChip from '@/components/medical-records/RecordTypeChip';
import type { MedicalRecord } from '@/types/medicalRecord';
import { formatFileSize } from '@/services/medicalStorageService';

interface MedicalRecordsTableProps {
  items: MedicalRecord[];
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  onSort: (column: string) => void;
  onEdit?: (record: MedicalRecord) => void;
  onDelete?: (record: MedicalRecord) => void;
}

function SortHeader({
  label,
  column,
  sortBy,
  sortOrder,
  onSort,
}: {
  label: string;
  column: string;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  onSort: (column: string) => void;
}) {
  const active = sortBy === column;
  return (
    <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
      <button
        type="button"
        onClick={() => onSort(column)}
        className="inline-flex items-center gap-1 hover:text-[var(--text-primary)]"
      >
        {label}
        {active ? (sortOrder === 'asc' ? ' ↑' : ' ↓') : ''}
      </button>
    </th>
  );
}

export default function MedicalRecordsTable({
  items,
  sortBy,
  sortOrder,
  onSort,
  onEdit,
  onDelete,
}: MedicalRecordsTableProps) {
  if (!items.length) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--border-color)] px-4 py-10 text-center text-sm text-[var(--text-secondary)]">
        No medical records match these filters.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)]">
      <table className="min-w-full text-sm">
        <thead className="border-b border-[var(--border-color)] bg-surface-50/80 dark:bg-surface-900/40">
          <tr>
            <SortHeader
              label="Title"
              column="title"
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={onSort}
            />
            <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              Patient
            </th>
            <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              Doctor
            </th>
            <SortHeader
              label="Type"
              column="record_type"
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={onSort}
            />
            <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              Files
            </th>
            <SortHeader
              label="Created"
              column="created_at"
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={onSort}
            />
            <th className="px-3 py-2 text-right text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((record) => {
            const totalBytes = record.documents.reduce(
              (sum, d) => sum + d.file_size,
              0,
            );
            return (
              <tr
                key={record.id}
                className="border-b border-[var(--border-color)] last:border-0"
              >
                <td className="px-3 py-3">
                  <Link
                    to={`/medical-records/${record.id}`}
                    className="font-medium text-primary-600 hover:underline"
                  >
                    {record.title}
                  </Link>
                  {record.diagnosis ? (
                    <p className="mt-0.5 line-clamp-1 text-xs text-[var(--text-secondary)]">
                      {record.diagnosis}
                    </p>
                  ) : null}
                </td>
                <td className="px-3 py-3 text-[var(--text-primary)]">
                  {record.patient
                    ? `${record.patient.first_name} ${record.patient.last_name}`
                    : '—'}
                </td>
                <td className="px-3 py-3 text-[var(--text-secondary)]">
                  {record.doctor
                    ? `Dr. ${record.doctor.first_name} ${record.doctor.last_name}`
                    : '—'}
                </td>
                <td className="px-3 py-3">
                  <RecordTypeChip type={record.record_type} />
                </td>
                <td className="px-3 py-3 text-[var(--text-secondary)]">
                  {record.documents.length}
                  {totalBytes
                    ? ` · ${formatFileSize(totalBytes)}`
                    : ''}
                </td>
                <td className="px-3 py-3 text-[var(--text-secondary)]">
                  {new Date(record.created_at).toLocaleDateString()}
                </td>
                <td className="px-3 py-3 text-right">
                  <div className="flex justify-end gap-2">
                    {onEdit ? (
                      <button
                        type="button"
                        onClick={() => onEdit(record)}
                        className="text-xs font-medium text-primary-600 hover:underline"
                      >
                        Edit
                      </button>
                    ) : null}
                    {onDelete ? (
                      <button
                        type="button"
                        onClick={() => onDelete(record)}
                        className="text-xs font-medium text-rose-600 hover:underline"
                      >
                        Delete
                      </button>
                    ) : null}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
