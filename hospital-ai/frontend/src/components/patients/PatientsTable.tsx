import { Link } from 'react-router-dom';
import type { Patient } from '@/types/patient';

interface PatientsTableProps {
  patients: Patient[];
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  onSort: (column: string) => void;
  onEdit: (patient: Patient) => void;
  onDelete: (patient: Patient) => void;
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
    <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
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

export default function PatientsTable({
  patients,
  sortBy,
  sortOrder,
  onSort,
  onEdit,
  onDelete,
}: PatientsTableProps) {
  if (patients.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--border-color)] bg-[var(--bg-navbar)] px-6 py-16 text-center">
        <p className="text-sm font-medium text-[var(--text-primary)]">
          No patients found
        </p>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Register a patient or adjust your search filters.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)]">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-[var(--border-color)]">
          <thead className="bg-surface-50 dark:bg-surface-900/40">
            <tr>
              <SortHeader
                label="Patient #"
                column="patient_number"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={onSort}
              />
              <SortHeader
                label="Name"
                column="last_name"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={onSort}
              />
              <SortHeader
                label="DOB"
                column="date_of_birth"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={onSort}
              />
              <SortHeader
                label="Gender"
                column="gender"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={onSort}
              />
              <SortHeader
                label="Blood"
                column="blood_group"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={onSort}
              />
              <SortHeader
                label="Phone"
                column="phone"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={onSort}
              />
              <th className="px-3 py-3 text-right text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-color)]">
            {patients.map((patient) => (
              <tr
                key={patient.id}
                className="hover:bg-surface-50/80 dark:hover:bg-surface-900/30"
              >
                <td className="whitespace-nowrap px-3 py-3 text-sm font-medium text-primary-600">
                  {patient.patient_number}
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-sm text-[var(--text-primary)]">
                  {patient.first_name} {patient.last_name}
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-sm text-[var(--text-secondary)]">
                  {patient.date_of_birth.slice(0, 10)}
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-sm text-[var(--text-secondary)]">
                  {patient.gender}
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-sm text-[var(--text-secondary)]">
                  {patient.blood_group || '—'}
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-sm text-[var(--text-secondary)]">
                  {patient.phone}
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-right text-sm">
                  <div className="flex justify-end gap-2">
                    <Link
                      to={`/patients/${patient.id}`}
                      className="rounded-md px-2 py-1 text-xs font-medium text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-950/40"
                    >
                      View
                    </Link>
                    <button
                      type="button"
                      onClick={() => onEdit(patient)}
                      className="rounded-md px-2 py-1 text-xs font-medium text-[var(--text-secondary)] hover:bg-surface-100 dark:hover:bg-surface-800"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => onDelete(patient)}
                      className="rounded-md px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
