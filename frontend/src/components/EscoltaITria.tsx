import { useCallback, useEffect, useMemo, useState } from 'react';
import { FaCheck, FaRedo, FaTimes, FaVolumeUp } from 'react-icons/fa';
import type { Drill } from '../types';
import Frase from './Frase';
import WordGloss from './WordGloss';

/**
 * Escolta una línia de la història i tria quina de les quatre frases escrites és (#387).
 *
 * No és l'«escolta i tria» de la pràctica: aquell dona quatre **significats en català** i entrena
 * a entendre. Això dona quatre **frases en amazic** i entrena una altra cosa —lligar el que se
 * sent amb el que està escrit—, que és el pas que falta per poder llegir el que ja s'entén
 * d'orella, i el que fa que el tifinag deixi de ser un dibuix.
 *
 * Per què dins d'una història: les altres línies del mateix conte són les distraccions bones
 * —mateixa veu, mateix tema, mateixa manera de parlar—. Agafades de tot el corpus, qualsevol les
 * encerta per eliminació sense haver entès res.
 *
 * Dues regles que decideixen si l'exercici val:
 *
 *  - **La resposta bona la va escriure algú.** Només hi entren les línies amb `text_tachelhit`;
 *    la lectura de màquina viu a `text_tachelhit_suggested` i no pot ser mai la resposta, perquè
 *    diria que és bona una frase que no ha mirat ningú.
 *  - **La veu és d'una persona.** `audio_url`, no la sintètica: una veu de màquina en amazic no
 *    ensenya com sona la llengua.
 */

/** Quantes preguntes té una ronda, com a màxim. */
const RONDA = 8;
/** Quantes opcions s'ensenyen, comptant la bona. */
const OPCIONS = 4;

const veu = (d: Drill) => (d.audio_url || '').trim();
const escrit = (d: Drill) => (d.text_tachelhit || '').trim();
const mots = (t: string) => t.toLowerCase().split(/[^\p{L}\p{N}ʷ]+/u).filter((w) => w.length > 1);
const barreja = <T,>(x: T[]) => x.map((v) => ({ v, k: Math.random() })).sort((a, b) => a.k - b.k).map((o) => o.v);

/** Les tres falses: d'una llargada semblant i, quan es pugui, que comparteixin alguna paraula. */
function distraccions(bona: Drill, totes: Drill[], quantes: number): Drill[] {
  const bo = escrit(bona);
  const seus = new Set(mots(bo));
  const pesades = totes
    .filter((d) => d.id !== bona.id && escrit(d) && escrit(d) !== bo)
    .map((d) => {
      const compartides = mots(escrit(d)).filter((w) => seus.has(w)).length;
      return { d, pes: Math.abs(escrit(d).length - bo.length) - compartides * 6 };
    })
    .sort((a, b) => a.pes - b.pes);
  // De les més semblants, tres a l'atzar: si sempre fossin les tres primeres, la segona vegada
  // que surt una línia ja se'n recorda la forma de les opcions i no cal escoltar res.
  return barreja(pesades.slice(0, quantes * 3)).slice(0, quantes).map((x) => x.d);
}

export interface EscoltaITriaProps {
  /** Les línies de la història, en ordre. */
  drills: Drill[];
  /** Fer sonar la veu d'una línia amb el reproductor de la història. */
  sona: (d: Drill) => void | Promise<void>;
  /** Aturar el que soni ara. */
  atura: () => void;
  onTanca: () => void;
}

