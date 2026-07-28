/** Shared surface card used across AI Center agent pages. */

export default function Card({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-2xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-5 shadow-sm ${className}`}
    >
      {children}
    </section>
  );
}
