import { toast } from 'sonner';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import { TextInput, TextSelect, TextTextarea } from '@/components/ui/FormFields';
import { useHospitalSettings } from '@/context/SettingsContext';
import { useTheme } from '@/context/ThemeContext';

export default function SettingsPage() {
  const { settings, updateSettings, resetSettings } = useHospitalSettings();
  const { theme, setTheme } = useTheme();

  return (
    <ErrorBoundary title="Settings error">
      <section className="mx-auto max-w-3xl space-y-6">
        <header>
          <h2 className="text-2xl font-semibold text-[var(--text-primary)]">
            Settings
          </h2>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Hospital branding, preferences, and future AI configuration.
          </p>
        </header>

        <div className="space-y-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-6">
          <TextInput
            label="Hospital name"
            value={settings.hospitalName}
            onChange={(e) => updateSettings({ hospitalName: e.target.value })}
          />
          <TextInput
            label="Hospital logo URL"
            value={settings.hospitalLogo}
            onChange={(e) => updateSettings({ hospitalLogo: e.target.value })}
            placeholder="https://…"
          />
          <TextSelect
            label="Theme"
            value={theme}
            options={[
              { value: 'light', label: 'Light' },
              { value: 'dark', label: 'Dark' },
            ]}
            onChange={(e) => {
              const next = e.target.value as 'light' | 'dark';
              setTheme(next);
              updateSettings({ theme: next });
            }}
          />
          <TextSelect
            label="Language"
            value={settings.language}
            options={[
              { value: 'en', label: 'English' },
              { value: 'hi', label: 'Hindi' },
              { value: 'es', label: 'Spanish' },
            ]}
            onChange={(e) => updateSettings({ language: e.target.value })}
          />
          <TextInput
            label="Timezone"
            value={settings.timezone}
            onChange={(e) => updateSettings({ timezone: e.target.value })}
          />
        </div>

        <div className="space-y-3 rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-6">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            Notification preferences
          </h3>
          <Toggle
            label="Email notifications"
            checked={settings.emailNotifications}
            onChange={(v) => updateSettings({ emailNotifications: v })}
          />
          <Toggle
            label="SMS notifications"
            checked={settings.smsNotifications}
            onChange={(v) => updateSettings({ smsNotifications: v })}
          />
          <Toggle
            label="Appointment reminders"
            checked={settings.appointmentReminders}
            onChange={(v) => updateSettings({ appointmentReminders: v })}
          />
        </div>

        <div className="space-y-3 rounded-xl border border-dashed border-[var(--border-color)] bg-[var(--bg-navbar)] p-6">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            AI configuration
          </h3>
          <p className="text-xs text-[var(--text-secondary)]">
            Placeholder for Week 2 agent settings — not implemented.
          </p>
          <TextTextarea
            label="Notes"
            rows={3}
            value={settings.aiConfigPlaceholder}
            onChange={(e) =>
              updateSettings({ aiConfigPlaceholder: e.target.value })
            }
          />
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => {
              toast.success('Settings saved locally');
            }}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white"
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => {
              resetSettings();
              toast.message('Settings reset');
            }}
            className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm"
          >
            Reset defaults
          </button>
        </div>
      </section>
    </ErrorBoundary>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-3 text-sm text-[var(--text-primary)]">
      <span>{label}</span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
    </label>
  );
}
