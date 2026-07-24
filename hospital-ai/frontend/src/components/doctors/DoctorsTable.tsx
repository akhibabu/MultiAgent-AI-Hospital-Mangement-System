import { Link } from 'react-router-dom';
import type { Doctor } from '@/types/doctor';

interface DoctorsTableProps {
  doctors: Doctor[];
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  onSort: (column: string) => void;
  onEdit: (doctor: Doctor) => void;
  onDelete: (doctor: Doctor) => void;
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
  onSort: (c: string) => void;
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

export default function DoctorsTable({
  doctors,
  sortBy,
  sortOrder,
  onSort,
  onEdit,
  onDelete,
}: DoctorsTableProps) {
  if (doctors.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--border-color)] bg-[var(--bg-navbar)] px-6 py-16 text-center">
        <p className="text-sm font-medium text-[var(--text-primary)]">
          No doctors found
        </p>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Register a doctor or adjust your filters.
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
              <SortHeader label="Doctor #" column="doctor_number" sortBy={sortBy} sortOrder={sortOrder} onSort={onSort} />
              <SortHeader label="Name" column="last_name" sortBy={sortBy} sortOrder={sortOrder} onSort={onSort} />
              <SortHeader label="Specialization" column="specialization" sortBy={sortBy} sortOrder={sortOrder} onSort={onSort} />
              <th className="px-3 py-3 text-left text-xs font-semibold uppercase text-[var(--text-secondary)]">
                Department
              </th>
              <SortHeader label="Exp." column="experience_years" sortBy={sortBy} sortOrder={sortOrder} onSort={onSort} />
              <SortHeader label="Status" column="availability_status" sortBy={sortBy} sortOrder={sortOrder} onSort={onSort} />
              <th className="px-3 py-3 text-right text-xs font-semibold uppercase text-[var(--text-secondary)]">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-color)]">
            {doctors.map((doctor) => (
              <tr key={doctor.id} className="hover:bg-surface-50/80 dark:hover:bg-surface-900/30">
                <td className="whitespace-nowrap px-3 py-3 text-sm font-medium text-primary-600">
                  {doctor.doctor_number}
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-sm text-[var(--text-primary)]">
                  <div className="flex items-center gap-2">
                    {doctor.profile_photo_url ? (
                      <img
                        src={doctor.profile_photo_url}
                        alt=""
                        className="h-8 w-8 rounded-full object-cover"
                      />
                    ) : null}
                    Dr. {doctor.first_name} {doctor.last_name}
                  </div>
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-sm text-[var(--text-secondary)]">
                  {doctor.specialization}
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-sm text-[var(--text-secondary)]">
                  {doctor.department?.name || '—'}
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-sm text-[var(--text-secondary)]">
                  {doctor.experience_years} yrs
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-sm">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      doctor.availability_status === 'Available'
                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                        : doctor.availability_status === 'Busy'
                          ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'
                          : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
                    }`}
                  >
                    {doctor.availability_status}
                  </span>
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-right text-sm">
                  <div className="flex justify-end gap-2">
                    <Link
                      to={`/doctors/${doctor.id}`}
                      className="rounded-md px-2 py-1 text-xs font-medium text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-950/40"
                    >
                      View
                    </Link>
                    <button
                      type="button"
                      onClick={() => onEdit(doctor)}
                      className="rounded-md px-2 py-1 text-xs font-medium text-[var(--text-secondary)] hover:bg-surface-100 dark:hover:bg-surface-800"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => onDelete(doctor)}
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
