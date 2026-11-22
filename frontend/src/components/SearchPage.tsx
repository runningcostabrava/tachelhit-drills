import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { FaMicrophone, FaPlay, FaSearch, FaStop } from 'react-icons/fa';
import { api } from '../api';
import type { Drill } from '../types';
import { hasIdentity } from '../config';
import { audioSrc, imatgeSrc } from '../services/audioLocal';
import { cercaLocal } from '../services/cercaLocal';
import { ordena } from '../utils/casaFrase';
import { gap, keepAwake, nowPlaying, say, stop } from '../utils/veu';
import { useDictat } from '../utils/dictat';
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
// la mateixa frase, perquè es compara també per so.
//
// **Primer el telèfon, després el servidor.** En Pablo, amb l'app a la mà: «in this phone the
// offline is not working, I can not search phrase». La cerca només preguntava a `/corpus/search`,
// i sense xarxa no hi havia res a fer —ni amb xarxa dolenta, perquè la petició es penja i la
// pantalla amb ella, i el Render triga mig minut a despertar-se. Ara es cerca de seguida a la
// còpia del telèfon, que és la biblioteca sencera, i quan el servidor respon es posa la seva
// resposta, que és la bona. Sense senyal, la del telèfon es queda, i es diu.
//
// I quan no hi és, no es diu «cap resultat» i avall: es diu que ningú no ho ha dit encara, i
// s'ofereixen les dues sortides que el projecte té — demanar-la (algú que ho sàpiga la gravarà)
// o dir-la tu mateix.
//
// **I es pot buscar parlant.** L'amo: «vull que la búsqueda al mòbil funcioni amb un micròfon».
// És el reconeixedor del mateix telèfon, el mateix que fa el dictat de la pantalla de gravar: va
// **sense xarxa**, i per això lliga amb una cerca que ja busca primer a la còpia del telèfon.
// Dicta en CATALÀ —del que busques, no de la llengua—, perquè cap telèfon no sap escriure amazic
// a l'oïda; per trobar una paraula amaziga, escriu-la com vulguis, que la cerca compara pel so.

