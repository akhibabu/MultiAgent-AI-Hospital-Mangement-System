import { Link } from 'react-router-dom';

export default function UnauthorizedPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
      <p className="text-sm font-semibold text-amber-600">401</p>
      <h1 className="text-2xl font-semibold text-[var(--text-primary)]">
        Unauthorized
      </h1>
      <p className="max-w-md text-sm text-[var(--text-secondary)]">
        You need to sign in with a valid hospital account to access this area.
      </p>
      <Link
        to="/login"
        className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white"
      >
        Go to login
      </Link>
    </div>
  );
}
