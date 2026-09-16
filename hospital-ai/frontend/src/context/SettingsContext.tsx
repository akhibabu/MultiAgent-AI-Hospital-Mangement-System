import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import {
  DEFAULT_HOSPITAL_SETTINGS,
  type HospitalSettings,
} from '@/types/hospital';

const STORAGE_KEY = 'hospital_ai_settings_v1';

interface SettingsContextValue {
  settings: HospitalSettings;
  updateSettings: (patch: Partial<HospitalSettings>) => void;
  resetSettings: () => void;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

function load(): HospitalSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_HOSPITAL_SETTINGS };
    const parsed = { ...DEFAULT_HOSPITAL_SETTINGS, ...JSON.parse(raw) } as HospitalSettings;
    const legacy = new Set([
      'Hospital GAAND',
      'Hospital GAAnd',
      'hospital GAAND',
      'Hospital AI',
      'hospital-ai',
      'Hospital AI API',
      'Eklavya Hospital',
      'eklavya hospital',
      'Eklavya hospital',
      'EKLAVYA HOSPITAL',
    ]);
    if (legacy.has(parsed.hospitalName)) {
      parsed.hospitalName = DEFAULT_HOSPITAL_SETTINGS.hospitalName;
    }
    return parsed;
  } catch {
    return { ...DEFAULT_HOSPITAL_SETTINGS };
  }
}

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<HospitalSettings>(load);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  }, [settings]);

  const value = useMemo(
    () => ({
      settings,
      updateSettings: (patch: Partial<HospitalSettings>) =>
        setSettings((prev) => ({ ...prev, ...patch })),
      resetSettings: () => setSettings({ ...DEFAULT_HOSPITAL_SETTINGS }),
    }),
    [settings],
  );

  return (
    <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
  );
}

export function useHospitalSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) {
    throw new Error('useHospitalSettings must be used within SettingsProvider');
  }
  return ctx;
}
