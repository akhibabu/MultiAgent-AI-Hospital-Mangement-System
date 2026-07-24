import { Link } from 'react-router-dom';
import type { ActivityItem } from '@/types/hospital';

export default function ActivityList({
  title,
  items,
  empty = 'Nothing yet',
}: {
  title: string;
  items: ActivityItem[];
  empty?: string;
}) {
  return (
    <section className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-navbar)] p-4">
      <h3 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
        {title}
      </h3>
      {!items.length ? (
        <p className="text-sm text-[var(--text-secondary)]">{empty}</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={`${item.type}-${item.id}-${item.timestamp}`}>
              {item.link ? (
                <Link
                  to={item.link}
                  className="block rounded-lg px-2 py-1.5 hover:bg-surface-100 dark:hover:bg-surface-800"
                >
                  <ItemBody item={item} />
                </Link>
              ) : (
                <div className="px-2 py-1.5">
                  <ItemBody item={item} />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ItemBody({ item }: { item: ActivityItem }) {
  return (
    <>
      <p className="text-sm font-medium text-[var(--text-primary)]">
        {item.title}
      </p>
      <p className="text-xs text-[var(--text-secondary)]">
        {item.subtitle ? `${item.subtitle} · ` : ''}
        {item.timestamp
          ? new Date(item.timestamp).toLocaleString()
          : ''}
      </p>
    </>
  );
}
