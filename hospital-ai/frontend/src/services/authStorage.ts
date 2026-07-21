const REMEMBER_KEY = 'hospital-ai-remember';

/**
 * Storage adapter for Supabase Auth.
 * "Remember me" → localStorage; otherwise sessionStorage.
 */
export function getAuthStorage(): Storage {
  if (typeof window === 'undefined') {
    return {
      getItem: () => null,
      setItem: () => undefined,
      removeItem: () => undefined,
      clear: () => undefined,
      key: () => null,
      length: 0,
    };
  }

  const remember = window.localStorage.getItem(REMEMBER_KEY);
  return remember === 'false' ? window.sessionStorage : window.localStorage;
}

export function setRememberPreference(remember: boolean): void {
  window.localStorage.setItem(REMEMBER_KEY, remember ? 'true' : 'false');
  if (!remember) {
    // Drop any prior persistent session when user opts out.
    window.localStorage.removeItem('sb-' + getProjectRef() + '-auth-token');
  }
}

function getProjectRef(): string {
  try {
    const url = import.meta.env.VITE_SUPABASE_URL || '';
    return new URL(url).hostname.split('.')[0] || 'hospital';
  } catch {
    return 'hospital';
  }
}
