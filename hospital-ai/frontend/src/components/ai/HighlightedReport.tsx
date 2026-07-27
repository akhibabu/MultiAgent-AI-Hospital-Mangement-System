/**
 * Interactive highlighted medical report for NER Stage 4.
 */
import { useMemo, useState } from 'react';
import type { MedicalEntity } from '@/types/ner';
import { ENTITY_HIGHLIGHT } from '@/types/ner';

type Props = {
  text: string;
  entities: MedicalEntity[];
};

type Segment =
  | { kind: 'text'; value: string }
  | { kind: 'entity'; value: string; entity: MedicalEntity };

function buildSegments(text: string, entities: MedicalEntity[]): Segment[] {
  const usable = entities
    .filter(
      (e) =>
        e.char_start != null &&
        e.char_end != null &&
        e.char_start >= 0 &&
        e.char_end > e.char_start &&
        e.char_end <= text.length,
    )
    .sort((a, b) => (a.char_start! - b.char_start!) || (b.char_end! - a.char_end!));

  // Greedy non-overlapping spans
  const picked: MedicalEntity[] = [];
  let cursor = 0;
  for (const e of usable) {
    if (e.char_start! < cursor) continue;
    picked.push(e);
    cursor = e.char_end!;
  }

  if (!picked.length) {
    // Fallback: try to find values in text (case-insensitive, non-overlapping)
    const found: { start: number; end: number; entity: MedicalEntity }[] = [];
    const lower = text.toLowerCase();
    const byLen = [...entities].sort((a, b) => b.value.length - a.value.length);
    const used = new Array(text.length).fill(false);
    for (const e of byLen) {
      if (!e.value || e.value.length < 2) continue;
      const idx = lower.indexOf(e.value.toLowerCase());
      if (idx < 0) continue;
      if (used.slice(idx, idx + e.value.length).some(Boolean)) continue;
      for (let i = idx; i < idx + e.value.length; i++) used[i] = true;
      found.push({ start: idx, end: idx + e.value.length, entity: e });
    }
    found.sort((a, b) => a.start - b.start);
    if (!found.length) return [{ kind: 'text', value: text }];
    const segs: Segment[] = [];
    let pos = 0;
    for (const f of found) {
      if (f.start > pos) segs.push({ kind: 'text', value: text.slice(pos, f.start) });
      segs.push({
        kind: 'entity',
        value: text.slice(f.start, f.end),
        entity: f.entity,
      });
      pos = f.end;
    }
    if (pos < text.length) segs.push({ kind: 'text', value: text.slice(pos) });
    return segs;
  }

  const segs: Segment[] = [];
  let pos = 0;
  for (const e of picked) {
    if (e.char_start! > pos) {
      segs.push({ kind: 'text', value: text.slice(pos, e.char_start!) });
    }
    segs.push({
      kind: 'entity',
      value: text.slice(e.char_start!, e.char_end!),
      entity: e,
    });
    pos = e.char_end!;
  }
  if (pos < text.length) segs.push({ kind: 'text', value: text.slice(pos) });
  return segs;
}

export default function HighlightedReport({ text, entities }: Props) {
  const [selected, setSelected] = useState<MedicalEntity | null>(null);
  const segments = useMemo(() => buildSegments(text, entities), [text, entities]);

  if (!text) {
    return (
      <p className="text-sm text-[var(--text-secondary)]">
        No cleaned report text available.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-[var(--border-color)] bg-white p-5 shadow-sm dark:bg-black/20">
        <p className="whitespace-pre-wrap font-serif text-[15px] leading-7 text-[var(--text-primary)]">
          {segments.map((seg, i) => {
            if (seg.kind === 'text') {
              return <span key={`t-${i}`}>{seg.value}</span>;
            }
            const style =
              ENTITY_HIGHLIGHT[seg.entity.type] || {
                bg: 'bg-black/10',
                text: 'text-[var(--text-primary)]',
              };
            return (
              <button
                key={`e-${i}-${seg.entity.type}-${seg.entity.value}`}
                type="button"
                title={`${seg.entity.type} · ${(seg.entity.confidence * 100).toFixed(0)}%`}
                onClick={() => setSelected(seg.entity)}
                className={`mx-0.5 inline rounded px-0.5 font-medium underline decoration-dotted underline-offset-2 ${style.bg} ${style.text}`}
              >
                {seg.value}
              </button>
            );
          })}
        </p>
      </div>

      {selected ? (
        <div className="rounded-xl border border-primary-500/30 bg-primary-600/5 p-4 text-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-[var(--text-secondary)]">
                Selected entity
              </p>
              <p className="mt-1 font-semibold text-[var(--text-primary)]">
                {selected.value}
              </p>
            </div>
            <button
              type="button"
              className="text-xs text-[var(--text-secondary)]"
              onClick={() => setSelected(null)}
            >
              Close
            </button>
          </div>
          <dl className="mt-3 grid gap-2 sm:grid-cols-2">
            <div>
              <dt className="text-xs text-[var(--text-secondary)]">Type</dt>
              <dd className="font-medium">{selected.type}</dd>
            </div>
            <div>
              <dt className="text-xs text-[var(--text-secondary)]">Confidence</dt>
              <dd className="font-medium">
                {(selected.confidence * 100).toFixed(0)}%
              </dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-xs text-[var(--text-secondary)]">Source</dt>
              <dd className="font-medium">
                {selected.source_document || 'Uploaded report'}
                {selected.page ? ` · page ${selected.page}` : ''}
              </dd>
            </div>
            {selected.sentence ? (
              <div className="sm:col-span-2">
                <dt className="text-xs text-[var(--text-secondary)]">Sentence</dt>
                <dd className="mt-0.5 text-[var(--text-secondary)]">
                  {selected.sentence}
                </dd>
              </div>
            ) : null}
          </dl>
        </div>
      ) : (
        <p className="text-xs text-[var(--text-secondary)]">
          Click a highlighted term to view entity type, confidence, and source.
        </p>
      )}
    </div>
  );
}
