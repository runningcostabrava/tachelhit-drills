import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaMicrophone, FaVolumeUp } from 'react-icons/fa';
import { api, type Abecedari, type GrupParelles, type Lletra, type MotDeLletra } from '../api';
import { getMediaUrl } from '../config';
import Frase from './Frase';

// Els sons i l'escriptura: una secció pròpia (#368).
//
// El capítol de la Gramàtica es diu «Sons i escriptura» i de l'escriptura no en deia res:
// pintava tifinag a cada targeta i donava per fet que qui mirava ja sabia què estava mirant.
// Aquí es diu què és aquesta escriptura, i cada lletra s'obre i SONA —amb una paraula de la
// biblioteca dita per algú, mai amb una veu de màquina (#288).
//
// La lletra que no sona enlloc hi surt igual i ho diu. De les paraules soles gravades, cap no
// porta ḍ, ḥ, ɛ, ṛ, ɣ, ṣ, ṭ ni ẓ (#302): això no s'amaga dins d'una xifra, es deixa a la vista
// lletra per lletra, que és el que converteix el forat en una petició concreta.

/** Fer sonar el tros d'una gravació on es diu una paraula. Cap fitxer de so nou: es busca
 *  el minut i se para al final de la paraula. */
function useTall() {
  const audio = useRef<HTMLAudioElement | null>(null);
  const fins = useRef<number | null>(null);
  const [sonant, setSonant] = useState<string | null>(null);

  const toca = useCallback(async (mot: MotDeLletra, id?: string) => {
    if (!mot.audio_url) return;
    audio.current?.pause();
    const a = new Audio(getMediaUrl(mot.audio_url));
    audio.current = a;
    fins.current = mot.end + 0.08;        // un alè més enllà, perquè no quedi tallada
    a.currentTime = Math.max(0, mot.start - 0.04);
    a.ontimeupdate = () => { if (fins.current != null && a.currentTime >= fins.current) { a.pause(); setSonant(null); } };
    a.onended = () => setSonant(null);
    a.onerror = () => setSonant(null);
    setSonant(id || mot.key);
    await a.play().catch(() => setSonant(null));
  }, []);

  useEffect(() => () => audio.current?.pause(), []);
  return { toca, sonant };
}

const ON = { inici: 'al començament', mig: 'al mig', final: 'al final' } as const;

/** Qui diu aquesta paraula, dit sense fer passar una veu per una altra (#288). */
function quiHoDiu(m: MotDeLletra): string {
  const mena = m.veu?.mena;
  if (mena === 'canal') return `veu d’un canal${m.veu?.qui ? `: ${m.veu.qui}` : ''}`;
  if (mena === 'captura') return 'tall d’un vídeo, no sabem de qui';
  if (m.veu?.qui) return m.veu.qui;
  return m.source === 'library' ? 'veu nostra' : 'corpus obert';
}

const MENA: Record<string, string> = {
  vocal: 'vocal',
  emfatica: 'emfàtica',
  labialitzada: 'amb els llavis arrodonits',
  gola: 'feta a la gola',
};

