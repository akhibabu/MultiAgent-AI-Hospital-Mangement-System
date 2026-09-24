export default function HumanReviewPanel() {
  return (
    <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm">
      <p className="font-medium text-amber-700">Human review required</p>
      <p className="mt-1 text-[var(--text-secondary)]">This task does not have a defensible automatic ground truth. Review factual correctness, completeness, clinical relevance, evidence grounding, safety, clarity, and unsupported claims before treating it as evaluated.</p>
    </div>
  );
}
