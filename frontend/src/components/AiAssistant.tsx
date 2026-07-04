import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { api } from '../api';

interface Msg { role: 'user' | 'model'; text: string; }

// Grammar-tutor chat panel. Optionally scoped to a selected drill.
export default function AiAssistant({ drillId, drillLabel, autoAnalyze, onClose }: {
  drillId?: number;
  drillLabel?: string;
  autoAnalyze?: boolean;   // on open, auto-run a morphological analysis of the drill
  onClose: () => void;
}) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const didAuto = useRef(false);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, busy]);

  // Auto-analysis when opened from a drill's "Analitza" button
  useEffect(() => {
    if (autoAnalyze && drillId && !didAuto.current) {
      didAuto.current = true;
      setMessages([{ role: 'user', text: '🔍 Analitza la forma taixelhit d\'aquest drill' }]);
      setBusy(true);
      api.aiAnalyzeDrill(drillId)
        .then(r => setMessages(m => [...m, { role: 'model', text: r.analysis }]))
        .catch(e => setMessages(m => [...m, { role: 'model', text: `⚠️ ${e.message || 'Error'}` }]))
        .finally(() => setBusy(false));
    }
  }, [autoAnalyze, drillId]);

  const suggestions = drillId
    ? ["Explica la gramàtica d'aquesta frase", 'Com es pronuncia?', 'Analitza el verb o els pronoms']
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
      setMessages(m => [...m, { role: 'model', text: `⚠️ ${e.message || 'Error'}. Comprova que GEMINI_API_KEY estigui configurada al servidor.` }]);
    } finally {
      setBusy(false);
    }
  };

  return createPortal(
    <div style={{ position: 'fixed', inset: 0, zIndex: 30000, display: 'flex', justifyContent: 'flex-end', background: 'rgba(15,23,42,0.4)' }} onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        style={{ width: 'min(480px, 100vw)', height: '100%', background: 'var(--bg)', display: 'flex', flexDirection: 'column', boxShadow: 'var(--shadow-lg)' }}
      >
        {/* Header */}
        <div style={{ background: 'var(--brand-gradient)', color: '#fff', padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontWeight: 800, fontSize: '17px' }}>🤖 Assistent de gramàtica</div>
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
        </div>

        {/* Input */}
        <div style={{ padding: '12px', borderTop: '1px solid var(--border)', display: 'flex', gap: '8px' }}>
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
      </div>
    </div>,
    document.body
  );
}
