import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { FaMicrophone, FaPlay, FaSearch } from 'react-icons/fa';
import { api } from '../api';
import type { Drill } from '../types';
import { getMediaUrl, hasIdentity, thumb } from '../config';
import { audioSrc } from '../services/audioLocal';
import { toast } from '../toast';
import { whyItFailed } from '../utils/errors';
import RecordAudioModal from './RecordAudioModal';

// Cercar una frase o una paraula, i dir-la si no hi és.
//
// L'amo: «una cosa primordial a l'aplicació hauria de ser buscar una frase o paraula o gravar un
// nou drill». Tenia raó i no hi era: per trobar una frase calia obrir la graella de tota la
// biblioteca i filtrar-hi, i per afegir-ne una, saber on era el creador.
//
// Es busca per les dues llengües i per qualsevol escriptura: «aghrum», «aɣrum» i «ⴰⵖⵔⵓⵎ» troben
// la mateixa frase, perquè el servidor compara també per so.
//
// I quan no hi és, no es diu «cap resultat» i avall: es diu que ningú no ho ha dit encara, i
// s'ofereixen les dues sortides que el projecte té — demanar-la (algú que ho sàpiga la gravarà)
// o dir-la tu mateix.

export default function SearchPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const q = params.get('q') || '';
  const [text, setText] = useState(q);
  const [rows, setRows] = useState<Drill[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState<Drill | null>(null);
  const box = useRef<HTMLInputElement | null>(null);

  useEffect(() => { document.title = 'Cerca · Tamazight'; box.current?.focus(); }, []);
  useEffect(() => { setText(q); }, [q]);

  const look = useCallback((term: string) => {
    if (!term.trim()) { setRows(null); return; }
    setBusy(true);
    api.corpusSearch({ q: term.trim(), limit: 40 })
      .then(setRows)
      .catch((e) => { setRows([]); toast.error(whyItFailed(e, 'No s’ha pogut cercar')); })
      .finally(() => setBusy(false));
  }, []);

  useEffect(() => { look(q); }, [q, look]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setParams(text.trim() ? { q: text.trim() } : {});
  };

  /** Demana-la: queda a «Posa-hi veu» perquè algú que ho sàpiga dir la gravi. */
  const ask = async () => {
    if (!hasIdentity()) { toast.error('Per demanar-la et cal un nom: fes-te’n un al perfil.'); return; }
    try {
      await api.addPetition(q, null);
      toast.success('Demanada. Sortirà a «Posa-hi veu» perquè algú la digui.');
    } catch (e) { toast.error(whyItFailed(e, 'No s’ha pogut demanar')); }
  };

  /** Digue-la tu: neix la frase i s'obre la gravadora de seguida. */
  const sayIt = async () => {
    if (!hasIdentity()) { toast.error('Per gravar et cal un nom: fes-te’n un al perfil.'); return; }
    setBusy(true);
    try {
      const made = await api.createDrill({ text_catalan: q, text_tachelhit: '' });
      setRecording(made);
    } catch (e) { toast.error(whyItFailed(e, 'No s’ha pogut crear la frase')); }
    finally { setBusy(false); }
  };

  return (
    <div style={{ padding: '20px 16px 48px', maxWidth: 760, margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, margin: '0 0 4px' }}>Cerca</h1>
      <p style={{ color: 'var(--text-soft)', fontSize: 14, margin: '0 0 14px', lineHeight: 1.55 }}>
        Una frase o una paraula, en amazic o en català. Tant li fa com l’escriguis: «aghrum»,
        «aɣrum» i «ⴰⵖⵔⵓⵎ» troben la mateixa frase.
      </p>

      <form onSubmit={submit} style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
        <input ref={box} value={text} onChange={(e) => setText(e.target.value)}
               placeholder="pa, aɣrum, «tinc gana»…" aria-label="Què busques"
               autoCapitalize="off" autoCorrect="off" spellCheck={false}
               style={{ flex: 1, minWidth: 0, padding: '11px 14px', fontSize: 15.5, borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit' }} />
        <button type="submit" aria-label="Cerca"
                style={{ padding: '11px 18px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit' }}>
          <FaSearch size={13} />
        </button>
      </form>

      {busy && <p style={{ color: 'var(--text-soft)', fontSize: 14 }}>Buscant…</p>}

      {!busy && rows && rows.length > 0 && (
        <>
          <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '0 0 8px' }}>
            {rows.length === 40 ? 'Les primeres 40' : `${rows.length} ${rows.length === 1 ? 'frase' : 'frases'}`}
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {rows.map((d) => (
              <div key={d.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)' }}>
                {d.image_url && (
                  <img src={thumb(getMediaUrl(d.image_url), 120)} alt="" loading="lazy"
                       style={{ width: 56, height: 56, objectFit: 'cover', borderRadius: 'var(--r-md)', flexShrink: 0 }}
                       onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div lang="shi" style={{ fontWeight: 800, fontSize: 16, color: 'var(--brand-1)', lineHeight: 1.3 }}>{d.text_tachelhit || '—'}</div>
                  <div style={{ fontSize: 13.5, color: 'var(--text-soft)' }}>{d.text_catalan}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
                    {d.speaker || d.author || 'sense nom'}
                    <span style={{ opacity: 0.6 }}>{d.variety ? ` · ${d.variety}` : ''}{d.region ? ` · ${d.region}` : ''}</span>
                    {!d.audio_url && ' · encara sense veu'}
                  </div>
                </div>
                {d.audio_url ? (
                  <button onClick={() => new Audio(audioSrc(d.audio_url as string)).play().catch(() => {})}
                          aria-label="Escolta-la" title="Escolta-la"
                          style={{ width: 36, height: 36, borderRadius: '50%', border: 'none', background: 'var(--brand-gradient)', color: '#fff', cursor: 'pointer', flexShrink: 0 }}>
                    <FaPlay size={11} />
                  </button>
                ) : null}
                <button onClick={() => { if (!hasIdentity()) { toast.error('Per gravar et cal un nom: fes-te’n un al perfil.'); return; } setRecording(d); }}
                        aria-label="Posa-hi la teva veu" title="Posa-hi la teva veu"
                        style={{ width: 36, height: 36, borderRadius: '50%', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--brand-1)', cursor: 'pointer', flexShrink: 0 }}>
                  <FaMicrophone size={12} />
                </button>
              </div>
            ))}
          </div>
        </>
      )}

      {!busy && q && rows && rows.length === 0 && (
        <div style={{ padding: '16px 18px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)' }}>
          <strong style={{ fontSize: 15.5 }}>Això encara no ho ha dit ningú</strong>
          <p style={{ fontSize: 13.5, color: 'var(--text-soft)', lineHeight: 1.6, margin: '4px 0 12px' }}>
            No és un error de la cerca: la biblioteca només té el que la gent hi ha posat. Pots
            demanar-ho —algú que ho sàpiga dir ho gravarà— o dir-ho tu mateix ara.
          </p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button onClick={ask} style={{ padding: '9px 16px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontWeight: 700, fontSize: 13.5, cursor: 'pointer', fontFamily: 'inherit' }}>
              Demana-la
            </button>
            <button onClick={sayIt} disabled={busy}
                    style={{ padding: '9px 16px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 13.5, cursor: 'pointer', fontFamily: 'inherit' }}>
              <FaMicrophone size={11} /> Digue-la tu
            </button>
            <button onClick={() => navigate('/drills')}
                    style={{ padding: '9px 16px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-soft)', fontWeight: 700, fontSize: 13.5, cursor: 'pointer', fontFamily: 'inherit' }}>
              Mira tota la biblioteca
            </button>
          </div>
        </div>
      )}

      {recording && (
        <RecordAudioModal drill={recording} onClose={() => setRecording(null)}
                          onSaved={() => { setRecording(null); toast.success('Gravada. Gràcies per la teva veu.'); look(q); }} />
      )}
    </div>
  );
}
