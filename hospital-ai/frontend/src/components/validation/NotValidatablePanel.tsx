export default function NotValidatablePanel({ reason }: { reason: string }) {
  return (
    <div className="rounded-xl border border-slate-500/30 bg-slate-500/5 p-4 text-sm">
      <p className="font-medium">Not currently validatable</p>
      <p className="mt-1 text-[var(--text-secondary)]">{reason}</p>
    </div>
  );
}
