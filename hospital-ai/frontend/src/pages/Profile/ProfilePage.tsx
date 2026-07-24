import { useState } from 'react';
import { toast } from 'sonner';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import { TextInput } from '@/components/ui/FormFields';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/services/supabaseClient';

export default function ProfilePage() {
  const { user, role } = useAuth();
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [saving, setSaving] = useState(false);

  async function handlePasswordChange(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }
    if (password !== confirm) {
      toast.error('Passwords do not match');
      return;
    }
    setSaving(true);
    try {
      const { error } = await supabase.auth.updateUser({ password });
      if (error) throw error;
      toast.success('Password updated');
      setPassword('');
      setConfirm('');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update password');
    } finally {
      setSaving(false);
    }
  }

  const initials =
    user?.full_name
      ?.split(' ')
      .map((p) => p[0])
      .join('')
      .slice(0, 2)
      .toUpperCase() || 'U';

  return (
    <ErrorBoundary title="Profile error">
      <section className="mx-auto max-w-3xl space-y-6">
        <header>
          <h2 className="text-2xl font-semibold text-[var(--text-primary)]">
            Profile
          </h2>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Your hospital account details and security settings.
          </p>
        </header>

        <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-6">
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary-600 text-lg font-semibold text-white">
              {initials}
            </div>
            <div>
              <p className="text-lg font-semibold text-[var(--text-primary)]">
                {user?.full_name || '—'}
              </p>
              <p className="text-sm text-[var(--text-secondary)]">{role}</p>
            </div>
          </div>

          <dl className="mt-6 grid gap-4 sm:grid-cols-2">
            <Field label="Email" value={user?.email} />
            <Field label="Role" value={role} />
            <Field
              label="Account created"
              value={
                user?.created_at
                  ? new Date(user.created_at).toLocaleString()
                  : '—'
              }
            />
            <Field
              label="Last profile update"
              value={
                user?.updated_at
                  ? new Date(user.updated_at).toLocaleString()
                  : '—'
              }
            />
            <Field
              label="Last login"
              value="Tracked by Supabase Auth session"
            />
            <Field label="Profile picture" value="Initials avatar (default)" />
          </dl>
        </div>

        <form
          onSubmit={handlePasswordChange}
          className="space-y-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-6"
        >
          <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            Change password
          </h3>
          <TextInput
            label="New password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
          />
          <TextInput
            label="Confirm password"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password"
          />
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {saving ? 'Updating…' : 'Update password'}
          </button>
        </form>
      </section>
    </ErrorBoundary>
  );
}

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <dt className="text-xs text-[var(--text-secondary)]">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium text-[var(--text-primary)]">
        {value || '—'}
      </dd>
    </div>
  );
}
