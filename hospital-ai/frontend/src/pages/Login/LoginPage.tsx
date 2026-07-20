import { Link } from 'react-router-dom';
import { APP_NAME } from '@/utils/constants';

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-app)] px-4">
      <div className="w-full max-w-md rounded-2xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-8 shadow-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary-600 text-lg font-bold text-white">
            HA
          </div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">
            Sign in to {APP_NAME}
          </h1>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">
            Authentication will be connected to Supabase Auth in a later step.
          </p>
        </div>

        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
          }}
        >
          <div>
            <label
              htmlFor="email"
              className="mb-1.5 block text-sm font-medium text-[var(--text-primary)]"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              placeholder="staff@hospital.local"
              disabled
              className="w-full rounded-lg border border-[var(--border-color)] bg-surface-50 px-3 py-2.5 text-sm text-[var(--text-secondary)] outline-none dark:bg-surface-900"
            />
          </div>
          <div>
            <label
              htmlFor="password"
              className="mb-1.5 block text-sm font-medium text-[var(--text-primary)]"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              placeholder="••••••••"
              disabled
              className="w-full rounded-lg border border-[var(--border-color)] bg-surface-50 px-3 py-2.5 text-sm text-[var(--text-secondary)] outline-none dark:bg-surface-900"
            />
          </div>
          <button
            type="submit"
            disabled
            className="w-full rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white opacity-60"
          >
            Sign in (coming soon)
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-[var(--text-secondary)]">
          Continue to the{' '}
          <Link to="/" className="font-medium text-primary-600 hover:underline">
            Dashboard scaffold
          </Link>
        </p>
      </div>
    </div>
  );
}
