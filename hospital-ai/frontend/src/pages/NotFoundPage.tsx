import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center px-4 text-center">
      <p className="text-6xl font-bold text-primary-600">404</p>
      <h1 className="mt-4 text-2xl font-semibold text-[var(--text-primary)]">
        Page not found
      </h1>
      <p className="mt-2 max-w-md text-sm text-[var(--text-secondary)]">
        The page you are looking for does not exist or has been moved.
      </p>
      <Link
        to="/"
        className="mt-6 rounded-lg bg-primary-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-primary-700"
      >
        Back to Dashboard
      </Link>
    </div>
  );
}
