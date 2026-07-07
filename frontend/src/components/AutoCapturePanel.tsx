import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaBolt, FaCheck, FaExclamationTriangle } from 'react-icons/fa';
import { api, type CaptureStatus } from '../api';
import { toast } from '../toast';

// Hands-off capture: queue a URL for the local agent to download on the user's
// own IP (dodging YouTube's block of Render), then Render makes drills. The
// user only pastes a URL here — the background agent (tools/capture_agent.py)
// does the rest.
const STAGE: Record<string, string> = {
  pending: 'A la cua — esperant el teu descarregador local…',
  claimed: 'Descarregant al teu ordinador…',
  processing: 'Render està creant els drills…',
  done: 'Fet',
  failed: 'Ha fallat',
};

export default function AutoCapturePanel() {
  const [url, setUrl] = useState('');
  const [tag, setTag] = useState('');
  const [reqId, setReqId] = useState<number | null>(null);
  const [status, setStatus] = useState<CaptureStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef<number | null>(null);
  const navigate = useNavigate();

  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current); }, []);

  const poll = (id: number) => {
    api.captureStatus(id)
      .then((s) => {
        setStatus(s);
        if (s.status === 'done' || s.status === 'failed') {
          setBusy(false);
          if (s.status === 'failed') toast.error(s.error || 'La captura ha fallat');
          return;
        }
        timer.current = window.setTimeout(() => poll(id), 4000);
      })
      .catch(() => { timer.current = window.setTimeout(() => poll(id), 5000); });
  };

  const start = async () => {
    const u = url.trim();
    if (!u) return;
    setBusy(true);
    setStatus(null);
    try {
      const { request_id } = await api.captureRequest(u, { tag: tag.trim() || undefined, audio_only: true });
      setReqId(request_id);
      toast.success('A la cua — el teu descarregador ho agafarà');
      poll(request_id);
    } catch (e: any) {
      setBusy(false);
      toast.error(e.message || 'No s\'ha pogut encuar');
    }
  };

  const done = status?.status === 'done';
  const failed = status?.status === 'failed';
  const n = status?.drills_created?.length ?? 0;

  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', padding: '20px', marginBottom: '18px', boxShadow: 'var(--shadow-sm)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '9px', marginBottom: '6px' }}>
        <span style={{ display: 'inline-flex', width: 34, height: 34, borderRadius: 'var(--r-md)', background: 'var(--brand-gradient-soft)', color: 'var(--brand-1)', alignItems: 'center', justifyContent: 'center' }}><FaBolt /></span>
        <div>
          <div style={{ fontWeight: 700, fontFamily: 'var(--font-display)', fontSize: '16px', color: 'var(--text)' }}>Captura automàtica</div>
          <div style={{ fontSize: '12px', color: 'var(--text-soft)' }}>Enganxa un URL de YouTube — el teu ordinador el baixa i Render fa els drills, sol.</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginTop: '12px' }}>
        <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://www.youtube.com/watch?v=…"
          style={{ flex: 2, minWidth: '220px', padding: '12px 14px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface-2)', fontSize: '15px', color: 'var(--text)' }} />
        <input value={tag} onChange={(e) => setTag(e.target.value)} placeholder="etiqueta (opcional)"
          style={{ flex: 1, minWidth: '120px', padding: '12px 14px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface-2)', fontSize: '15px', color: 'var(--text)' }} />
        <button onClick={start} disabled={busy || !url.trim()}
          style={{ padding: '12px 20px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 700, fontSize: '14px', cursor: (busy || !url.trim()) ? 'not-allowed' : 'pointer', opacity: (busy || !url.trim()) ? 0.6 : 1 }}>
          {busy ? 'En marxa…' : 'Captura'}
        </button>
      </div>

      {status && (
        <div style={{ marginTop: '14px', padding: '12px 14px', borderRadius: 'var(--r-md)', background: done ? 'var(--emerald-soft)' : failed ? 'var(--rose-soft)' : 'var(--surface-2)', border: `1px solid ${done ? 'var(--emerald)' : failed ? 'var(--rose)' : 'var(--border)'}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13.5px', fontWeight: 700, color: done ? 'var(--emerald)' : failed ? 'var(--rose)' : 'var(--text)' }}>
            {done ? <FaCheck /> : failed ? <FaExclamationTriangle /> : null}
            {done ? `${n} drill${n === 1 ? '' : 's'} creats` : (STAGE[status.status] || status.status)}
            {status.job_status && status.status === 'processing' ? ` (${status.job_status})` : ''}
          </div>
          {done && (
            <button onClick={() => navigate('/')} style={{ marginTop: '10px', padding: '8px 16px', borderRadius: 'var(--r-pill)', border: '1px solid var(--emerald)', background: 'var(--surface)', color: 'var(--emerald)', fontWeight: 700, fontSize: '13px', cursor: 'pointer' }}>
              Veure els drills
            </button>
          )}
        </div>
      )}

      {reqId && status && (status.status === 'pending' || status.status === 'claimed') && (
        <div style={{ marginTop: '8px', fontSize: '11.5px', color: 'var(--text-muted)' }}>
          Cal que el teu <strong>agent de captura</strong> estigui en marxa a l'ordinador (tools/capture_agent). Si no baixa en un minut, engega'l.
        </div>
      )}
    </div>
  );
}
