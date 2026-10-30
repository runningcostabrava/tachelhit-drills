import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaChevronLeft, FaExternalLinkAlt, FaPlay, FaRedo } from 'react-icons/fa';
import { api, type ListenItem } from '../api';
import { audioSrc } from '../services/audioLocal';
import { say, stop } from '../utils/veu';
import { GlossWords, type Gloss } from './WordGloss';
import Frase from './Frase';

// Escoltar i triar: un exercici d'entendre, no de llegir (#333).
//
// Tot el que teníem entrena a llegir amazic. Res no entrenava a entendre'l quan algú el diu, que
// és el que al final serveix per parlar amb algú.
//
// Dues coses que decideixen si això serveix o no:
//
//   - **No es veu res abans de triar.** Si la frase és a la pantalla, l'exercici torna a ser de
//     llegir. Per això el text, el nom de qui parla i la font surten NOMÉS després.
//   - **Es pot tornar a sentir tantes vegades com calgui**, abans i després. No és un examen de
//     memòria: és aprendre a distingir on acaba una paraula i on comença l'altra.
//
// I funciona sense transcripció, que és el que el fa possible avui: les 644 línies que tenen veu
// i cap paraula amaziga escrita (#320) no serveixen per llegir i serveixen exactament per a això.

export default function ListenPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<ListenItem[] | null>(null);
  const [n, setN] = useState(0);
  const [triat, setTriat] = useState<number | null>(null);
  const [encerts, setEncerts] = useState(0);

  const carrega = useCallback(() => {
    setItems(null); setN(0); setTriat(null); setEncerts(0);
    api.listenSession(10).then((r) => setItems(r.items)).catch(() => setItems([]));
  }, []);

  useEffect(() => { document.title = 'Escolta i tria · Tamazight'; carrega(); }, [carrega]);
  useEffect(() => () => stop(), []);

  const item = items?.[n];
  const sona = () => { if (item) say(audioSrc(item.audio_url)); };

  // Sonar tot sol en arribar a un tall nou: el primer que ha de passar és sentir-lo.
  useEffect(() => {
    if (item) say(audioSrc(item.audio_url));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item?.drill_id]);

  if (!items) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>Carregant…</div>;
  if (!items.length) return (
    <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)', lineHeight: 1.6 }}>
      Encara no hi ha prou talls amb veu i significat per fer-ne un exercici.
    </div>
  );

  if (!item) {
    return (
      <div style={{ padding: '40px 16px', maxWidth: 560, margin: '0 auto', textAlign: 'center' }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24 }}>
          {encerts} de {items.length}
        </h1>
        <p style={{ color: 'var(--text-soft)', lineHeight: 1.6, margin: '6px 0 18px' }}>
          El que compta no és la nota: és quantes vegades has hagut de tornar a sentir el tall.
          Cada vegada que hi tornes, l'orella hi guanya.
        </p>
        <button onClick={carrega} style={primari}><FaRedo size={12} /> Una altra tanda</button>
      </div>
    );
  }

  const despres = item.despres;
  const glosses: Gloss[] = (() => {
    try { const g = JSON.parse(despres.glosses || '[]'); return Array.isArray(g) ? g : []; }
    catch { return []; }
  })();

  return (
    <div style={{ padding: '20px 16px 60px', maxWidth: 620, margin: '0 auto' }}>
      <button onClick={() => navigate('/practice')} style={enrere}><FaChevronLeft /> Pràctica</button>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', margin: '6px 0 2px' }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 23, margin: 0 }}>Escolta i tria</h1>
        <span style={{ fontSize: 13, color: 'var(--text-soft)' }}>{n + 1} / {items.length}</span>
      </div>
      <p style={{ color: 'var(--text-soft)', fontSize: 13.5, margin: '0 0 18px', lineHeight: 1.55 }}>
        Sentiràs una frase. Tria què vol dir. Torna-la a sentir les vegades que vulguis.
      </p>

      <button onClick={sona} style={{ ...primari, width: '100%', justifyContent: 'center', padding: '16px 18px', fontSize: 15 }}>
        <FaPlay size={13} /> Torna-la a sentir
      </button>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 9, margin: '18px 0' }}>
        {item.opcions.map((o, i) => {
          const tria = triat === i;
          const mostra = triat !== null;
          const color = !mostra ? 'var(--border)'
            : o.bona ? '#2e7d32' : (tria ? '#c62828' : 'var(--border)');
          return (
            <button key={i} disabled={mostra} onClick={() => {
              setTriat(i);
              if (o.bona) setEncerts((e) => e + 1);
            }} style={{
              textAlign: 'left', padding: '12px 14px', borderRadius: 'var(--r-lg)',
              border: `1.5px solid ${color}`, background: mostra && o.bona ? 'rgba(46,125,50,0.08)' : 'var(--surface)',
              color: 'var(--text)', fontSize: 15, lineHeight: 1.45, cursor: mostra ? 'default' : 'pointer',
              fontFamily: 'inherit', fontWeight: mostra && o.bona ? 700 : 500,
            }}>{o.text}</button>
          );
        })}
      </div>

      {/* Només després de triar. Si això es veiés abans, l'exercici tornaria a ser de llegir. */}
      {triat !== null && (
        <section style={{ padding: '14px 16px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface-2)' }}>
          {despres.text_tachelhit ? (
            <Frase text={despres.text_tachelhit} size="md" />
          ) : (
            <div style={{ fontSize: 13.5, color: 'var(--saffron-dark, #7A4A12)', fontWeight: 700 }}>
              D'aquesta frase encara no en tenim les paraules escrites: se sent, i no es pot llegir.
            </div>
          )}
          {glosses.length > 0 && <GlossWords words={glosses} size="sm" />}
          <p style={{ margin: '10px 0 0', fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.55 }}>
            {despres.speaker && despres.speaker !== 'Auto Capture' && <>Ho diu <strong>{despres.speaker}</strong>. </>}
            {despres.region && <>De {despres.region}. </>}
            {despres.source_channel && <>Del canal <strong>{despres.source_channel}</strong>. </>}
            {despres.source_url && (
              <a href={despres.source_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--brand-1)', fontWeight: 700 }}>
                mira'n l'original <FaExternalLinkAlt size={9} />
              </a>
            )}
          </p>
          <button onClick={() => { setTriat(null); setN((x) => x + 1); }}
                  style={{ ...primari, marginTop: 12 }}>Següent</button>
        </section>
      )}
    </div>
  );
}

const primari: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 18px',
  borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)',
  color: '#fff', fontWeight: 800, fontSize: 14, cursor: 'pointer', fontFamily: 'inherit',
};
const enrere: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 6, padding: 0, border: 'none',
  background: 'none', color: 'var(--brand-1)', fontWeight: 700, fontSize: 13,
  cursor: 'pointer', fontFamily: 'inherit',
};
