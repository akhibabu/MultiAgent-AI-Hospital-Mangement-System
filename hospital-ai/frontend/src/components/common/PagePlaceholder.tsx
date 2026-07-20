interface PagePlaceholderProps {
  title: string;
  description: string;
  moduleName: string;
}

export default function PagePlaceholder({
  title,
  description,
  moduleName,
}: PagePlaceholderProps) {
  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
          {title}
        </h2>
        <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">
          {description}
        </p>
      </header>

      <div className="rounded-xl border border-dashed border-[var(--border-color)] bg-[var(--bg-navbar)] p-8">
        <p className="text-sm font-medium text-[var(--text-primary)]">
          {moduleName} module placeholder
        </p>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-[var(--text-secondary)]">
          This screen is part of the Week 1 architecture scaffold. Business
          logic, CRUD operations, and AI agent integrations will be added in
          subsequent steps.
        </p>
        <ul className="mt-4 list-inside list-disc space-y-1 text-sm text-[var(--text-secondary)]">
          <li>UI shell and navigation are ready</li>
          <li>API contracts will be defined next</li>
          <li>Data models and Supabase wiring come later</li>
        </ul>
      </div>
    </section>
  );
}
