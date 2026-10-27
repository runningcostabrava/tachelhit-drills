import { useMemo, useState } from 'react';
import { FaCheck, FaTimes, FaRedo, FaRegLightbulb } from 'react-icons/fa';
import type { MethodExercise, MethodExerciseItem } from '../api';

/**
 * Els exercicis del llibre, fets de debò (#380).
 *
 * Al llibre són una llista amb la resposta impresa a sota: qui els «fa» en paper ja l'ha vista.
 * Aquí no. L'amo: «podem incorporar els exercicis de forma dinàmica, utilitzant el fet que
 * estem en una web i podem fer coses intel·ligents».
 *
 * Tres maneres de fer-los, i la mena de l'exercici tria quina:
 *
 * · **ordena** — les paraules de la resposta surten desordenades i es toquen en ordre. És
 *   l'únic exercici del llibre que en paper no es pot fer sense escriure.
 * · **completa** i **tria** — la frase porta un buit i s'hi escriu. Es compara pel SO, no
 *   lletra per lletra: qui escriu `gh` on la resposta diu `ɣ` ha encertat, i dir-li que no
 *   seria ensenyar-li una falsedat (#364).
 * · la resta — es pensa i es destapa. Destapar no és fer trampa si abans has provat.
 *
 * Els ítems que el llibre deixa **sense resposta** es diuen com el que són. El llibre els posa
 * en blanc perquè els faci qui aprèn; inventar-los una solució seria pitjor que no tenir-ne.
 */

/** Igual per comparar: sense diacrítics, sense puntuació i sense majúscules.
 *
 *  La mateixa regla que al transliterador: `ɣ`/`gh`, `c`/`ch` i `ɛ`/`e` són la mateixa lletra
 *  escrita de dues maneres, i el llibre d'on surten aquests exercicis fa servir la segona.
 *  Comparar-les com si fossin diferents suspendria qui ho ha fet bé.
 */
function pla(s: string): string {
  return (s || '')
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/ɣ/g, 'gh').replace(/ġ/g, 'gh')
    .replace(/ɛ/g, 'e').replace(/ʷ/g, 'w').replace(/č|c/g, 'ch')
    .replace(/[^a-z0-9]/g, '');
}

const MENES: Record<string, string> = {
  completa: 'Omple el buit',
  tria: 'Tria la paraula',
  ordena: 'Posa-ho en ordre',
  pregunta: 'Fes la pregunta',
  respon: 'Respon',
  pronom: 'Canvia-ho per un pronom',
  analitza: 'Mira el verb',
};

function Tif({ children }: { children?: string | null }) {
  if (!children) return null;
  return <div lang="shi" style={{ fontFamily: 'var(--font-tifinagh, inherit)', fontSize: 18, color: 'var(--text)', lineHeight: 1.4 }}>{children}</div>;
}

/** Les paraules d'una frase, barrejades, per tornar-les a posar en ordre. */
function Ordena({ item }: { item: MethodExerciseItem }) {
  const bones = useMemo(() => (item.resposta?.shi || '').split(/\s+/).filter(Boolean), [item]);
  const [triades, setTriades] = useState<number[]>([]);
  // La barreja es fa una vegada: si es refés a cada pintada, les paraules ballarien pel camí.
  const ordre = useMemo(() => {
    const idx = bones.map((_, i) => i);
    for (let i = idx.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [idx[i], idx[j]] = [idx[j], idx[i]];
    }
    return idx;
  }, [bones]);
  const fet = triades.length === bones.length;
  const be = fet && triades.every((v, i) => bones[v] === bones[i]);

  return (
    <div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
        {ordre.filter((i) => !triades.includes(i)).map((i) => (
          <button key={i} onClick={() => setTriades([...triades, i])}
                  style={{ padding: '6px 11px', borderRadius: 'var(--r-pill)', cursor: 'pointer',
                           border: '1px solid var(--border)', background: 'var(--surface-2)',
                           color: 'var(--brand-1)', fontFamily: 'inherit', fontWeight: 700, fontSize: 14 }}>
            <span lang="shi">{bones[i]}</span>
          </button>
        ))}
      </div>
      <div style={{ minHeight: 34, display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center',
                    padding: '7px 9px', borderRadius: 'var(--r-md)', border: '1px dashed var(--border)',
                    background: 'var(--surface)' }}>
        {triades.length === 0 && <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>Toca les paraules en l'ordre que toca</span>}
        {triades.map((i, k) => (
          <button key={k} onClick={() => setTriades(triades.slice(0, k))}
                  style={{ padding: '4px 9px', borderRadius: 'var(--r-pill)', cursor: 'pointer',
                           border: 'none', background: 'var(--brand-gradient-soft)',
                           color: 'var(--text)', fontFamily: 'inherit', fontWeight: 700, fontSize: 14 }}>
            <span lang="shi">{bones[i]}</span>
          </button>
        ))}
      </div>
      {fet && (
        <div style={{ marginTop: 7, fontSize: 13.5, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6,
                      color: be ? 'var(--emerald)' : 'var(--rose)' }}>
          {be ? <><FaCheck size={12} /> Ben posat.</>
              : <><FaTimes size={12} /> Encara no. <button onClick={() => setTriades([])}
                    style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: 'inherit',
                             textDecoration: 'underline', fontFamily: 'inherit', fontWeight: 600 }}>torna-hi</button></>}
        </div>
      )}
    </div>
  );
}

