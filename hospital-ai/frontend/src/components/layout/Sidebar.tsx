import { NavLink } from 'react-router-dom';
import { APP_NAME, NAV_ITEMS } from '@/utils/constants';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  return (
    <>
      {isOpen && (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          aria-label="Close sidebar overlay"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-[var(--bg-sidebar)] text-slate-100 transition-transform duration-200 lg:static lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-label="Main navigation"
      >
        <div className="flex h-16 items-center gap-3 border-b border-slate-700/60 px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-600 text-sm font-bold">
            HA
          </div>
          <div>
            <p className="text-sm font-semibold tracking-wide">{APP_NAME}</p>
            <p className="text-xs text-slate-400">Management System</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              onClick={onClose}
              className={({ isActive }) =>
                `block rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? 'bg-primary-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-700/60 px-4 py-4">
          <p className="text-xs text-slate-500">Week 1 · Architecture scaffold</p>
        </div>
      </aside>
    </>
  );
}