export default function SearchPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const q = params.get('q') || '';
  const [text, setText] = useState(q);
  const [rows, setRows] = useState<Drill[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState<Drill | null>(null);
  /** El que es veu ve de la còpia del telèfon i el servidor encara no ha dit la seva. */
  const [delTelefon, setDelTelefon] = useState(false);
  const box = useRef<HTMLInputElement | null>(null);
  /** Quina cerca és la vigent: una resposta que arriba tard no ha de trepitjar la nova. */
  const torn = useRef(0);

  useEffect(() => { document.title = 'Cerca · Tamazight'; box.current?.focus(); }, []);
  useEffect(() => { setText(q); }, [q]);

  // Buscar parlant: el micròfon de la caixa de cerca. El dictat viu a `utils/dictat.ts`
  // perquè la caixa de la portada també el té.
  const { dictant, dicta } = useDictat((dit) => setParams({ q: dit }));

  /** Quina frase sona ara de la seqüència, i quina seqüència manda. */
  const [sonant, setSonant] = useState<number | null>(null);
  const seq = useRef(0);

  const aturaVeu = useCallback(() => {
    seq.current++;
    stop();
    setSonant(null);
    keepAwake(false);
    nowPlaying(null);
  }, []);

  useEffect(() => () => aturaVeu(), [aturaVeu]);

  /**
   * Escoltar-les totes, en l'ordre que es veuen.
   *
   * En Pablo: «I should be able to reproduce in that order all the results of the search». Sona
   * pel reproductor de tota l'app —un sol element declarat al sistema— i per `audioSrc`, de
   * manera que surt del fitxer del telèfon quan ja és baixat: també va sense xarxa i no calla
   * quan s'apaga la pantalla. Les que encara no tenen veu se salten, i es diu quantes són.
   */
  const escoltaTotes = useCallback(async () => {
    const ambVeu = (rows || []).filter((d) => (d.audio_url || '').trim());
    if (!ambVeu.length) { toast.info('Cap d’aquestes frases no té veu encara.'); return; }
    const mudes = (rows || []).length - ambVeu.length;
    if (mudes) toast.info(`${mudes} ${mudes === 1 ? 'frase no té veu i se salta' : 'frases no tenen veu i se salten'}.`);
    const meu = ++seq.current;
    keepAwake(true);
    nowPlaying({ title: `Cerca: ${q}`, artist: 'Tamazight', onPause: aturaVeu });
    for (const d of ambVeu) {
      if (seq.current !== meu) return;
      setSonant(d.id);
      await say(audioSrc(d.audio_url as string));
      if (seq.current !== meu) return;
      await gap(350);
    }
    if (seq.current !== meu) return;
    setSonant(null); keepAwake(false); nowPlaying(null);
  }, [rows, q, aturaVeu]);

  /** Una sola frase: atura la seqüència, perquè dues veus alhora no s'entenen. */
  const sonaUna = useCallback((d: Drill) => {
    seq.current++;
    keepAwake(false); nowPlaying(null);
    setSonant(d.id);
    void say(audioSrc(d.audio_url as string)).then(() => setSonant((ara) => (ara === d.id ? null : ara)));
  }, []);

  const look = useCallback((term: string) => {
    seq.current++; stop(); setSonant(null);
    const net = term.trim();
    if (!net) { setRows(null); setDelTelefon(false); return; }
    const meu = ++torn.current;
    let servidorJaHaDit = false;
    setBusy(true);
    setDelTelefon(false);

    // La còpia del telèfon: respon a l'instant i va sense xarxa.
    cercaLocal(net).then((locals) => {
      if (torn.current !== meu || servidorJaHaDit) return;
      setRows(locals); setDelTelefon(true); setBusy(false);
    }).catch(() => { /* sense còpia, s'espera el servidor */ });

    api.corpusSearch({ q: net, limit: 40 })
      .then((r) => {
        if (torn.current !== meu) return;
        servidorJaHaDit = true;
        // El servidor les torna per data. Es reordenen aquí amb la mateixa regla que la còpia del
        // telèfon, perquè l'ordre que es veu no depengui d'on ha vingut la resposta.
        setRows(ordena(r, net)); setDelTelefon(false);
      })
      .catch((e) => {
        if (torn.current !== meu) return;
        // Sense servidor es queda el que ha trobat el telèfon; només es crida si tampoc hi havia còpia.
        setRows((prev) => {
          if (prev === null) toast.error(whyItFailed(e, 'No s’ha pogut cercar'));
          return prev ?? [];
        });
      })
      .finally(() => { if (torn.current === meu) setBusy(false); });
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
        «aɣrum» i «ⴰⵖⵔⵓⵎ» troben la mateixa frase. O prem el micròfon i digue-ho.
      </p>

      <form onSubmit={submit} style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
        <input ref={box} value={text} onChange={(e) => setText(e.target.value)}
               placeholder={dictant ? 'Parla…' : 'pa, aɣrum, «tinc gana»…'} aria-label="Què busques"
               autoCapitalize="off" autoCorrect="off" spellCheck={false}
               style={{ flex: 1, minWidth: 0, padding: '11px 14px', fontSize: 15.5, borderRadius: 'var(--r-pill)', border: `1px solid ${dictant ? 'var(--rose, #b5435a)' : 'var(--border)'}`, background: 'var(--surface)', color: 'var(--text)', fontFamily: 'inherit' }} />
        <button type="button" onClick={() => dicta(setText)}
                  aria-label={dictant ? 'Prou, busca-ho' : 'Digues què busques'}
                  title={dictant ? 'Prou, busca-ho' : 'Digues què busques'}
                  style={{ padding: '11px 16px', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: dictant ? 'var(--rose, #b5435a)' : 'var(--surface)', color: dictant ? '#fff' : 'var(--brand-1)', cursor: 'pointer', fontFamily: 'inherit', flexShrink: 0 }}>
          <FaMicrophone size={15} />
        </button>
        <button type="submit" aria-label="Cerca"
                style={{ padding: '11px 18px', borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit' }}>
          <FaSearch size={13} />
        </button>
      </form>
      {dictant && (
        <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '-10px 0 14px' }}>
          T’escolto. Torna a prémer el micròfon quan hagis acabat.
        </p>
      )}

      {busy && <p style={{ color: 'var(--text-soft)', fontSize: 14 }}>Buscant…</p>}

      {!busy && rows && rows.length > 0 && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '0 0 8px' }}>
            <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: 0, flex: 1, minWidth: 0 }}>
              {rows.length === 40 ? 'Les primeres 40' : `${rows.length} ${rows.length === 1 ? 'frase' : 'frases'}`}
              , les més semblants primer
              {delTelefon && ' · de la còpia del telèfon'}
            </p>
            <button onClick={sonant === null ? escoltaTotes : aturaVeu}
                    aria-label={sonant === null ? 'Escolta-les totes, en aquest ordre' : 'Atura'}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '8px 14px', borderRadius: 'var(--r-pill)', border: 'none', background: sonant === null ? 'var(--brand-gradient)' : 'var(--rose, #b5435a)', color: '#fff', fontWeight: 800, fontSize: 12.5, cursor: 'pointer', fontFamily: 'inherit', flexShrink: 0 }}>
              {sonant === null ? <><FaPlay size={10} /> Escolta-les totes</> : <><FaStop size={10} /> Atura</>}
            </button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {rows.map((d) => (
              <div key={d.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', borderRadius: 'var(--r-lg)', background: 'var(--surface)', border: sonant === d.id ? '2px solid var(--brand-1)' : '1px solid var(--border)' }}>
                {d.image_url && (
                  <img src={imatgeSrc(d.image_url, 120)} alt="" loading="lazy"
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
                  <button onClick={() => sonaUna(d)}
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
