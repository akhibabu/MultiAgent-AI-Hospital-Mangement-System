/** Shared status/tone pill used across AI Center agent pages. */

export type BadgeTone = 'green' | 'blue' | 'amber' | 'red' | 'gray';

export default function Badge({
  tone,
  children,
}: {
  tone: BadgeTone;
  children: React.ReactNode;
}) {
  const map: Record<BadgeTone, string> = {
    green: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
    blue: 'bg-primary-600/15 text-primary-700 dark:text-primary-300',
    amber: 'bg-amber-500/15 text-amber-800 dark:text-amber-200',
    red: 'bg-red-500/15 text-red-700 dark:text-red-300',
    gray: 'bg-black/5 text-[var(--text-secondary)] dark:bg-white/10',
  };
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${map[tone]}`}
    >
      {children}
    </span>
  );
}
