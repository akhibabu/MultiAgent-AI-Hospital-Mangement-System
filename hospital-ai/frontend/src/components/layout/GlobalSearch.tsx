import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useGlobalSearch } from '@/hooks/useHospital';
import type { GlobalSearchHit } from '@/types/hospital';

export default function GlobalSearch() {
  const [input, setInput] = useState('');
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const { data, isFetching } = useGlobalSearch(q);

  useEffect(() => {
    const t = window.setTimeout(() => setQ(input.trim()), 300);
    return () => window.clearTimeout(t);
  }, [input]);

  const groups = useMemo(() => {
    if (!data) return [] as { label: string; items: GlobalSearchHit[] }[];
    return [
      { label: 'Patients', items: data.patients },
      { label: 'Doctors', items: data.doctors },
      { label: 'Departments', items: data.departments },
      { label: 'Appointments', items: data.appointments },
      { label: 'Medical Records', items: data.medical_records },
    ].filter((g) => g.items.length);
  }, [data]);

  return (
    <div className="relative hidden min-w-0 flex-1 md:block md:max-w-md lg:max-w-lg">
      <input
        type="search"
        value={input}
        onChange={(e) => {
          setInput(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
        placeholder="Search patients, doctors, appointments…"
        className="w-full rounded-lg border border-[var(--border-color)] bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-500"
      />
      {open && q.length >= 2 ? (
        <div className="absolute left-0 right-0 top-full z-40 mt-1 max-h-96 overflow-auto rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] shadow-lg">
          {isFetching && !data ? (
            <p className="px-3 py-4 text-sm text-[var(--text-secondary)]">
              Searching…
            </p>
          ) : !groups.length ? (
            <p className="px-3 py-4 text-sm text-[var(--text-secondary)]">
              No results for “{q}”
            </p>
          ) : (
            groups.map((g) => (
              <div key={g.label} className="border-b border-[var(--border-color)] last:border-0">
                <p className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                  {g.label}
                </p>
                {g.items.map((hit) => (
                  <Link
                    key={`${hit.category}-${hit.id}`}
                    to={hit.link}
                    className="block px-3 py-2 hover:bg-surface-100 dark:hover:bg-surface-800"
                    onClick={() => setOpen(false)}
                  >
                    <p className="text-sm font-medium text-[var(--text-primary)]">
                      {hit.title}
                    </p>
                    {hit.subtitle ? (
                      <p className="text-xs text-[var(--text-secondary)]">
                        {hit.subtitle}
                      </p>
                    ) : null}
                  </Link>
                ))}
              </div>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}