export default function EscoltaITria({ drills, sona, atura, onTanca }: EscoltaITriaProps) {
  const [ronda, setRonda] = useState(0);
  const [i, setI] = useState(0);
  const [tria, setTria] = useState<number | null>(null);
  const [encerts, setEncerts] = useState(0);

  // Les preguntes d'aquesta ronda. Es trien una vegada: si es recalculessin a cada pintada, les
  // opcions ballarien sota el dit.
  const preguntes = useMemo(() => {
    const bones = drills.filter((d) => veu(d) && escrit(d));
    return barreja(bones).slice(0, RONDA).map((bona) => ({
      bona,
      opcions: barreja([bona, ...distraccions(bona, drills, OPCIONS - 1)]),
    }));
    // `ronda` hi és a posta: demanar-ne una altra vol dir tornar a triar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [drills, ronda]);

  const q = preguntes[i];
  const torna = useCallback(() => { if (q) sona(q.bona); }, [q, sona]);

  // Cada pregunta comença sonant: escoltar ÉS la pregunta.
  useEffect(() => { torna(); }, [i, ronda]);  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => atura(), []);         // eslint-disable-line react-hooks/exhaustive-deps

  if (!preguntes.length) {
    return (
      <section style={caixa}>
        <Capçalera onTanca={onTanca} dreta={null} />
        <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.6, color: 'var(--text-soft)' }}>
          Aquesta història encara no es pot practicar així: calen línies que tinguin <strong>la veu
          d'una persona</strong> i <strong>les paraules escrites</strong>. Si parles amazic, posar
          la veu o escriure una línia obre aquest exercici per a tothom.
        </p>
      </section>
    );
  }

  if (i >= preguntes.length) {
    return (
      <section style={caixa}>
        <Capçalera onTanca={onTanca} dreta={null} />
        <p style={{ margin: 0, fontSize: 15, fontWeight: 800 }}>
          {encerts} de {preguntes.length} {encerts === 1 ? 'encertada' : 'encertades'}.
        </p>
        <p style={{ margin: 0, fontSize: 13.5, color: 'var(--text-soft)', lineHeight: 1.6 }}>
          Les falses d'una ronda nova no són les mateixes: la història té més línies que
          s'assemblen a aquesta.
        </p>
        <button onClick={() => { setRonda((r) => r + 1); setI(0); setTria(null); setEncerts(0); }} style={primari}>
          <FaRedo size={12} /> Una altra ronda
        </button>
      </section>
    );
  }

  const encertada = tria != null && tria === q.bona.id;

  return (
    <section style={caixa}>
      <Capçalera onTanca={onTanca} dreta={`${i + 1} de ${preguntes.length}`} />

      <p style={{ margin: 0, fontSize: 13.5, color: 'var(--text-soft)', lineHeight: 1.55 }}>
        Sona una línia de la història. Quina de les quatre és?
      </p>

      <button onClick={torna} style={secundari}><FaVolumeUp size={13} /> Torna-ho a sentir</button>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {q.opcions.map((o) => {
          const esBona = o.id === q.bona.id;
          const triada = tria === o.id;
          const marca = tria == null ? null : esBona ? 'bona' : triada ? 'falsa' : null;
          return (
            <button key={o.id}
                    onClick={() => {
                      if (tria != null) return;
                      setTria(o.id);
                      if (o.id === q.bona.id) setEncerts((n) => n + 1);
                      else torna();   // en fallar, es torna a sentir de seguida
                    }}
                    style={{
                      ...opcio,
                      borderColor: marca === 'bona' ? 'var(--emerald)' : marca === 'falsa' ? 'var(--rose)' : 'var(--border)',
                      background: marca === 'bona' ? 'var(--emerald-soft)' : marca === 'falsa' ? 'var(--rose-soft)' : 'var(--surface)',
                      cursor: tria == null ? 'pointer' : 'default',
                    }}>
              <span style={{ flex: 1, minWidth: 0 }}>
                <Frase text={escrit(o)} size="md" />
              </span>
              {marca === 'bona' && <FaCheck size={14} color="var(--emerald)" />}
              {marca === 'falsa' && <FaTimes size={14} color="var(--rose)" />}
            </button>
          );
        })}
      </div>

      {/* En encertar i en fallar, el mateix: la frase paraula per paraula, què vol dir i qui ho
          diu. Saber que has fallat no ensenya res; veure què deia, sí. */}
      {tria != null && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '12px 14px', borderRadius: 'var(--r-lg)', background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
          <strong style={{ fontSize: 13.5, color: encertada ? 'var(--emerald)' : 'var(--rose)' }}>
            {encertada ? 'Sí, és aquesta.' : 'Era aquesta altra.'}
          </strong>
          <Frase text={escrit(q.bona)} size="md" />
          {(q.bona.text_catalan || '').trim() && (
            <div style={{ fontSize: 13.5, color: 'var(--text-soft)' }}>{q.bona.text_catalan}</div>
          )}
          <WordGloss drill={q.bona} size="sm" />
          {(q.bona.author || '').trim() && (q.bona.author || '').trim() !== 'Auto Capture' && (
            <div style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>
              Ho diu <strong>{q.bona.author}</strong>{(q.bona.region || '').trim() ? ` · ${q.bona.region}` : ''}.
            </div>
          )}
          <button onClick={() => { setTria(null); setI((n) => n + 1); }} style={primari}>
            {i + 1 < preguntes.length ? 'Següent' : 'Acabem'}
          </button>
        </div>
      )}
    </section>
  );
}

function Capçalera({ onTanca, dreta }: { onTanca: () => void; dreta: string | null }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
      <strong style={{ fontSize: 15 }}>Escolta i tria la frase</strong>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
        {dreta && <span style={{ fontSize: 12.5, color: 'var(--text-muted)', fontWeight: 700 }}>{dreta}</span>}
        <button onClick={onTanca} aria-label="Tanca l'exercici"
                style={{ width: 36, height: 36, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: 'var(--r-pill)', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-soft)', cursor: 'pointer' }}>
          <FaTimes size={13} />
        </button>
      </span>
    </div>
  );
}

const caixa: React.CSSProperties = {
  display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 18,
  padding: '14px 16px', borderRadius: 'var(--r-xl)',
  border: '1px solid var(--brand-1)', background: 'var(--surface)',
};
const opcio: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 10, textAlign: 'left',
  padding: '12px 14px', minHeight: 56, borderRadius: 'var(--r-lg)',
  border: '1px solid var(--border)', background: 'var(--surface)',
  color: 'var(--text)', fontFamily: 'inherit',
};
const primari: React.CSSProperties = {
  alignSelf: 'flex-start', display: 'inline-flex', alignItems: 'center', gap: 8,
  padding: '10px 18px', minHeight: 44, borderRadius: 'var(--r-pill)', border: 'none',
  background: 'var(--brand-gradient)', color: '#fff', fontWeight: 800, fontSize: 14,
  cursor: 'pointer', fontFamily: 'inherit',
};
const secundari: React.CSSProperties = {
  alignSelf: 'flex-start', display: 'inline-flex', alignItems: 'center', gap: 8,
  padding: '10px 16px', minHeight: 44, borderRadius: 'var(--r-pill)',
  border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)',
  fontWeight: 700, fontSize: 13.5, cursor: 'pointer', fontFamily: 'inherit',
};
