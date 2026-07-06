import { useEffect, useRef, useState } from 'react';
import { FaImage, FaStop, FaPlay } from 'react-icons/fa';
import { api, type ImageFillStatus } from '../api';
import { toast } from '../toast';

// Watch + control the background job that AI-illustrates drills without an
// image. Polls status every 5s while running; lets the user start/stop it.
export default function ImageFillPanel() {
  const [status, setStatus] = useState<ImageFillStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef<number | null>(null);

  const poll = async () => {
    try { setStatus(await api.imageFillStatus()); } catch { /* ignore transient */ }
  };

  useEffect(() => {
    poll();
    timer.current = window.setInterval(poll, 5000);
    return () => { if (timer.current) window.clearInterval(timer.current); };
  }, []);

  const start = async () => {
    setBusy(true);
    try {
      await api.imageFillStart(true);
      toast.success('Generació d\'imatges iniciada');
      await poll();
    } catch (e: any) {
      toast.error(e.message || 'No s\'ha pogut iniciar');
    } finally { setBusy(false); }
  };

  const stop = async () => {
    setBusy(true);
    try {
      await api.imageFillStop();
      toast.success('Aturant…');
      await poll();
    } catch (e: any) {
      toast.error(e.message || 'No s\'ha pogut aturar');
    } finally { setBusy(false); }
  };

  const running = status?.running;
  const total = status?.total ?? 0;
  const done = status?.done ?? 0;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', padding: '20px', marginBottom: '20px', boxShadow: 'var(--shadow-sm)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ display: 'inline-flex', width: 38, height: 38, borderRadius: 'var(--r-md)', background: 'var(--brand-gradient-soft)', color: 'var(--brand-1)', alignItems: 'center', justifyContent: 'center' }}><FaImage /></span>
          <div>
            <div style={{ fontWeight: 700, fontFamily: 'var(--font-display)', fontSize: '16px', color: 'var(--text)' }}>Imatges dels drills</div>
            <div style={{ fontSize: '12.5px', color: 'var(--text-soft)' }}>Genera il·lustracions (IA) per als drills concrets que no en tenen</div>
          </div>
        </div>
        {running ? (
          <button onClick={stop} disabled={busy} style={btn('var(--rose-soft)', 'var(--rose)', true)}><FaStop /> Atura</button>
        ) : (
          <button onClick={start} disabled={busy} style={btn('var(--brand-1)', '#fff')}><FaPlay /> Genera imatges</button>
        )}
      </div>

      {status && (running || done > 0) && (
        <div style={{ marginTop: '16px' }}>
          <div style={{ height: 10, background: 'var(--surface-2)', borderRadius: 'var(--r-pill)', overflow: 'hidden', border: '1px solid var(--border)' }}>
            <div style={{ width: `${pct}%`, height: '100%', background: 'var(--brand-gradient)', transition: 'width 0.4s ease' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', marginTop: '8px', fontSize: '12.5px', color: 'var(--text-soft)', flexWrap: 'wrap' }}>
            <span><strong style={{ color: 'var(--text)' }}>{done}</strong> / {total} fetes ({pct}%)</span>
            <span>{status.skipped} omeses · {status.failed} errors</span>
          </div>
          {running && status.current && (
            <div style={{ marginTop: '6px', fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              Ara: «{status.current}»
            </div>
          )}
          {!running && done > 0 && (
            <div style={{ marginTop: '6px', fontSize: '12px', color: 'var(--emerald)', fontWeight: 600 }}>
              Acabat · {done} imatges generades{status.skipped ? `, ${status.skipped} omeses (abstractes)` : ''}.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function btn(bg: string, color: string, outline = false): React.CSSProperties {
  return { display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 18px', borderRadius: 'var(--r-pill)', fontWeight: 700, fontSize: '14px', cursor: 'pointer', background: bg, color, border: outline ? `1px solid ${color}` : '1px solid transparent' };
}
