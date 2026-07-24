import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from '@/hooks/useHospital';
import { PRIORITY_COLORS } from '@/types/dashboard';

export default function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const { data } = useNotifications();
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();
  const unread = data?.unread_count ?? 0;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative rounded-lg border border-[var(--border-color)] px-2.5 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-surface-100 dark:hover:bg-surface-800"
        aria-label="Notifications"
      >
        Alerts
        {unread > 0 ? (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-600 px-1 text-[10px] text-white">
            {unread > 9 ? '9+' : unread}
          </span>
        ) : null}
      </button>
      {open ? (
        <div className="absolute right-0 top-full z-40 mt-1 w-80 max-w-[90vw] overflow-hidden rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] shadow-lg">
          <div className="flex items-center justify-between border-b border-[var(--border-color)] px-3 py-2">
            <p className="text-sm font-semibold text-[var(--text-primary)]">
              Notifications
            </p>
            <button
              type="button"
              onClick={() => markAll.mutate()}
              className="text-xs text-primary-600 hover:underline"
            >
              Mark all read
            </button>
          </div>
          <ul className="max-h-80 overflow-auto">
            {!(data?.items.length) ? (
              <li className="px-3 py-6 text-center text-sm text-[var(--text-secondary)]">
                No notifications
              </li>
            ) : (
              data.items.map((n) => (
                <li
                  key={n.id}
                  className={`border-b border-[var(--border-color)] px-3 py-2 last:border-0 ${
                    n.is_read ? 'opacity-70' : ''
                  }`}
                >
                  <button
                    type="button"
                    className="w-full text-left"
                    onClick={() => {
                      if (!n.is_read) markRead.mutate(n.id);
                    }}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium text-[var(--text-primary)]">
                        {n.title}
                      </p>
                      <span
                        className={`shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${PRIORITY_COLORS[n.priority]}`}
                      >
                        {n.priority}
                      </span>
                    </div>
                    <p className="mt-0.5 line-clamp-2 text-xs text-[var(--text-secondary)]">
                      {n.message}
                    </p>
                    <p className="mt-1 text-[10px] uppercase tracking-wide text-[var(--text-secondary)]">
                      {n.category} ·{' '}
                      {new Date(n.created_at).toLocaleString()}
                    </p>
                  </button>
                  {n.link ? (
                    <Link
                      to={n.link}
                      onClick={() => setOpen(false)}
                      className="mt-1 inline-block text-xs text-primary-600 hover:underline"
                    >
                      Open
                    </Link>
                  ) : null}
                </li>
              ))
            )}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
