import { useState } from 'react';
import { useTheme } from '@/context/ThemeContext';
import { useAuth } from '@/hooks/useAuth';

interface NavbarProps {
  title: string;
  onMenuClick: () => void;
}

export default function Navbar({ title, onMenuClick }: NavbarProps) {
  const { theme, toggleTheme } = useTheme();
  const { user, role, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  async function handleLogout() {
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      setIsLoggingOut(false);
    }
  }

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-[var(--border-color)] bg-[var(--bg-navbar)] px-4 shadow-sm lg:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          className="rounded-lg p-2 text-[var(--text-secondary)] transition hover:bg-surface-100 lg:hidden dark:hover:bg-surface-800"
          aria-label="Open sidebar"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="h-5 w-5"
          >
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
        <h1 className="text-lg font-semibold text-[var(--text-primary)]">
          {title}
        </h1>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        <button
          type="button"
          onClick={toggleTheme}
          className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition hover:bg-surface-100 dark:hover:bg-surface-800"
          aria-label="Toggle theme"
        >
          {theme === 'light' ? 'Dark' : 'Light'} mode
        </button>

        {user && (
          <div className="hidden items-center gap-3 rounded-xl border border-[var(--border-color)] px-3 py-1.5 sm:flex">
            <div className="min-w-0 text-right">
              <p className="truncate text-sm font-medium text-[var(--text-primary)]">
                {user.full_name}
              </p>
              <p className="truncate text-xs text-[var(--text-secondary)]">
                {role}
              </p>
            </div>
            <div
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-600 text-xs font-semibold text-white"
              aria-hidden
            >
              {user.full_name
                .split(' ')
                .map((part) => part[0])
                .join('')
                .slice(0, 2)
                .toUpperCase()}
            </div>
          </div>
        )}

        <button
          type="button"
          onClick={handleLogout}
          disabled={isLoggingOut}
          className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-slate-700 disabled:opacity-60 dark:bg-slate-700 dark:hover:bg-slate-600"
        >
          {isLoggingOut ? 'Signing out…' : 'Logout'}
        </button>
      </div>
    </header>
  );
}
