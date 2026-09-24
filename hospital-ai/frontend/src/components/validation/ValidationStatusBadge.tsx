interface Props { state: string; }

export default function ValidationStatusBadge({ state }: Props) {
  const styles: Record<string, string> = {
    VALIDATED: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600',
    PENDING_HUMAN_REVIEW: 'border-amber-500/30 bg-amber-500/10 text-amber-600',
    NOT_VALIDATABLE: 'border-slate-500/30 bg-slate-500/10 text-slate-500',
    PENDING_DATASET: 'border-blue-500/30 bg-blue-500/10 text-blue-600',
    IN_PROGRESS: 'border-violet-500/30 bg-violet-500/10 text-violet-600',
    ERROR: 'border-rose-500/30 bg-rose-500/10 text-rose-600',
  };
  const labels: Record<string, string> = {
    VALIDATED: 'Validated',
    PENDING_HUMAN_REVIEW: 'Human review',
    NOT_VALIDATABLE: 'Not validatable',
    PENDING_DATASET: 'Pending dataset',
    IN_PROGRESS: 'In progress',
    ERROR: 'Error',
  };
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${styles[state] ?? styles.NOT_VALIDATABLE}`}>{labels[state] ?? state.replace(/_/g, ' ')}</span>;
}