/** Una frase amb un buit, i el que hi va escrit. */
function Omple({ item }: { item: MethodExerciseItem }) {
  const [escrit, setEscrit] = useState('');
  const [mirat, setMirat] = useState(false);
  const be = pla(escrit) !== '' && pla(item.resposta?.shi || '').includes(pla(escrit));
  const parts = (item.pregunta.shi || '').split('...');

  return (
    <div>
      <div lang="shi" style={{ fontSize: 16, fontWeight: 600, color: 'var(--brand-1)', display: 'flex',
                               flexWrap: 'wrap', alignItems: 'center', gap: 4 }}>
        <span>{parts[0]}</span>
        {parts.length > 1 && (
          <input value={escrit} onChange={(e) => { setEscrit(e.target.value); setMirat(false); }}
                 aria-label="el que hi falta"
                 style={{ width: `${Math.max(5, escrit.length + 2)}ch`, padding: '2px 7px', fontSize: 15,
                          fontFamily: 'inherit', fontWeight: 700, color: 'var(--text)',
                          borderRadius: 'var(--r-sm)', border: `1.5px solid ${escrit && be ? 'var(--emerald)' : 'var(--border)'}`,
                          background: 'var(--surface)' }} />
        )}
        <span>{parts.slice(1).join('...')}</span>
      </div>
      {escrit && (
        <div style={{ marginTop: 5, fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6,
                      color: be ? 'var(--emerald)' : 'var(--text-muted)' }}>
          {be ? <><FaCheck size={11} /> Això és.</> : <>Encara no hi és.</>}
        </div>
      )}
      <Solucio item={item} obert={mirat} obre={() => setMirat(true)} />
    </div>
  );
}

