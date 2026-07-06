import { useEffect, useRef, useState } from 'react';
import { api, type TransliterationForms } from '../api';

// "Write the way your thumbs know, see your word whole." Takes what the user
// typed (demotic phone-Latin) and shows, in the background, its Tifinagh and
// clean academic-Latin faces — suggestions to accept, never overwriting gold.
export default function TransliterationPreview({
  text,
  onUseTifinagh,
  onUseLatin,
}: {
  text: string;
  onUseTifinagh?: (tifinagh: string) => void;
  onUseLatin?: (clean: string) => void;
}) {
  const [forms, setForms] = useState<TransliterationForms | null>(null);
  const timer = useRef<number | null>(null);
  const seq = useRef(0);

  useEffect(() => {
    const t = text.trim();
    if (timer.current) window.clearTimeout(timer.current);
    if (!t) { setForms(null); return; }
    const mine = ++seq.current;
    timer.current = window.setTimeout(() => {
      api.transliterate(t)
        .then((f) => { if (mine === seq.current) setForms(f); })
        .catch(() => { /* transient — keep last */ });
    }, 300);
    return () => { if (timer.current) window.clearTimeout(timer.current); };
  }, [text]);

  if (!forms || (!forms.tifinagh && !forms.clean_latin)) return null;

  return (
    <div style={{ marginTop: '8px', padding: '12px 14px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)' }}>
      <div style={{ fontSize: '10.5px', fontWeight: 800, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '8px' }}>
        Altres formes (automàtic)
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', width: '58px', flexShrink: 0 }}>Tifinag</span>
        <span style={{ fontFamily: 'var(--font-tifinagh)', fontSize: '22px', color: 'var(--brand-1)', flex: 1, minWidth: 0, wordBreak: 'break-word' }}>{forms.tifinagh || '—'}</span>
        {onUseTifinagh && forms.tifinagh && (
          <button type="button" onClick={() => onUseTifinagh(forms.tifinagh)} style={useBtn}>Fes servir</button>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginTop: '8px' }}>
        <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', width: '58px', flexShrink: 0 }}>Llatí net</span>
        <span style={{ fontSize: '15px', color: 'var(--text)', flex: 1, minWidth: 0, wordBreak: 'break-word' }}>{forms.clean_latin || '—'}</span>
        {onUseLatin && forms.clean_latin && (
          <button type="button" onClick={() => onUseLatin(forms.clean_latin)} style={useBtn}>Fes servir</button>
        )}
      </div>

      <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--text-muted)' }}>
        clau fonèmica: <code style={{ fontSize: '11px' }}>{forms.key || '—'}</code>
      </div>
    </div>
  );
}

const useBtn: React.CSSProperties = {
  flexShrink: 0, padding: '4px 10px', fontSize: '12px', fontWeight: 700, cursor: 'pointer',
  background: 'var(--surface)', color: 'var(--brand-1)', border: '1px solid var(--brand-1)', borderRadius: 'var(--r-pill)',
};
