import { type FormEvent, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { isAxiosError } from 'axios';
import { useAuth } from '@/hooks/useAuth';
import { APP_NAME } from '@/utils/constants';

interface FormErrors {
  email?: string;
  password?: string;
  form?: string;
}

function validate(email: string, password: string): FormErrors {
  const errors: FormErrors = {};
  if (!email.trim()) {
    errors.email = 'Email is required';
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
    errors.email = 'Enter a valid email address';
  }
  if (!password) {
    errors.password = 'Password is required';
  } else if (password.length < 6) {
    errors.password = 'Password must be at least 6 characters';
  }
  return errors;
}

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const from =
    (location.state as { from?: { pathname?: string } } | null)?.from
      ?.pathname || '/dashboard';

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors = validate(email, password);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setIsSubmitting(true);
    setErrors({});

    try {
      await login({ email, password, rememberMe });
      navigate(from.startsWith('/login') ? '/dashboard' : from, {
        replace: true,
      });
    } catch (error) {
      let message = 'Unable to sign in. Please try again.';
      if (isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        if (typeof detail === 'string') message = detail;
        else if (!error.response) {
          message =
            'Cannot reach the API. Ensure the backend is running on port 8000.';
        }
      } else if (error instanceof Error && error.message) {
        message = error.message;
      }
      setErrors({ form: message });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[var(--bg-app)] px-4">
      <div
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{
          background:
            'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(37, 99, 235, 0.25), transparent), radial-gradient(ellipse 60% 40% at 100% 100%, rgba(14, 165, 233, 0.12), transparent)',
        }}
      />

      <div className="relative w-full max-w-md rounded-2xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-8 shadow-lg shadow-slate-900/5">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary-600 text-lg font-bold text-white">
            HA
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            Sign in to {APP_NAME}
          </h1>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">
            Secure staff access powered by Supabase Auth
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit} noValidate>
          {errors.form && (
            <div
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300"
              role="alert"
            >
              {errors.form}
            </div>
          )}

          <div>
            <label
              htmlFor="email"
              className="mb-1.5 block text-sm font-medium text-[var(--text-primary)]"
            >
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isSubmitting}
              placeholder="staff@hospital.local"
              className={`w-full rounded-lg border bg-transparent px-3 py-2.5 text-sm text-[var(--text-primary)] outline-none transition focus:ring-2 focus:ring-primary-500/30 ${
                errors.email
                  ? 'border-red-400 focus:border-red-500'
                  : 'border-[var(--border-color)] focus:border-primary-500'
              }`}
            />
            {errors.email && (
              <p className="mt-1 text-xs text-red-600">{errors.email}</p>
            )}
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
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isSubmitting}
              placeholder="••••••••"
              className={`w-full rounded-lg border bg-transparent px-3 py-2.5 text-sm text-[var(--text-primary)] outline-none transition focus:ring-2 focus:ring-primary-500/30 ${
                errors.password
                  ? 'border-red-400 focus:border-red-500'
                  : 'border-[var(--border-color)] focus:border-primary-500'
              }`}
            />
            {errors.password && (
              <p className="mt-1 text-xs text-red-600">{errors.password}</p>
            )}
          </div>

          <div className="flex items-center justify-between gap-3 pt-1">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-[var(--text-secondary)]">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                disabled={isSubmitting}
                className="h-4 w-4 rounded border-[var(--border-color)] text-primary-600 focus:ring-primary-500"
              />
              Remember me
            </label>
            <button
              type="button"
              className="text-sm font-medium text-primary-600 hover:underline disabled:opacity-50"
              disabled={isSubmitting}
              onClick={() => {
                // UI only for this step — password reset comes later
              }}
            >
              Forgot password?
            </button>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isSubmitting ? (
              <>
                <span
                  className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
                  aria-hidden
                />
                Signing in…
              </>
            ) : (
              'Sign in'
            )}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-[var(--text-secondary)]">
          Having trouble? Contact your hospital administrator.
        </p>
        <p className="mt-2 text-center text-xs text-[var(--text-secondary)]">
          <Link to="/dashboard" className="text-primary-600 hover:underline">
            Back to app
          </Link>{' '}
          (requires sign-in)
        </p>
      </div>
    </div>
  );
}
