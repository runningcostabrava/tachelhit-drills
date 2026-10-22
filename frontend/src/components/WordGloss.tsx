import type { Drill } from '../types';

// Word by word: each Tamazight word as the speaker wrote it, its Tifinagh, and the Catalan word(s)
// it answers to («—» when the Catalan says it another way). Stored on the drill (`glosses`, JSON),
// written once by the gloss pass; nothing is computed here.
export interface Gloss { shi: string; tif?: string | null; ca?: string | null }

export function parseGlosses(drill: Pick<Drill, 'glosses'> | null | undefined): Gloss[] {
  if (!drill?.glosses) return [];
  try { const g = JSON.parse(drill.glosses); return Array.isArray(g) ? g.filter((x) => x && typeof x.shi === 'string') : []; } catch { return []; }
}

export default function WordGloss({ drill, size = 'md', align = 'left' }: { drill: Pick<Drill, 'glosses'> | null | undefined; size?: 'sm' | 'md'; align?: 'left' | 'center' }) {
  return <GlossWords words={parseGlosses(drill)} size={size} align={align} />;
}

// The same strip from words already parsed — the grammar lessons carry theirs in the lesson itself.
export function GlossWords({ words: g, size = 'md', align = 'left' }: { words: Gloss[] | null | undefined; size?: 'sm' | 'md'; align?: 'left' | 'center' }) {
  if (!g || g.length === 0) return null;
  const fs = size === 'sm' ? 12 : 14;
  return (
    <div aria-label="Paraula per paraula" style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 8px', justifyContent: align === 'center' ? 'center' : 'flex-start', marginTop: 8 }}>
      {g.map((w, i) => (
        <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '4px 8px', borderRadius: 'var(--r-md)', background: 'var(--surface-2)', border: '1px solid var(--border)', minWidth: 34 }}>
          <span style={{ fontSize: fs + 1, fontWeight: 800, color: 'var(--text)', lineHeight: 1.2 }}>{w.shi}</span>
          {w.tif && <span style={{ fontSize: fs - 1, color: 'var(--text-muted)', fontFamily: 'var(--font-tifinagh)', lineHeight: 1.2 }}>{w.tif}</span>}
          <span style={{ fontSize: fs - 1, color: w.ca && w.ca !== '—' ? 'var(--brand-1)' : 'var(--text-muted)', fontWeight: 600, lineHeight: 1.2, marginTop: 1 }}>{w.ca || '—'}</span>
        </div>
      ))}
    </div>
  );
}
