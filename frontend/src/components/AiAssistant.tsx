import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../api';
import { API_BASE, getMediaUrl } from '../config';
import AiQuota from './AiQuota';

interface Msg { role: 'user' | 'model'; text: string; }

const DOCK_WIDTH = 420;

// Grammar-tutor chat panel. Optionally scoped to a selected drill.
export default function AiAssistant({ drillId, drillLabel, autoAction, onClose }: {
  drillId?: number;
  drillLabel?: string;
  autoAction?: 'analyze' | 'review' | 'explain';  // on open, auto-run this on the drill
  onClose: () => void;
}) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [sayWord, setSayWord] = useState('');
  const [saying, setSaying] = useState(false);
  const [related, setRelated] = useState<{ id: number; text_catalan?: string; text?: string; words: string[] }[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const didAuto = useRef(false);
  const [quotaKey, setQuotaKey] = useState(0);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, busy]);

  // Auto-run analysis/review when opened from a drill button
  useEffect(() => {
    if (autoAction && drillId && !didAuto.current) {
      didAuto.current = true;
      const isReview = autoAction === 'review';
      const isExplain = autoAction === 'explain';
      setMessages([{ role: 'user', text: isExplain ? '💡 Explica\'m la frase paraula per paraula' : isReview ? '🔎 Revisa aquest drill' : '🔍 Analitza la forma taixelhit d\'aquest drill' }]);
      setBusy(true);
      const call = isExplain
        ? api.aiExplainDrill(drillId).then(r => { setRelated(r.related || []); return (r.draft ? '✍️ Lectura automàtica, encara no confirmada pel parlant.\n\n' : '') + r.explanation; })
        : isReview ? api.aiReviewDrill(drillId).then(r => r.review) : api.aiAnalyzeDrill(drillId).then(r => r.analysis);
      call
        .then(text => setMessages(m => [...m, { role: 'model', text }]))
        .catch(e => setMessages(m => [...m, { role: 'model', text: `⚠️ ${e.message || 'Error'}` }]))
        .finally(() => { setBusy(false); setQuotaKey(k => k + 1); });
    }
  }, [autoAction, drillId]);

  const suggestions = drillId
    ? ["Explica'm la frase paraula per paraula", 'Com es pronuncia?', 'Analitza el verb o els pronoms']
    : ['Com es forma el plural dels noms?', 'Explica els pronoms personals en amazic', "Com funciona l'estat d'annexió (construït)?"];

  const send = async (text: string) => {
    const q = text.trim();
    if (!q || busy) return;
    const history = messages.slice(-8);
    setMessages(m => [...m, { role: 'user', text: q }]);
    setInput('');
    setBusy(true);
    try {
      const res = await api.aiAsk(q, drillId, history);
      setMessages(m => [...m, { role: 'model', text: res.answer }]);
    } catch (e: any) {
      const msg: string = e?.message || 'Error';
      // a 429 carries a human sentence (daily cap / monthly budget); a server error gets the hint
      const limited = /consultes|Pressupost/i.test(msg);
      setMessages(m => [...m, { role: 'model', text: limited ? `⏳ ${msg}` : `⚠️ ${msg}. Comprova que GEMINI_API_KEY estigui configurada al servidor.` }]);
    } finally {
      setBusy(false);
      setQuotaKey(k => k + 1);
    }
  };

  // Synthetic Tamazight voice for one word or phrase (nothing is stored on the drill)
  const pronounce = async (text: string) => {
    const t = text.trim();
    if (!t || saying) return;
    setSaying(true);
    try {
      const r = await fetch(`${API_BASE}/tts/tachelhit`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: t }) });
      const j = await r.json();
      if (!r.ok || !j.url) throw new Error(j.detail || 'TTS');
      await new Audio(getMediaUrl(j.url)).play();
    } catch (e: any) {
      setMessages(m => [...m, { role: 'model', text: `⚠️ No he pogut pronunciar «${t}» (${e?.message || 'error de veu'}).` }]);
    } finally {
      setSaying(false);
    }
  };

  // Desktop: a dock snapped to the right edge that pushes the page (no overlay, the
  // list stays usable); phones: a full-height sheet over the page.
  const docked = typeof window !== 'undefined' && window.innerWidth >= 900;
  useEffect(() => {
    if (!docked) return;
    const prev = document.body.style.paddingRight;
    document.body.style.paddingRight = `${DOCK_WIDTH}px`;
    window.dispatchEvent(new Event('resize'));
    return () => { document.body.style.paddingRight = prev; window.dispatchEvent(new Event('resize')); };
  }, [docked]);

  return createPortal(
    <div
      style={docked
        ? { position: 'fixed', top: 0, right: 0, bottom: 0, width: `${DOCK_WIDTH}px`, zIndex: 100000, display: 'flex' }
        : { position: 'fixed', inset: 0, zIndex: 100000, display: 'flex', justifyContent: 'flex-end', background: 'rgba(15,23,42,0.4)' }}
      onClick={docked ? undefined : onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{ width: docked ? '100%' : 'min(480px, 100vw)', height: '100%', background: 'var(--bg)', display: 'flex', flexDirection: 'column', boxShadow: 'var(--shadow-lg)', borderLeft: docked ? '1px solid var(--border)' : 'none' }}
      >
        {/* Header */}
        <div style={{ background: 'var(--brand-gradient)', color: '#fff', padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontWeight: 800, fontSize: '17px' }}>{autoAction === 'explain' ? '💡 Explica\'m la frase' : '🤖 Assistent de gramàtica'}</div>
            <div style={{ fontSize: '12px', opacity: 0.85 }}>
              {drillLabel ? `Sobre: ${drillLabel}` : 'Amazic · taixelhit · font: amazic.cat'}
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'rgba(255,255,255,0.2)', border: 'none', color: '#fff', width: '32px', height: '32px', borderRadius: 'var(--r-pill)', cursor: 'pointer', fontSize: '16px' }}>✕</button>
        </div>

        {/* Messages */}
        <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {messages.length === 0 && (
            <div style={{ color: 'var(--text-soft)', fontSize: '14px' }}>
              <p style={{ marginTop: 0 }}>Pregunta'm sobre la gramàtica amaziga{drillId ? ' o aquest drill' : ''}. Em baso en el Compendi de Gramàtica Amaziga.</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {suggestions.map((s, i) => (
                  <button key={i} onClick={() => send(s)} style={{ textAlign: 'left', padding: '10px 14px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', cursor: 'pointer', fontSize: '13px', color: 'var(--text)' }}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} style={{ alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '88%' }}>
              <div style={{
                padding: '10px 14px', borderRadius: 'var(--r-lg)', fontSize: '14px', lineHeight: 1.5, whiteSpace: 'pre-wrap',
                background: m.role === 'user' ? 'var(--brand-1)' : 'var(--surface)',
                color: m.role === 'user' ? '#fff' : 'var(--text)',
                border: m.role === 'user' ? 'none' : '1px solid var(--border)',
              }}>
                {m.text}
              </div>
            </div>
          ))}
          {busy && (
            <div style={{ alignSelf: 'flex-start', padding: '10px 14px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', color: 'var(--text-muted)', fontSize: '14px' }}>
              pensant…
            </div>
          )}
          {related.length > 0 && !busy && (
            <div style={{ alignSelf: 'stretch', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '12px 14px' }}>
              <div style={{ fontWeight: 800, fontSize: '13px', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '8px' }}>Altres drills amb les mateixes paraules</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {related.map(r => (
                  <a key={r.id} href={`/?q=${encodeURIComponent(r.text_catalan || String(r.id))}`} style={{ textDecoration: 'none', color: 'var(--text)', fontSize: '13px', lineHeight: 1.4, padding: '8px 10px', borderRadius: 'var(--r-md)', background: 'var(--surface-2)' }}>
                    <span style={{ fontWeight: 700 }}>{r.text_catalan || `Drill #${r.id}`}</span>
                    {r.text && <span style={{ display: 'block', color: 'var(--text-soft)' }}>{r.text}</span>}
                    <span style={{ display: 'block', marginTop: '3px', fontSize: '12px', color: 'var(--brand-1)', fontWeight: 700 }}>{r.words.join(' · ')}</span>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Pronounce a word with the synthetic voice */}
        <div style={{ padding: '8px 12px 0', borderTop: '1px solid var(--border)', display: 'flex', gap: '8px', alignItems: 'center' }}>
          <input
            value={sayWord}
            onChange={(e) => setSayWord(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') pronounce(sayWord); }}
            placeholder="Pronuncia una paraula (veu sintètica)…"
            aria-label="Paraula a pronunciar"
            style={{ flex: 1, padding: '9px 12px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: '13px', color: 'var(--text)', outline: 'none' }}
          />
          <button onClick={() => pronounce(sayWord)} disabled={saying || !sayWord.trim()} title="Veu sintètica tamazight: orientativa, no és la del parlant" style={{ padding: '9px 14px', background: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: saying ? 'wait' : 'pointer' }}>
            {saying ? '…' : '🔊'}
          </button>
        </div>

        {/* Input */}
        <div style={{ padding: '12px', display: 'flex', gap: '8px' }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') send(input); }}
            placeholder="Fes una pregunta…"
            disabled={busy}
            style={{ flex: 1, padding: '12px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: '14px', color: 'var(--text)', outline: 'none' }}
          />
          <button onClick={() => send(input)} disabled={busy || !input.trim()} style={{ padding: '12px 18px', background: 'var(--brand-gradient)', color: '#fff', border: 'none', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: busy ? 'wait' : 'pointer' }}>
            ↑
          </button>
        </div>
        <AiQuota refreshKey={quotaKey} />
      </div>
    </div>,
    document.body
  );
}
