import { useState } from 'react';
import { FaCheck, FaPlay, FaRedo, FaTimes } from 'react-icons/fa';
import type { Exercici } from '../api';
import AmbSo from './AmbSo';
import { audioSrc } from '../services/audioLocal';
import Frase from './Frase';

// «Fes-ho tu»: els exercicis que pregunten LA PEÇA de la unitat (#428).
//
// Les preguntes que ja hi havia comproven que reconeixes una frase —«com es diu X?»—, i això no
// és el que la unitat ensenya. A «possessius», el que s'ha d'aprendre és que la casa d'ell no es
// diu com la casa teva.
//
// Les frases són de la biblioteca i la resposta és la que va dir qui la va dir. Es corregeix
// **pel so**: qui escriu «gh» on la resposta diu «ɣ» ha encertat, perquè són la mateixa lletra
// escrita per dues mans (#364), i dir-li que no seria ensenyar-li una falsedat.

/** Igual per comparar: la mateixa regla del transliterador, i la mateixa que fan servir els
 *  exercicis del llibre. */
function pla(s: string): string {
  return (s || '')
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/ɣ/g, 'gh').replace(/ġ/g, 'gh')
    .replace(/ɛ/g, 'e').replace(/ʷ/g, 'w').replace(/č|c/g, 'ch')
    .replace(/[^a-z0-9]/g, '');
}

/** L'enllaç del vídeo, obert al segon on surt la taula: qui ho vulgui comprovar no ha de buscar
 *  deu minuts. Sense segon, l'enllaç de sempre. */
function minut(url: string, segon?: number | null): string {
  if (!segon) return url;
  return url + (url.includes('?') ? '&' : '?') + 't=' + Math.max(0, Math.floor(segon));
}

export default function ExercicisDeLaUnitat({ exercicis }: { exercicis?: Exercici[] | null }) {
  if (!exercicis || exercicis.length === 0) return null;
  return (
    <div>
      <h2 style={{ fontSize: 18, margin: '0 0 4px' }}>Fes-ho tu</h2>
      <p style={{ margin: '0 0 12px', fontSize: 13.5, color: 'var(--text-soft)', lineHeight: 1.55 }}>
        El tros que aquesta unitat ensenya, tapat. Quan la frase és de la biblioteca, la resposta
        és la que va dir qui la va dir; quan surt d'una classe de gramàtica, ho diu a sota.
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* La clau és `id` i no `drill_id`: els exercicis de l'estat d'annexió no surten de cap
            frase —es fan amb una taula de formes— i tots tindrien `drill_id` buit. */}
        {exercicis.map((e) => <Un key={e.id} e={e} />)}
      </div>
    </div>
  );
}

function Un({ e }: { e: Exercici }) {
  const [dit, setDit] = useState('');
  const [tria, setTria] = useState<string | null>(null);
  const [mirat, setMirat] = useState(false);

  const resposta = tria ?? dit;
  const encertat = mirat && pla(resposta) === pla(e.resposta);
  const toca = () => { if (e.audio_url) new Audio(audioSrc(e.audio_url)).play().catch(() => {}); };

  return (
    <section style={{ padding: '14px 16px', borderRadius: 'var(--r-xl)', border: `1px solid ${mirat ? (encertat ? 'var(--emerald)' : 'var(--rose)') : 'var(--border)'}`, background: 'var(--surface)' }}>
      <div style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 6 }}>{e.pregunta}</div>

      <Frase text={e.shi} size="md" />
      <div style={{ fontSize: 13.5, color: 'var(--text-soft)', marginTop: 2 }}>{e.ca}</div>

      {e.opcions.length > 0 ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
          {e.opcions.map((o) => {
            const esBona = mirat && pla(o) === pla(e.resposta);
            const triada = tria === o;
            return (
              <button key={o} disabled={mirat}
                      onClick={() => { setTria(o); setMirat(true); }}
                      style={{
                        padding: '10px 16px', minHeight: 44, borderRadius: 'var(--r-pill)', cursor: mirat ? 'default' : 'pointer',
                        fontFamily: 'inherit', fontWeight: 700, fontSize: 14,
                        border: `1px solid ${esBona ? 'var(--emerald)' : mirat && triada ? 'var(--rose)' : 'var(--border)'}`,
                        background: esBona ? 'var(--emerald-soft)' : mirat && triada ? 'var(--rose-soft)' : 'var(--surface-2)',
                        color: 'var(--text)',
                      }}>
                {o}
              </button>
            );
          })}
        </div>
      ) : (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
          <input value={dit} onChange={(ev) => setDit(ev.target.value)} disabled={mirat}
                 onKeyDown={(ev) => { if (ev.key === 'Enter' && dit.trim()) setMirat(true); }}
                 placeholder={e.que} aria-label={e.que}
                 style={{ flex: '1 1 180px', minWidth: 0, padding: '10px 12px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', background: 'var(--surface-2)', color: 'var(--text)', fontSize: 16, fontFamily: 'inherit' }} />
          <button onClick={() => setMirat(true)} disabled={mirat || !dit.trim()}
                  style={{ padding: '10px 18px', minHeight: 44, borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 14, cursor: mirat || !dit.trim() ? 'default' : 'pointer', fontFamily: 'inherit', opacity: mirat || !dit.trim() ? 0.6 : 1 }}>
            Mira-ho
          </button>
        </div>
      )}

      {!mirat && (
        <p style={{ margin: '8px 0 0', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{e.ajuda}</p>
      )}

      {mirat && (
        <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 10 }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 800, fontSize: 14, color: encertat ? 'var(--emerald)' : 'var(--rose)' }}>
            {encertat ? <><FaCheck size={12} /> Sí</> : <><FaTimes size={12} /> Era «{e.resposta}»</>}
          </span>
          {/* Qui ho diu, sempre: la frase és d'algú. */}
          {e.audio_url && (
            <AmbSo url={e.audio_url}><button onClick={toca} style={botonet}>
              <FaPlay size={10} /> Escolta-la{e.speaker ? ` · ${e.speaker}` : ''}{e.region ? ` · ${e.region}` : ''}
            </button></AmbSo>
          )}
          <button onClick={() => { setMirat(false); setTria(null); setDit(''); }} style={botonet}>
            <FaRedo size={10} /> Torna-hi
          </button>
        </div>
      )}

      {/* El crèdit, sempre i encertis o no: aquestes formes són d'una classe d'algú, i el minut
          hi va perquè qui vulgui les pugui tornar a veure escrites a la pantalla. */}
      {e.font?.autor && (
        <p style={{ margin: '8px 0 0', fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.5 }}>
          {e.font.obra ? `${e.font.obra} · ` : ''}{e.font.autor}
          {e.font.url && (
            <> · <a href={minut(e.font.url, e.font.segon)} target="_blank" rel="noreferrer"
                    style={{ color: 'var(--brand-1)' }}>mira-ho al vídeo</a></>
          )}
        </p>
      )}
    </section>
  );
}

const botonet: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 14px', minHeight: 40,
  borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)',
  color: 'var(--brand-1)', fontWeight: 700, fontSize: 12.5, cursor: 'pointer', fontFamily: 'inherit',
};
