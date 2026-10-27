import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, type VerifyItem, type VerifyQueue as VerifyQueueData } from '../api';
import { getMediaUrl } from '../config';
import { toast } from '../toast';
import RecordAudioModal from './RecordAudioModal';
import { FaCheck, FaPen, FaForward, FaRedo, FaUser, FaMicrophone } from 'react-icons/fa';

/**
 * Speaker verification queue. The listening review left machine readings ("[heard]" /
 * "[? a | b]") next to doubtful recordings; here a speaker hears each clip and decides:
 * accept a reading, keep the stored text, correct it in place (tap the text), record their own
 * voice, or skip. Phone-first, one drill at a time.
 */
export default function VerifyQueue() {
  const navigate = useNavigate();
  const [data, setData] = useState<VerifyQueueData | null>(null);
  const [items, setItems] = useState<VerifyItem[]>([]);
  const [idx, setIdx] = useState(0);
  const [reason, setReason] = useState<string>('');
  const [registered, setRegistered] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  // tapping the stored text turns it into a box to correct it in place
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mediaRef = useRef<HTMLVideoElement | HTMLAudioElement | null>(null);

  const load = useCallback(async (keepIndex = false) => {
    try {
      const r = await api.verifyQueue(reason || undefined, 500);
      setData(r);
      setItems(r.drills);
      setIdx(i => (keepIndex ? Math.min(i, Math.max(0, r.drills.length - 1)) : 0));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [reason]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { api.me().then(m => setRegistered(!!m)).catch(() => setRegistered(false)); }, []);

  const current = items[idx];
  useEffect(() => { setEditing(false); }, [current?.id]);
  const replay = useCallback(() => {
    const m = mediaRef.current;
    if (!m) return;
    m.currentTime = 0;
    m.play().catch(() => {});
  }, []);

  // Space replays the clip (desktop); the editor has its own keys
  useEffect(() => {
    if (editing || recording) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.code === 'Space' && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement)) {
        e.preventDefault();
        replay();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [editing, recording, replay]);

  const dropCurrent = () => {
    if (!current) return;
    const gone = current.reason;
    setItems(list => list.filter((_, i) => i !== idx));
    setData(d => d ? { ...d, total: d.total - 1, counts: { ...d.counts, [gone]: Math.max(0, (d.counts[gone] || 0) - 1) } } : d);
    setIdx(i => Math.min(i, Math.max(0, items.length - 2)));
  };

  const resolve = async (text?: string) => {
    if (!current || busy) return;
    setBusy(true);
    try {
      await api.resolveDrill(current.id, text);
      toast.success(text ? 'Text confirmat' : 'Text mantingut');
      dropCurrent();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const startEdit = () => {
    if (registered === false || busy) return;
    setDraft((current?.text_tachelhit || '').trim());
    setEditing(true);
  };

  const skip = () => setIdx(i => (items.length ? (i + 1) % items.length : 0));

  const stored = (current?.text_tachelhit || '').trim();
  const latin = (current?.text_tachelhit_latin || '').trim();
  const label = current ? (data?.labels[current.reason] || current.reason) : '';
  const heardTitle = current?.reason === 'subtitle' ? 'Lectura del subtítol (sense confirmar)' : current?.reason === 'confirm' ? 'La màquina ha sentit el mateix' : 'El que la màquina ha sentit (no verificat)';
  const totalAll = data ? Object.values(data.counts).reduce((a, b) => a + b, 0) : 0;

  const chip = (active: boolean): React.CSSProperties => ({
    padding: '6px 12px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', cursor: 'pointer',
    fontWeight: 700, fontSize: '13px', whiteSpace: 'nowrap',
    background: active ? 'var(--brand-gradient-soft)' : 'var(--surface-2)', color: active ? 'var(--brand-1)' : 'var(--text-soft)',
  });
  const bigBtn = (kind: 'accept' | 'keep' | 'neutral'): React.CSSProperties => ({
    width: '100%', textAlign: 'left', padding: '12px 14px', borderRadius: '12px', cursor: busy ? 'wait' : 'pointer',
    fontWeight: 700, fontSize: '16px', display: 'flex', alignItems: 'center', gap: '10px', lineHeight: 1.3,
    border: kind === 'neutral' ? '1px solid var(--border)' : 'none',
    background: kind === 'accept' ? 'var(--emerald)' : kind === 'keep' ? 'var(--emerald-soft)' : 'var(--surface-2)',
    color: kind === 'accept' ? '#fff' : kind === 'keep' ? 'var(--emerald)' : 'var(--text)',
    opacity: busy ? 0.6 : 1,
  });

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', paddingBottom: 'calc(40px + env(safe-area-inset-bottom, 0px))' }}>
      <div style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)', padding: '14px 16px' }}>
        <div style={{ maxWidth: '640px', margin: '0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: '12px' }}>
            <h1 style={{ margin: 0, fontFamily: 'var(--font-display)', fontSize: '22px', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>Per verificar</h1>
            {data && <span style={{ color: 'var(--text-soft)', fontSize: '14px', fontWeight: 700 }}>{items.length ? `${idx + 1} / ${items.length}` : '0'}</span>}
          </div>
          <p style={{ margin: '4px 0 10px', color: 'var(--text-soft)', fontSize: '13px' }}>
            Escolta la gravació i digues què es diu de veritat. Les lectures proposades les ha fet una màquina.
          </p>
          {data && (
            <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '2px' }}>
              <button style={chip(reason === '')} onClick={() => setReason('')}>Tot ({totalAll})</button>
              {Object.entries(data.counts).map(([k, n]) => (
                <button key={k} style={chip(reason === k)} onClick={() => setReason(k)} title={data.labels[k]}>
                  {SHORT[k] || k} ({n})
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div style={{ maxWidth: '640px', margin: '0 auto', padding: '14px 16px' }}>
        {registered === false && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 12px', marginBottom: '12px', background: 'var(--surface-2)', border: '1px solid var(--saffron)', borderRadius: '12px', fontSize: '14px', color: 'var(--text)' }}>
            <FaUser /> Per verificar cal un perfil registrat: la verificació queda signada.
            <button onClick={() => navigate('/profile')} style={{ marginLeft: 'auto', padding: '6px 10px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--saffron)', color: '#fff', fontWeight: 700, cursor: 'pointer' }}>Perfil</button>
          </div>
        )}
        {error && <p style={{ color: 'var(--text)' }}>{error}</p>}
        {data && !current && !error && (
          <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-soft)' }}>
            <div style={{ fontSize: '40px' }}>✅</div>
            <p style={{ fontWeight: 700, color: 'var(--text)' }}>Res per verificar{reason ? ' en aquest grup' : ''}.</p>
          </div>
        )}
        {current && (
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '16px', padding: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '12px', fontWeight: 700, padding: '3px 9px', borderRadius: 'var(--r-pill)', background: 'var(--saffron)', color: '#fff' }}>{label}</span>
              <span style={{ fontSize: '12px', color: 'var(--text-soft)' }}>#{current.id}{current.tag ? ` · ${current.tag}` : ''}</span>
            </div>

            {current.video_url ? (
              <video key={current.id} ref={el => { mediaRef.current = el; }} src={getMediaUrl(current.video_url)} controls autoPlay playsInline
                     style={{ width: '100%', maxHeight: '38vh', borderRadius: '12px', background: '#000' }} />
            ) : (
              <audio key={current.id} ref={el => { mediaRef.current = el; }} src={getMediaUrl(current.audio_url || '')} controls autoPlay style={{ width: '100%' }} />
            )}
            <button onClick={replay} style={{ ...bigBtn('neutral'), marginTop: '8px', justifyContent: 'center' }}><FaRedo /> Torna a escoltar</button>

            <div style={{ marginTop: '14px' }}>
              <div style={{ fontSize: '17px', fontWeight: 700, color: 'var(--text)' }}>{current.text_catalan || <em style={{ color: 'var(--text-soft)' }}>sense català</em>}</div>
              {current.text_arabic && <div dir="rtl" style={{ fontSize: '16px', color: 'var(--text-soft)', marginTop: '2px' }}>{current.text_arabic}</div>}
            </div>

            <div style={{ marginTop: '12px' }}>
              <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-soft)' }}>Text actual</div>
              {!editing ? (
                <>
                  <button onClick={startEdit} disabled={registered === false} aria-label="Toca per corregir el text"
                          style={{ display: 'block', width: '100%', textAlign: 'left', marginTop: '4px', padding: '10px 12px', borderRadius: '12px', background: 'var(--surface-2)', border: '1px dashed var(--brand-1)', cursor: registered === false ? 'default' : 'text', fontFamily: 'inherit' }}>
                    <span style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                      <span style={{ flex: 1, minWidth: 0 }}>
                        <span style={{ display: 'block', fontSize: '18px', fontFamily: 'var(--font-tifinagh)', color: stored ? 'var(--text)' : 'var(--text-soft)' }}>{stored || '— sense text —'}</span>
                        {latin && latin !== stored && <span style={{ display: 'block', fontSize: '14px', color: 'var(--text-soft)' }}>{latin}</span>}
                      </span>
                      <FaPen style={{ flexShrink: 0, marginTop: '5px', color: 'var(--brand-1)' }} />
                    </span>
                  </button>
                  <div style={{ fontSize: '12px', color: 'var(--text-soft)', marginTop: '4px' }}>
                    {stored ? 'No és ben bé el que se sent? Toca el text i corregeix-lo tu mateix.' : 'Toca aquí i escriu el que se sent.'}
                  </div>
                </>
              ) : (
                <div style={{ marginTop: '4px' }}>
                  <textarea autoFocus value={draft} onChange={e => setDraft(e.target.value)} rows={2} aria-label="El text tal com se sent"
                            onKeyDown={e => { if (e.key === 'Escape') setEditing(false); if (e.key === 'Enter' && !e.shiftKey && draft.trim()) { e.preventDefault(); resolve(draft.trim()); } }}
                            style={{ display: 'block', width: '100%', boxSizing: 'border-box', padding: '10px 12px', borderRadius: '12px', border: '2px solid var(--brand-1)', background: 'var(--surface)', color: 'var(--text)', fontSize: '18px', fontFamily: 'var(--font-tifinagh)', resize: 'vertical' }} />
                  <div style={{ fontSize: '12px', color: 'var(--text-soft)', margin: '4px 0 8px' }}>
                    Escriu-ho tal com ho sents a la gravació, en llatí o en tifinagh. En desar-lo, queda com a text verificat i signat amb el teu perfil.
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button disabled={busy || !draft.trim()} onClick={() => resolve(draft.trim())} style={{ ...bigBtn('accept'), justifyContent: 'center', opacity: busy || !draft.trim() ? 0.6 : 1 }}><FaCheck /> Desa aquest text</button>
                    <button onClick={() => setEditing(false)} style={{ ...bigBtn('neutral'), justifyContent: 'center' }}>Cancel·la</button>
                  </div>
                </div>
              )}
            </div>

            {current.heard.length > 0 && (
              <div style={{ marginTop: '12px' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-soft)', marginBottom: '6px' }}>{heardTitle}</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {current.heard.map(opt => (
                    <button key={opt} disabled={busy || registered === false} onClick={() => resolve(opt)} style={bigBtn('accept')}>
                      <FaCheck style={{ flexShrink: 0 }} /><span style={{ fontFamily: 'var(--font-tifinagh)' }}>{opt}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
              {stored && !editing && (
                <button disabled={busy || registered === false} onClick={() => resolve()} style={bigBtn('keep')}>
                  <FaCheck /> El text actual és correcte
                </button>
              )}
              <div style={{ display: 'flex', gap: '8px' }}>
                <button onClick={() => setRecording(true)} style={{ ...bigBtn('neutral'), justifyContent: 'center' }}><FaMicrophone /> Grava-ho tu</button>
                <button onClick={skip} style={{ ...bigBtn('neutral'), justifyContent: 'center' }}><FaForward /> Salta</button>
              </div>
            </div>
          </div>
        )}
      </div>

      {recording && current && (
        <RecordAudioModal drill={current} onClose={() => setRecording(false)}
                          onSaved={() => { setRecording(false); toast.success('Gràcies: la teva veu queda al costat de la gravació original.'); }} />
      )}
    </div>
  );
}

const SHORT: Record<string, string> = {
  differs: 'No coincideix',
  contested: 'Dues escoltes',
  empty: 'Sense text',
  subtitle: 'Subtítol',
  confirm: 'Confirma',
};
