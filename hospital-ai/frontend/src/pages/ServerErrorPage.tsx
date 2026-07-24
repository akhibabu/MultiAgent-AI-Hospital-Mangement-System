import { Link } from 'react-router-dom';

export default function ServerErrorPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
      <p className="text-sm font-semibold text-rose-600">500</p>
      <h1 className="text-2xl font-semibold text-[var(--text-primary)]">
        Something went wrong
      </h1>
      <p className="max-w-md text-sm text-[var(--text-secondary)]">
        An unexpected server error occurred. Try again or return to the
        dashboard.
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm"
        >
          Reload
        </button>
        <Link
          to="/dashboard"
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white"
        >
          Dashboard
        </Link>
      </div>
    </div>
  );
}
