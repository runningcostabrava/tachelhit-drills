import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaBolt, FaCheck, FaExclamationTriangle } from 'react-icons/fa';
import { api, type CaptureStatus, type CaptureQueueItem } from '../api';
import { toast } from '../toast';

// Hands-off capture: queue a URL for the local agent to download on the user's
// own IP (dodging YouTube's block of Render), then Render makes drills. The
// user only pastes a URL here — the background agent (tools/capture_agent.py)
// does the rest.
const AGENT_WIN = 'https://github.com/runningcostabrava/tachelhit-drills/releases/download/capture-agent/TachelhitCaptureAgent.exe';
const AGENT_MAC = 'https://github.com/runningcostabrava/tachelhit-drills/releases/download/capture-agent/TachelhitCaptureAgent-macos.zip';

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
  const [audioOnly, setAudioOnly] = useState(false); // video clips by default; audio for podcasts
  const [variety, setVariety] = useState('');
  const [varieties, setVarieties] = useState<{ code: string; label: string }[]>([]);
  useEffect(() => { api.varieties().then(setVarieties).catch(() => setVarieties([])); }, []);
  const [status, setStatus] = useState<CaptureStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [agent, setAgent] = useState<{ online: boolean; version: string | null; latest?: string | null } | null>(null);
  const [busyRow, setBusyRow] = useState<number | null>(null);
  // An agent older than the one the release is built from fails in ways that look like a broken
  // video, so say it instead of leaving it to be guessed (#197).
  const outdated = !!(agent?.online && agent.version && agent.latest && agent.version !== agent.latest);

  const act = async (id: number, what: () => Promise<unknown>, said: string) => {
    setBusyRow(id);
    try { await what(); toast.success(said); await refreshQueue(); }
    catch (e: any) { toast.error(e?.message || 'No s\u2019ha pogut'); }
    finally { setBusyRow(null); }
  };
  const retry = (id: number) => act(id, () => api.retryCapture(id), 'Tornada a la cua');
  const forget = (id: number) => act(id, () => api.forgetCapture(id), 'Treta de la llista');
  const clearDone = async () => {
    const done = queue.filter((r) => r.status === 'done');
    for (const r of done) { try { await api.forgetCapture(r.id); } catch { /* keep going */ } }
    toast.success(`${done.length} ${done.length === 1 ? 'captura treta' : 'captures tretes'}`);
    await refreshQueue();
  };
  // The queue: what the agent has done and is doing (the server's list, not the agent's log).
  const [queue, setQueue] = useState<CaptureQueueItem[]>([]);
  // One way of reading the queue, used by the poll and by every button that changes it.
  const refreshQueue = useCallback(
    () => api.captureQueue(20).then((q) => { setQueue(q.requests); setAgent(q.agent); }).catch(() => {}),
    [],
  );
  useEffect(() => {
    refreshQueue();
    const id = window.setInterval(refreshQueue, 15000);
    return () => window.clearInterval(id);
  }, [status?.status, refreshQueue]);
  const timer = useRef<number | null>(null);
  const navigate = useNavigate();

  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current); }, []);

  // Is a local agent connected? Checked on mount and every 10 s while the panel is open,
  // so the user knows before pasting a URL that nobody would download.
  useEffect(() => {
    let alive = true;
    const check = () => api.captureAgent().then((a) => { if (alive) setAgent(a); }).catch(() => { if (alive) setAgent(null); });
    check();
    const id = window.setInterval(check, 10000);
    return () => { alive = false; window.clearInterval(id); };
  }, []);

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
      const { request_id } = await api.captureRequest(u, { tag: tag.trim() || undefined, audio_only: audioOnly, variety: variety || undefined });
      toast.success('A la cua — el teu descarregador ho agafarà');
      poll(request_id);
    } catch (e) {
      setBusy(false);
      toast.error((e as Error).message || 'No s\'ha pogut encuar');
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
      <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '10px', fontSize: '13px', color: 'var(--text-soft)', cursor: 'pointer' }}>
        <input type="checkbox" checked={audioOnly} onChange={(e) => setAudioOnly(e.target.checked)} />
        Només àudio (podcast / veu) — sense marcar, cada drill porta el seu clip de vídeo
      </label>
      <label style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px', marginTop: '8px', fontSize: '13px', color: 'var(--text-soft)' }}>
        <span style={{ whiteSpace: 'nowrap' }}>Varietat que ensenya el vídeo</span>
        <select value={variety} onChange={(e) => setVariety(e.target.value)} style={{ flex: '1 1 200px', minWidth: 0, maxWidth: '100%', padding: '6px 8px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--text)' }}>
          <option value="">— com les captures anteriors del canal —</option>
          {varieties.map((v) => <option key={v.code} value={v.code}>{v.label}</option>)}
        </select>
      </label>

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

      <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', fontSize: '12.5px', color: 'var(--text-soft)' }}>
        <span aria-hidden style={{ width: 9, height: 9, borderRadius: '50%', background: agent?.online ? 'var(--emerald)' : 'var(--rose)', flex: 'none' }} />
        {agent?.online ? (
          <span>Agent de captura connectat al teu ordinador{agent.version ? ` (v${agent.version})` : ''}.</span>
        ) : (
          <span>Cap agent de captura connectat. Instal·la'l un cop al teu ordinador: s'engega sol en iniciar sessió.</span>
        )}
        {/* The links live outside that branch on purpose: they used to appear only when NO agent
            was connected, which is exactly when you do not need them. You want them to put one on
            another computer, or to replace the one you have (#197). */}
        <span style={{ opacity: agent?.online && !outdated ? 0.65 : 1 }}>
          <a href={AGENT_WIN} style={{ color: 'var(--brand-1)', fontWeight: 700 }}>Windows</a>
          {' · '}
          <a href={AGENT_MAC} style={{ color: 'var(--brand-1)', fontWeight: 700 }}>Mac</a>
        </span>
        {outdated && (
          <span style={{ color: 'var(--saffron-dark, #7A4A12)', fontWeight: 700 }}>
            N'hi ha una de més nova (v{agent?.latest}). Un agent vell falla d'una manera que sembla
            un error del vídeo: val la pena actualitzar-lo.
          </span>
        )}
      </div>

      {queue.length > 0 && (
        <div style={{ marginTop: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 10, marginBottom: '6px' }}>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Cua de captures</div>
            {queue.some((r) => r.status === 'done') && (
              <button onClick={clearDone} style={{ ...rowBtn, color: 'var(--text-muted)' }}>Neteja les fetes</button>
            )}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {queue.map((r) => {
              const state = r.status === 'done' ? 'fet' : r.status === 'failed' ? 'error' : r.status === 'pending' ? 'en cua' : 'en curs';
              const color = r.status === 'done' ? 'var(--emerald)' : r.status === 'failed' ? 'var(--rose)' : r.status === 'pending' ? 'var(--text-muted)' : 'var(--saffron-strong)';
              const when = r.created_at ? new Date(r.created_at).toLocaleTimeString('ca-ES', { hour: '2-digit', minute: '2-digit' }) : '';
              const finished = r.status === 'done' || r.status === 'failed';
              return (
                <div key={r.id} style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '7px 10px', borderRadius: 'var(--r-md)', background: 'var(--surface-2)', border: '1px solid var(--border)', fontSize: '12.5px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, flex: 'none' }} aria-hidden />
                    {/* the VIDEO, not the tag: twelve rows all reading «Nomatrails YouTube, Aït Mraw»
                        said nothing about which one each was (#197) */}
                    <a href={r.url} target="_blank" rel="noopener noreferrer"
                       style={{ fontWeight: 700, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1, minWidth: 120 }}>
                      {r.url.replace(/^https?:\/\/(www\.)?/, '')}
                    </a>
                    <span style={{ color, fontWeight: 700, flex: 'none' }}>{state}{r.drills_created != null ? ` · ${Array.isArray(r.drills_created) ? r.drills_created.length : r.drills_created} drills` : ''}</span>
                    <span style={{ color: 'var(--text-muted)', flex: 'none' }}>{when}</span>
                    {r.status === 'failed' && (
                      <button onClick={() => retry(r.id)} disabled={busyRow === r.id} style={rowBtn}>
                        {busyRow === r.id ? '…' : 'Torna-ho a provar'}
                      </button>
                    )}
                    {finished && (
                      <button onClick={() => forget(r.id)} disabled={busyRow === r.id} style={{ ...rowBtn, color: 'var(--text-muted)' }} title="Treu-la de la llista">×</button>
                    )}
                  </div>
                  {r.tag && <div style={{ color: 'var(--text-muted)' }}>{r.tag}</div>}
                  {/* the reason, readable: it used to live in a mouse-over, which on a phone is nowhere */}
                  {r.error && <div style={{ color: 'var(--rose)', lineHeight: 1.45, wordBreak: 'break-word' }}>{r.error}</div>}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

const rowBtn: React.CSSProperties = {
  flex: 'none', padding: '3px 9px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)',
  background: 'var(--surface)', color: 'var(--brand-1)', fontWeight: 700, fontSize: '11.5px',
  cursor: 'pointer', fontFamily: 'inherit',
};
