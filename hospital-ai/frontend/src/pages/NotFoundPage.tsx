import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
      <p className="text-sm font-semibold text-primary-600">404</p>
      <h1 className="text-2xl font-semibold text-[var(--text-primary)]">
        Page not found
      </h1>
      <p className="max-w-md text-sm text-[var(--text-secondary)]">
        The page you requested does not exist or was moved.
      </p>
      <Link
        to="/dashboard"
        className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white"
      >
        Back to dashboard
      </Link>
    </div>
  );
}
