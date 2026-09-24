import type { ReactNode } from 'react';
import Loading from '@/components/ui/Loading';

export function ValidationQueryGate<T>({ query, loadingLabel, children }: { query: { isLoading?: boolean; isError?: boolean; data?: T }; loadingLabel: string; children: (data: T) => ReactNode }) {
  if (query.isLoading) return <Loading message={loadingLabel} />;
  if (query.isError || !query.data) return <p className="text-sm text-[var(--text-secondary)]">Validation data is unavailable. Run the benchmark first or check the backend.</p>;
  return <>{children(query.data)}</>;
}
