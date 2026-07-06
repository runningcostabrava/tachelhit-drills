import { useEffect, useRef, useState } from 'react';
import { FaExclamationTriangle, FaSyncAlt } from 'react-icons/fa';
import { api, type SpacesHealth } from '../api';

const LABELS: Record<string, string> = {
  asr: 'transcripció', tts: 'veu', translation: 'traducció', ocr: 'OCR', image: 'imatges',
};

// Honest state for the free HF Spaces that power capture. Polls their health;
// when a needed one is asleep/down it says so and offers to pre-warm, instead
// of the user hitting Transcribe and getting a silent failure. Renders nothing
// while everything's up.
export default function ServiceStatusBanner({ services = ['asr', 'translation', 'ocr', 'tts'] }: { services?: string[] }) {
  const [health, setHealth] = useState<SpacesHealth | null>(null);
  const [waking, setWaking] = useState(false);
  const timer = useRef<number | null>(null);
  const alive = useRef(true);

  const schedule = (ms: number) => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(poll, ms);
  };
  const poll = async () => {
    try {
      const h = await api.spacesHealth();
      if (!alive.current) return;
      setHealth(h);
      const anyBusy = services.some((s) => h[s] && (h[s].state === 'waking' || h[s].state === 'down'));
      schedule(anyBusy ? 12000 : 45000); // watch closely while waking; relax when healthy
    } catch {
      schedule(30000);
    }
  };
  useEffect(() => {
    alive.current = true;
    poll();
    return () => { alive.current = false; if (timer.current) window.clearTimeout(timer.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // only alarm on genuinely busy/broken public Spaces — never on private ones
  // (which a public probe reports as private_or_missing) or unset ones.
  const relevant = services
    .map((s) => ({ key: s, st: health?.[s]?.state }))
    .filter((x) => x.st === 'waking' || x.st === 'down');
  if (!health || relevant.length === 0) return null;

  const wakingList = relevant.filter((x) => x.st === 'waking').map((x) => LABELS[x.key] || x.key);
  const downList = relevant.filter((x) => x.st === 'down').map((x) => LABELS[x.key] || x.key);

  const wake = async () => {
    setWaking(true);
    // wake ONLY the services this banner is about — waking all at once can hit
    // HuggingFace's free CPU quota.
    try { await api.wakeSpaces(relevant.map((r) => r.key)); } catch { /* fire and forget */ }
    setTimeout(() => { setWaking(false); poll(); }, 1500);
  };

  const msg = downList.length
    ? `Alguns serveis d'IA no responen (${[...downList, ...wakingList].join(', ')}). El pla gratuït de HuggingFace només manté uns quants Spaces actius alhora — potser cal pausar-ne d'altres. Prova de despertar-lo i torna-ho a intentar en un moment.`
    : `S'estan despertant els serveis d'IA (${wakingList.join(', ')})… pot trigar ~30 s.`;

  return (
    <div role="status" style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap', padding: '12px 16px', background: 'var(--amber-soft)', border: '1px solid var(--amber)', borderRadius: 'var(--r-md)', margin: '0 0 14px' }}>
      <span style={{ color: 'var(--amber-strong)', display: 'flex' }}><FaExclamationTriangle /></span>
      <span style={{ flex: 1, minWidth: '200px', fontSize: '13px', color: 'var(--amber-strong)', fontWeight: 600 }}>{msg}</span>
      <button onClick={wake} disabled={waking} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '7px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--amber)', background: 'var(--surface)', color: 'var(--amber-strong)', fontWeight: 700, fontSize: '13px', cursor: waking ? 'wait' : 'pointer' }}>
        <FaSyncAlt /> {waking ? 'Despertant…' : "Desperta'ls"}
      </button>
    </div>
  );
}
