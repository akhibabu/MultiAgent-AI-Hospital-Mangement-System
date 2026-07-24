import { memo } from 'react';
import { Link } from 'react-router-dom';

interface KpiCardProps {
  label: string;
  value: string | number;
  hint?: string;
  to?: string;
}

function KpiCard({ label, value, hint, to }: KpiCardProps) {
  const content = (
    <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4 transition hover:border-primary-500/40">
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">
        {value}
      </p>
      {hint ? (
        <p className="mt-1 text-xs text-[var(--text-secondary)]">{hint}</p>
      ) : null}
    </div>
  );
  if (to) {
    return (
      <Link to={to} className="block">
        {content}
      </Link>
    );
  }
  return content;
}

export default memo(KpiCard);
