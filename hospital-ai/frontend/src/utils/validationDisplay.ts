export function formatCount(value: unknown): string {
  const n = typeof value === 'number' ? value : Number(value ?? 0);
  return Number.isFinite(n) ? n.toLocaleString() : '0';
}

export function formatPercent(value: unknown): string {
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return 'n/a';
  const percent = Math.abs(n) <= 1 ? n * 100 : n;
  return `${percent.toFixed(1)}%`;
}

export function formatHeadlineValue(metric: string | null | undefined, value: unknown): string {
  if (value == null) return '—';
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return String(value);
  const normalized = String(metric ?? '').toLowerCase();
  if (normalized.includes('accuracy') || normalized.includes('precision') || normalized.includes('recall') || normalized.includes('f1') || normalized.includes('ndcg') || normalized.includes('rate') || normalized.includes('cer') || normalized.includes('wer')) {
    return formatPercent(n);
  }
  return n.toFixed(1);
}
