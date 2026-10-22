import { useRef, useState } from 'react';
import { FaVolumeUp } from 'react-icons/fa';
import { api } from '../api';
import { getMediaUrl } from '../config';
import type { Drill } from '../types';

// Word by word: each Tamazight word as the speaker wrote it, its Tifinagh, and the Catalan word(s)
// it answers to («—» when the Catalan says it another way). Stored on the drill (`glosses`, JSON),
// written once by the gloss pass; nothing is computed here.
//
// Press a word and you hear it. Not a synthetic voice and not a new sound file: forced alignment
// knows when each word is spoken inside the recordings we already have, so this seeks into one of
// them and stops at the end of the word. A word said by somebody with a name and a place comes
// first; the open corpus only fills the gaps, and says so.
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
  // Which word is sounding, and who said it, so the strip can show it without asking again.
  const [saying, setSaying] = useState<string | null>(null);
  const [heard, setHeard] = useState<Record<string, string | null>>({});
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const stopAt = useRef<number | null>(null);

  const say = async (word: string) => {
    if (saying) return;
    setSaying(word);
    try {
      const r = await api.wordAudio(word);
      const clip = r.clips[0];
      if (!clip) { setHeard((h) => ({ ...h, [word]: null })); return; }
      if (audioRef.current) audioRef.current.pause();
      const a = new Audio(getMediaUrl(clip.audio_url));
      audioRef.current = a;
      stopAt.current = clip.end + 0.08;          // a breath past the word, so it is not clipped short
      a.currentTime = Math.max(0, clip.start - 0.04);
      a.ontimeupdate = () => { if (stopAt.current != null && a.currentTime >= stopAt.current) { a.pause(); setSaying(null); } };
      a.onended = () => setSaying(null);
      a.onerror = () => setSaying(null);
      setHeard((h) => ({ ...h, [word]: clip.source === 'library' ? (clip.speaker || 'la nostra veu') : 'veu del corpus obert' }));
      await a.play().catch(() => setSaying(null));
    } catch {
      setHeard((h) => ({ ...h, [word]: null }));
      setSaying(null);
    }
  };

  if (!g || g.length === 0) return null;
  const fs = size === 'sm' ? 12 : 14;
  return (
    <div aria-label="Paraula per paraula" style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 8px', justifyContent: align === 'center' ? 'center' : 'flex-start', marginTop: 8 }}>
      {g.map((w, i) => {
        const who = heard[w.shi];
        return (
          <button
            key={i}
            onClick={() => say(w.shi)}
            title={who === null ? 'Encara no hi ha ningú que la digui' : who ? `Ho diu ${who}` : 'Escolta aquesta paraula'}
            aria-label={`Escolta ${w.shi}`}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '4px 8px',
              borderRadius: 'var(--r-md)', background: saying === w.shi ? 'var(--brand-gradient-soft)' : 'var(--surface-2)',
              border: '1px solid var(--border)', minWidth: 34, cursor: 'pointer', fontFamily: 'inherit',
            }}
          >
            <span style={{ fontSize: fs + 1, fontWeight: 800, color: 'var(--text)', lineHeight: 1.2, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              {w.shi}
              <FaVolumeUp size={fs - 4} style={{ color: saying === w.shi ? 'var(--brand-1)' : 'var(--text-muted)', opacity: who === null ? 0.3 : 1 }} />
            </span>
            {w.tif && <span style={{ fontSize: fs - 1, color: 'var(--text-muted)', fontFamily: 'var(--font-tifinagh)', lineHeight: 1.2 }}>{w.tif}</span>}
            <span style={{ fontSize: fs - 1, color: w.ca && w.ca !== '—' ? 'var(--brand-1)' : 'var(--text-muted)', fontWeight: 600, lineHeight: 1.2, marginTop: 1 }}>{w.ca || '—'}</span>
            {who && <span style={{ fontSize: fs - 3, color: 'var(--text-muted)', lineHeight: 1.2 }}>{who}</span>}
          </button>
        );
      })}
    </div>
  );
}
