import { useState, useRef, useEffect } from 'react';
import { api } from '../api';
import { getMediaUrl } from '../config';
import { subscribeSelection, notifyDrillsChanged } from '../selection';
import { FaComments, FaPlay, FaRedo, FaChevronRight, FaPaperPlane, FaCheck, FaSearch, FaExclamationTriangle } from 'react-icons/fa';

interface Action { name: string; args: any; result: any; }
interface Msg { role: 'user' | 'model'; text: string; actions?: Action[]; }

// Collapsible right-hand copilot dock. Agentic: it can create/edit/search
// drills and speak Tachelhit, aware of the currently-selected drills.
export default function AiCopilot({ onClose }: { onClose: () => void }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<number[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => subscribeSelection(setSelected), []);
  useEffect(() => {
    inputRef.current?.focus();
    const onKeyDown = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }, [messages, busy]);

  const play = (url: string) => { const a = new Audio(getMediaUrl(url)); a.play().catch(() => {}); };

  const send = async (text: string) => {
    const q = text.trim();
    if (!q || busy) return;
    const history = messages.slice(-8).map(m => ({ role: m.role, text: m.text }));
    setMessages(m => [...m, { role: 'user', text: q }]);
    setInput('');
    setBusy(true);
    try {
      const res = await api.aiAgent(q, selected, history);
      setMessages(m => [...m, { role: 'model', text: res.answer, actions: res.actions }]);
      // Refresh drill lists if the copilot changed data
      if (res.actions?.some(a => ['create_drill', 'update_drill'].includes(a.name) && !a.result?.error)) {
        notifyDrillsChanged();
      }
    } catch (e: any) {
      setMessages(m => [...m, { role: 'model', text: `⚠️ No he pogut respondre ara mateix. Torna-ho a provar d'aquí a un moment.` }]);
    } finally {
      setBusy(false);
    }
  };

  const suggestions = selected.length
    ? ['Analitza el drill seleccionat', 'Tradueix-lo i desa la forma', 'Fes 3 exemples i deixa-me\'ls escoltar']
    : ['Crea un drill: «aigua» en taixelhit', 'Cerca drills sobre la família', 'Com es diu «gràcies»? Fes-m\'ho escoltar'];

  const renderActions = (actions?: Action[]) => {
    if (!actions?.length) return null;
    return (
      <div role="group" aria-label="Accions realitzades" style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '8px' }}>
        {actions.map((a, i) => {
          if (a.result?.error) return <span key={i} style={chip('var(--rose-soft)', 'var(--rose)')}><FaExclamationTriangle style={{ marginRight: '4px', verticalAlign: '-1px' }} />{a.name}: {a.result.error}</span>;
          if (a.name === 'create_drill') return <span key={i} style={chip('var(--emerald-soft)', 'var(--emerald)')}><FaCheck style={{ marginRight: '4px', verticalAlign: '-1px' }} />Drill #{a.result.created_drill_id} creat</span>;
          if (a.name === 'update_drill') return <span key={i} style={chip('var(--emerald-soft)', 'var(--emerald)')}><FaCheck style={{ marginRight: '4px', verticalAlign: '-1px' }} />Drill #{a.result.updated_drill_id} actualitzat</span>;
          if (a.name === 'search_drills') return <span key={i} style={chip('var(--surface-2)', 'var(--text-soft)')}><FaSearch style={{ marginRight: '4px', verticalAlign: '-1px' }} />{a.result.count} resultats</span>;
          if (a.name === 'speak_tachelhit' && a.result?.audio_url)
            return (
              <button key={i} onClick={() => play(a.result.audio_url)} style={{ ...chip('var(--sky-soft)', 'var(--sky)'), cursor: 'pointer', border: '1px solid var(--sky)' }}>
                <FaPlay style={{ marginRight: '4px', verticalAlign: '-1px' }} />Escolta «{a.result.text}»
              </button>
            );
          return null;
        })}
      </div>
    );
  };

  return (
    <div role="dialog" aria-label="Copilot" style={{
      position: 'fixed', top: 0, right: 0, bottom: 0, width: 'min(440px, 100vw)', zIndex: 15000,
      background: 'var(--bg)', borderLeft: '1px solid var(--border)', boxShadow: '-8px 0 32px rgba(15,23,42,0.12)',
      display: 'flex', flexDirection: 'column'
    }}>
      <div style={{ background: 'var(--brand-gradient)', color: '#fff', padding: 'calc(14px + env(safe-area-inset-top)) 18px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontWeight: 800, fontSize: '16px', fontFamily: 'var(--font-display)', display: 'flex', alignItems: 'center', gap: '8px' }}><FaComments /> Copilot</div>
          <div style={{ fontSize: '11px', opacity: 0.85 }}>
            {selected.length ? `${selected.length} drill(s) seleccionats` : 'crea · tradueix · cerca · escolta'}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {messages.length > 0 && (
            <button onClick={() => setMessages([])} title="Nova conversa" aria-label="Nova conversa" style={{ background: 'rgba(255,255,255,0.2)', border: 'none', color: '#fff', width: '32px', height: '32px', borderRadius: 'var(--r-pill)', cursor: 'pointer', fontSize: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><FaRedo /></button>
          )}
          <button onClick={onClose} title="Amaga" aria-label="Amaga el copilot" style={{ background: 'rgba(255,255,255,0.2)', border: 'none', color: '#fff', width: '32px', height: '32px', borderRadius: 'var(--r-pill)', cursor: 'pointer', fontSize: '18px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><FaChevronRight /></button>
        </div>
      </div>

      <div ref={scrollRef} role="log" aria-live="polite" aria-atomic="false" style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {messages.length === 0 && (
          <div style={{ color: 'var(--text-soft)', fontSize: '14px' }}>
            <p style={{ marginTop: 0 }}>Sóc el teu copilot. Puc crear i editar drills, cercar-los, i fer exemples parlats — selecciona drills a la graella per parlar-ne.</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {suggestions.map((s, i) => (
                <button key={i} onClick={() => send(s)} aria-label={`Suggeriment: ${s}`} style={{ textAlign: 'left', padding: '10px 14px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', cursor: 'pointer', fontSize: '13px', color: 'var(--text)' }}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{ alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '90%' }}>
            <div style={{
              padding: '10px 14px', borderRadius: 'var(--r-lg)', fontSize: '14px', lineHeight: 1.5, whiteSpace: 'pre-wrap', overflowWrap: 'break-word',
              background: m.role === 'user' ? 'var(--brand-1)' : 'var(--surface)',
              color: m.role === 'user' ? '#fff' : 'var(--text)',
              border: m.role === 'user' ? 'none' : '1px solid var(--border)',
            }}>
              {m.text}
              {renderActions(m.actions)}
            </div>
          </div>
        ))}
        {busy && <div style={{ alignSelf: 'flex-start', padding: '10px 14px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', color: 'var(--text-muted)', fontSize: '14px' }}>treballant…</div>}
      </div>

      <div style={{ padding: '12px', paddingBottom: 'calc(12px + env(safe-area-inset-bottom))', borderTop: '1px solid var(--border)', display: 'flex', gap: '8px' }}>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') send(input); }}
          placeholder={selected.length ? 'Demana una acció sobre la selecció…' : 'Demana crear, cercar, traduir…'}
          aria-label="Missatge al copilot"
          disabled={busy}
          style={{ flex: 1, padding: '12px 14px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', fontSize: '14px', color: 'var(--text)' }}
        />
        <button onClick={() => send(input)} disabled={busy || !input.trim()} aria-label="Envia" style={{ padding: '12px 18px', background: 'var(--brand-gradient)', color: '#fff', border: 'none', borderRadius: 'var(--r-pill)', fontWeight: 700, cursor: (busy || !input.trim()) ? 'not-allowed' : 'pointer', opacity: (busy || !input.trim()) ? 0.5 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><FaPaperPlane /></button>
      </div>
    </div>
  );
}

function chip(bg: string, color: string): React.CSSProperties {
  return { display: 'inline-block', padding: '5px 11px', borderRadius: 'var(--r-pill)', fontSize: '12px', fontWeight: 700, background: bg, color, overflowWrap: 'break-word', maxWidth: '100%' };
}
