import { useTheme } from '@/context/ThemeContext';

interface NavbarProps {
  title: string;
  onMenuClick: () => void;
}

export default function Navbar({ title, onMenuClick }: NavbarProps) {
  const { theme, toggleTheme } = useTheme();

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

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={toggleTheme}
          className="rounded-lg border border-[var(--border-color)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition hover:bg-surface-100 dark:hover:bg-surface-800"
          aria-label="Toggle theme"
        >
          {theme === 'light' ? 'Dark' : 'Light'} mode
        </button>
        <div className="hidden items-center gap-2 rounded-full border border-[var(--border-color)] px-3 py-1.5 sm:flex">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          <span className="text-xs text-[var(--text-secondary)]">
            System ready
          </span>
        </div>
      </div>
    </header>
  );
}