/** La resposta del llibre, destapada quan qui fa l'exercici ho demana. */
function Solucio({ item, obert, obre }: { item: MethodExerciseItem; obert: boolean; obre: () => void }) {
  if (item.sense_solucio || !item.resposta) {
    return (
      <div style={{ marginTop: 6, fontSize: 12.5, color: 'var(--text-muted)' }}>
        El llibre no en dona la resposta: aquest el deixa per fer.
      </div>
    );
  }
  if (!obert) {
    return (
      <button onClick={obre}
              style={{ marginTop: 6, background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                       color: 'var(--brand-1)', fontFamily: 'inherit', fontSize: 13, fontWeight: 600,
                       display: 'flex', alignItems: 'center', gap: 5 }}>
        <FaRegLightbulb size={12} /> Mira la resposta
      </button>
    );
  }
  return (
    <div style={{ marginTop: 7, padding: '7px 10px', borderRadius: 'var(--r-md)',
                  background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
      <Tif>{item.resposta.tif}</Tif>
      <div lang="shi" style={{ fontSize: 15, fontWeight: 700, color: 'var(--brand-1)' }}>{item.resposta.shi}</div>
      {item.resposta.ca && <div style={{ fontSize: 13.5, color: 'var(--text-soft)' }}>{item.resposta.ca}</div>}
    </div>
  );
}

function Item({ item, kind }: { item: MethodExerciseItem; kind: string }) {
  const [mirat, setMirat] = useState(false);
  const teBuit = (item.pregunta.shi || '').includes('...');

  return (
    <li style={{ padding: '11px 0', borderTop: '1px solid var(--border)' }}>
      {kind === 'ordena' && item.resposta ? (
        <>
          <Tif>{item.pregunta.tif}</Tif>
          <div lang="shi" style={{ fontSize: 14.5, color: 'var(--text-soft)', marginBottom: 8 }}>{item.pregunta.shi}</div>
          <Ordena item={item} />
        </>
      ) : teBuit ? (
        <Omple item={item} />
      ) : (
        <>
          <Tif>{item.pregunta.tif}</Tif>
          <div lang="shi" style={{ fontSize: 16, fontWeight: 600, color: 'var(--brand-1)' }}>{item.pregunta.shi}</div>
          <Solucio item={item} obert={mirat} obre={() => setMirat(true)} />
        </>
      )}
    </li>
  );
}

export default function MethodExercises({ exercises }: { exercises: MethodExercise[] }) {
  const [obert, setObert] = useState<string | null>(exercises[0]?.id ?? null);
  if (!exercises?.length) return null;
  const font = exercises[0]?.font;

  return (
    <section style={{ marginBottom: 26 }}>
      <div style={{ paddingTop: 12, borderTop: '1px solid var(--border)', marginBottom: 10 }}>
        <h2 style={{ margin: 0, fontFamily: 'var(--font-display)', fontSize: 19, color: 'var(--text)' }}>
          Fes els exercicis del llibre
        </h2>
        {font && (
          <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '4px 0 0', lineHeight: 1.5 }}>
            De <i>{font.obra}</i>, de {font.autor} ({font.any}). {font.nota}
          </p>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {exercises.map((e) => {
          const ample = obert === e.id;
          const amb = e.items.filter((i) => i.resposta).length;
          return (
            <div key={e.id} style={{ border: '1px solid var(--border)', borderRadius: 'var(--r-lg)',
                                     background: 'var(--surface)', overflow: 'hidden' }}>
              <button onClick={() => setObert(ample ? null : e.id)}
                      style={{ width: '100%', textAlign: 'left', padding: '12px 14px', cursor: 'pointer',
                               border: 'none', background: ample ? 'var(--surface-2)' : 'transparent',
                               fontFamily: 'inherit', color: 'var(--text)' }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 11, fontWeight: 800, letterSpacing: '.05em', textTransform: 'uppercase',
                                 color: 'var(--brand-1)', background: 'var(--brand-gradient-soft)',
                                 borderRadius: 'var(--r-pill)', padding: '2px 8px' }}>
                    {MENES[e.kind] || e.kind}
                  </span>
                  <span style={{ fontWeight: 600, fontSize: 14.5, minWidth: 0 }}>{e.consigna}</span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 3 }}>
                  {e.items.length} {e.items.length === 1 ? 'frase' : 'frases'}
                  {amb < e.items.length && ` · ${e.items.length - amb} sense resposta al llibre`}
                </div>
              </button>

              {ample && (
                <div style={{ padding: '0 14px 12px' }}>
                  {e.model && (
                    <div style={{ padding: '9px 11px', margin: '2px 0 4px', borderRadius: 'var(--r-md)',
                                  background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
                      <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '.05em',
                                    textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 3 }}>com es fa</div>
                      <div lang="shi" style={{ fontSize: 14.5, color: 'var(--text-soft)' }}>{e.model.pregunta.shi}</div>
                      <div lang="shi" style={{ fontSize: 15, fontWeight: 700, color: 'var(--brand-1)' }}>→ {e.model.resposta.shi}</div>
                    </div>
                  )}
                  <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                    {e.items.map((it, k) => <Item key={k} item={it} kind={e.kind} />)}
                  </ul>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '10px 0 0', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <FaRedo size={10} /> Consigna del llibre: «{e.consigna_fr}»
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