export default function AlfabetPage() {
  const navigate = useNavigate();
  const [abc, setAbc] = useState<Abecedari | null>(null);
  const [tria, setTria] = useState<string | null>(null);
  const [plena, setPlena] = useState<Record<string, Lletra>>({});
  const [parelles, setParelles] = useState<GrupParelles[] | null>(null);
  const { toca, sonant } = useTall();

  useEffect(() => {
    document.title = 'Els sons i l’escriptura · Tamazight';
    api.alfabet().then(setAbc).catch(() => setAbc(null));
    api.alfabetParelles().then((r) => setParelles(r.parelles)).catch(() => setParelles([]));
  }, []);

  // En obrir una lletra es demanen totes les seves paraules: a la graella només n'hi havia dues.
  useEffect(() => {
    if (!tria || plena[tria]) return;
    api.alfabetLletra(tria, 12).then((l) => setPlena((p) => ({ ...p, [tria]: l }))).catch(() => {});
  }, [tria, plena]);

  const oberta = tria ? (plena[tria] || abc?.lletres.find((l) => l.tif === tria) || null) : null;

  if (!abc) {
    return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-soft)' }}>Carregant…</div>;
  }

  return (
    <div style={{ padding: '20px 16px 60px', maxWidth: 820, margin: '0 auto' }}>
      <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, margin: '0 0 6px', lineHeight: 1.2 }}>
        Els sons i l’escriptura
      </h1>
      <p style={{ color: 'var(--text-soft)', fontSize: 13.5, margin: '0 0 18px', lineHeight: 1.55 }}>
        {abc.total} lletres · {abc.amb_so} ja sonen
        {typeof abc.de_casa === 'number' && <> · <strong>{abc.de_casa} les diu algú que coneixem</strong></>}
        {abc.mudes.length > 0 && <> · {abc.mudes.length} encara no sonen</>}
        {abc.nomes_de_fora && abc.nomes_de_fora.length > 0 && (
          <>
            <br />
            Hi ha {abc.nomes_de_fora.length} {abc.nomes_de_fora.length === 1 ? 'lletra' : 'lletres'} que
            només sonen en una veu de fora —un canal, un tall d’un vídeo—: {abc.nomes_de_fora.join(' ')}.
            Per escoltar-les serveixen; per imitar-les, el que falta és algú de casa que les digui.
          </>
        )}
      </p>

      <section style={{ padding: '14px 16px', borderRadius: 'var(--r-xl)', border: '1px solid var(--border)', background: 'var(--surface)', marginBottom: 20 }}>
        <h2 style={{ fontSize: 17, margin: '0 0 8px' }}>{abc.que_es.titol}</h2>
        {abc.que_es.cos.map((p, i) => (
          <p key={i} style={{ margin: '0 0 10px', fontSize: 14.5, lineHeight: 1.65 }}>{p}</p>
        ))}
      </section>

      {/* La graella. Tifinag gran, el llatí a sota: la lletra és el que s'ha d'aprendre a
          reconèixer, i el llatí només hi és per dir-la. */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(64px, 1fr))', gap: 8, marginBottom: 18 }}>
        {abc.lletres.map((l) => {
          const triada = tria === l.tif;
          return (
            <button key={l.tif} onClick={() => setTria(triada ? null : l.tif)}
                    aria-pressed={triada}
                    title={l.sona ? `${l.lat} · ${l.quantes} ${l.quantes === 1 ? 'paraula' : 'paraules'} que sonen` : `${l.lat} · encara no sona`}
                    style={{
                      minHeight: 64, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2,
                      borderRadius: 'var(--r-lg)', cursor: 'pointer', fontFamily: 'inherit',
                      border: `1px solid ${triada ? 'var(--brand-1)' : 'var(--border)'}`,
                      background: triada ? 'var(--brand-gradient-soft)' : 'var(--surface)',
                      color: l.sona ? 'var(--text)' : 'var(--text-muted)',
                    }}>
              <span lang="zgh" style={{ fontSize: 24, fontWeight: 800, lineHeight: 1 }}>{l.tif}</span>
              <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-soft)' }}>{l.lat}</span>
              {/* El número que importa no és quantes vegades sona, sinó quantes la diu algú que
                  coneixem (#302): una lletra que només sona en una veu d'un canal és una petició
                  pendent, no una lletra resolta. */}
              <span style={{ fontSize: 10, color: !l.sona ? 'var(--text-muted)' : l.de_casa ? 'var(--emerald)' : 'var(--amber-strong, #8a6100)' }}>
                {!l.sona ? 'muda' : l.de_casa ? `${l.de_casa} ♪` : 'de fora'}
              </span>
            </button>
          );
        })}
      </div>

      {oberta && (
        <section style={{ padding: '16px', borderRadius: 'var(--r-xl)', border: '1px solid var(--brand-1)', background: 'var(--surface)', marginBottom: 22 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
            <span lang="zgh" style={{ fontSize: 44, fontWeight: 800, lineHeight: 1 }}>{oberta.tif}</span>
            <span style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-soft)' }}>{oberta.lat}</span>
            {oberta.mena && (
              <span style={{ fontSize: 12, fontWeight: 700, padding: '4px 10px', borderRadius: 'var(--r-pill)', background: 'var(--surface-2)', color: 'var(--text-soft)' }}>
                {MENA[oberta.mena]}
              </span>
            )}
          </div>
          <p style={{ margin: '10px 0 0', fontSize: 15, lineHeight: 1.6 }}>{oberta.com}</p>
          {oberta.altres?.length ? (
            <p style={{ margin: '6px 0 0', fontSize: 13.5, color: 'var(--text-soft)' }}>
              A la biblioteca també la trobaràs escrita {oberta.altres.map((a) => `«${a}»`).join(', ')}.
            </p>
          ) : null}
          {/* La nota no és «com sona»: és el que fa que les paraules d'aquesta lletra siguin les
              que són. A la ⵅ i a la ⵖ explica per què «rix» i «riɣ» són la mateixa paraula, que
              és de les coses més útils que es poden saber d'aquesta llengua i no una errada a
              amagar (#364, #239). Per això es veu, i no en lletra petita. */}
          {oberta.nota ? (
            <p style={{ margin: '10px 0 0', padding: '10px 12px', fontSize: 13.5, lineHeight: 1.6,
                        borderRadius: 'var(--r-md, 8px)', background: 'var(--brand-gradient-soft)',
                        border: '1px solid var(--border)' }}>
              {oberta.nota}
            </p>
          ) : null}

          {oberta.exemples.length ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 14 }}>
              {oberta.exemples.map((m) => (
                <div key={`${m.key}-${m.drill_id}`}
                     style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface-2)' }}>
                  <button onClick={() => toca(m)} aria-label={`Escolta ${m.word}`}
                          style={{ width: 44, height: 44, flexShrink: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%', border: 'none', background: sonant === m.key ? 'var(--brand-1)' : 'var(--brand-gradient)', color: '#fff', cursor: 'pointer' }}>
                    <FaVolumeUp size={14} />
                  </button>
                  <span style={{ flex: 1, minWidth: 0 }}>
                    <Frase text={m.word} size="md" />
                    {m.meaning && <span style={{ fontSize: 13, color: 'var(--text-soft)' }}>{m.meaning}</span>}
                  </span>
                  <span style={{ textAlign: 'right', fontSize: 11.5, color: 'var(--text-muted)', flexShrink: 0, maxWidth: 160 }}>
                    {m.posicio && <div>{ON[m.posicio]}</div>}
                    {/* Qui ho diu, sempre, i sense fer passar una veu d'un canal per una de
                        casa (#288). */}
                    <div style={{ color: m.de_casa === false ? 'var(--amber-strong, #8a6100)' : undefined }}>{quiHoDiu(m)}</div>
                    {m.region && <div>{m.region}</div>}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ marginTop: 14, padding: '12px 14px', borderRadius: 'var(--r-lg)', background: 'var(--brand-gradient-soft)', fontSize: 13.5, lineHeight: 1.6 }}>
              <strong>D’aquesta lletra encara no en tenim cap paraula gravada.</strong> No és que
              no sigui important: és que ningú no ens ha dit encara una paraula que la porti.
              <div style={{ marginTop: 10 }}>
                <button onClick={() => navigate('/veus')} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 16px', minHeight: 44, borderRadius: 'var(--r-pill)', border: 'none', background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 13.5, cursor: 'pointer', fontFamily: 'inherit' }}>
                  <FaMicrophone size={12} /> Posa-hi la teva veu
                </button>
              </div>
            </div>
          )}
        </section>
      )}

      <Parelles grups={parelles} toca={toca} sonant={sonant} />
    </div>
  );
}

