interface LoadingProps {
  message?: string;
  fullScreen?: boolean;
}

export default function Loading({
  message = 'Loading…',
  fullScreen = false,
}: LoadingProps) {
  return (
    <div
      className={
        fullScreen
          ? 'flex min-h-screen items-center justify-center bg-[var(--bg-app)]'
          : 'flex items-center justify-center py-16'
      }
      role="status"
      aria-live="polite"
    >
      <div className="flex flex-col items-center gap-3">
        <div
          className="h-10 w-10 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600"
          aria-hidden="true"
        />
        <p className="text-sm text-[var(--text-secondary)]">{message}</p>
      </div>
    </div>
  );
}
