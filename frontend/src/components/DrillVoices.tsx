import { useEffect, useState } from 'react';
import { FaPlay } from 'react-icons/fa';
import { api, type Recording } from '../api';
import { getMediaUrl } from '../config';
import { varietyShort, varietyLabel } from '../varieties';

// Learner-facing: the different speakers' takes of a drill, each tagged with
// its variety, so you can hear how the phrase is said across varieties. Renders
// nothing unless the drill actually has extra takes beyond its primary audio.
export default function DrillVoices({ drillId }: { drillId: number }) {
  const [recs, setRecs] = useState<Recording[]>([]);

  useEffect(() => {
    let live = true;
    setRecs([]);
    api.drillRecordings(drillId).then((r) => { if (live) setRecs(r); }).catch(() => {});
    return () => { live = false; };
  }, [drillId]);

  const play = (url: string) => { const a = new Audio(getMediaUrl(url)); a.play().catch(() => {}); };

  if (recs.length === 0) return null;

  return (
    <div style={{ padding: '0 24px 16px', display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center', alignItems: 'center' }}>
      <span style={{ fontSize: '11px', fontWeight: 800, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Veus:</span>
      {recs.map((r) => (
        <button
          key={r.id}
          onClick={() => play(r.audio_url)}
          title={`${r.speaker || 'Anònim'}${r.variety ? ' · ' + varietyLabel(r.variety) : ''}`}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '5px 11px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--text)', cursor: 'pointer', fontSize: '12px', fontWeight: 700 }}
        >
          <FaPlay size={9} />
          {r.variety && <span style={{ fontWeight: 800, color: 'var(--saffron-strong)' }}>{varietyShort(r.variety)}</span>}
          <span style={{ color: 'var(--text-soft)' }}>{r.speaker || 'Anònim'}</span>
        </button>
      ))}
    </div>
  );
}