/** Dos sons que s'assemblen, i dues paraules que només es diferencien en aquell so. És la peça
 *  que de debò ensenya a sentir la diferència, i surt de la biblioteca: una parella inventada
 *  ensenyaria a sentir una diferència entre paraules que ningú no ha dit mai. */
function Parelles({ grups, toca, sonant }: { grups: GrupParelles[] | null; toca: (m: MotDeLletra, id?: string) => void; sonant: string | null }) {
  const [prova, setProva] = useState<{ grup: number; parella: number; quina: 'a' | 'b'; dit: 'a' | 'b' | null } | null>(null);
  const amb = useMemo(() => (grups || []).filter((g) => g.parelles.length), [grups]);

  if (grups === null) return null;
  if (!amb.length) {
    return (
      <section style={{ padding: '14px 16px', borderRadius: 'var(--r-xl)', border: '1px solid var(--border)', background: 'var(--surface)' }}>
        <h2 style={{ fontSize: 17, margin: '0 0 8px' }}>Dos sons que s’assemblen</h2>
        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: 'var(--text-soft)' }}>
          Encara no tenim cap parella de paraules que es distingeixi per un sol so i que es pugui
          sentir sencera. Quan en tinguem, aquí hi haurà l’exercici de dir quina de les dues sona.
        </p>
      </section>
    );
  }

  return (
    <section style={{ padding: '14px 16px', borderRadius: 'var(--r-xl)', border: '1px solid var(--border)', background: 'var(--surface)' }}>
      <h2 style={{ fontSize: 17, margin: '0 0 4px' }}>Dos sons que s’assemblen</h2>
      <p style={{ margin: '0 0 14px', fontSize: 13.5, color: 'var(--text-soft)', lineHeight: 1.6 }}>
        Dues paraules que només es diferencien en una lletra. Escolta-les una darrere l’altra i
        després prova de dir quina sona.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {amb.map((g, gi) => (
          <div key={`${g.so_a}${g.so_b}`}>
            <div style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>
              <span lang="zgh">{g.tif_a}</span> {g.so_a} &nbsp;·&nbsp; <span lang="zgh">{g.tif_b}</span> {g.so_b}
              <span style={{ fontWeight: 600, color: 'var(--text-muted)', fontSize: 12.5 }}>
                {' '}· {g.quantes} {g.quantes === 1 ? 'parella' : 'parelles'} a la biblioteca
              </span>
            </div>
            {g.parelles.map((p, pi) => {
              const jugant = prova && prova.grup === gi && prova.parella === pi;
              const amagada = jugant ? p[prova!.quina] : null;
              return (
                <div key={`${p.a.key}-${p.b.key}`} style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  {(['a', 'b'] as const).map((cara) => {
                    const m = p[cara];
                    const encertada = jugant && prova!.dit === cara && cara === prova!.quina;
                    const errada = jugant && prova!.dit === cara && cara !== prova!.quina;
                    return (
                      <button key={cara}
                              onClick={() => {
                                if (jugant && prova!.dit === null) setProva({ ...prova!, dit: cara });
                                else toca(m, `${m.key}-${cara}`);
                              }}
                              style={{
                                display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 14px', minHeight: 48,
                                borderRadius: 'var(--r-lg)', cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
                                background: encertada ? 'var(--emerald-soft)' : errada ? 'var(--rose-soft)' : 'var(--surface-2)',
                                border: `1px solid ${encertada ? 'var(--emerald)' : errada ? 'var(--rose)' : 'var(--border)'}`,
                                color: 'var(--text)',
                              }}>
                        <FaVolumeUp size={12} color={sonant === `${m.key}-${cara}` ? 'var(--brand-1)' : 'var(--text-soft)'} />
                        <span>
                          <Frase text={m.word} size="sm" />
                          {m.meaning && <span style={{ fontSize: 12, color: 'var(--text-soft)' }}>{m.meaning}</span>}
                        </span>
                      </button>
                    );
                  })}
                  {jugant ? (
                    prova!.dit === null ? (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-soft)' }}>
                        <button onClick={() => amagada && toca(amagada, `${amagada.key}-prova`)}
                                style={botonet}><FaVolumeUp size={11} /> Torna-ho a sentir</button>
                        Quina de les dues és?
                      </span>
                    ) : (
                      <span style={{ fontSize: 13, fontWeight: 700, color: prova!.dit === prova!.quina ? 'var(--emerald)' : 'var(--rose)' }}>
                        {prova!.dit === prova!.quina ? 'Sí, aquesta.' : `Era «${p[prova!.quina].word}».`}{' '}
                        <button onClick={() => setProva(null)} style={botonet}>Prou</button>
                      </span>
                    )
                  ) : (
                    <button onClick={() => {
                      const quina = Math.random() < 0.5 ? 'a' : 'b';
                      setProva({ grup: gi, parella: pi, quina, dit: null });
                      toca(p[quina], `${p[quina].key}-prova`);
                    }} style={botonet}>Quina sona?</button>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </section>
  );
}

const botonet: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 12px', minHeight: 40,
  borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)',
  color: 'var(--brand-1)', fontWeight: 700, fontSize: 12.5, cursor: 'pointer', fontFamily: 'inherit',
};
