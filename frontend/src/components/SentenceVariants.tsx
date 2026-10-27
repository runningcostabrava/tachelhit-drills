import { FaPlay } from 'react-icons/fa';
import { getMediaUrl } from '../config';

// Les altres maneres de dir la mateixa frase.
//
// Qui grava pot escriure-la com la diu ell («Com ho dius tu?», a la gravadora), i això es desa
// amb la gravació. Fins ara només es veia al reproductor, i l'amo ho va dir clar: «si jo gravo i
// canvio el text, el sistema hauria de mostrar també l'altra versió de la mateixa frase amb la
// seva gravació, i hauria de mostrar l'autor i la zona».
//
// Una frase dita d'una altra manera NO és una correcció de la de dalt. Són dues maneres, i
// totes dues porten el nom de qui la diu i el seu poble: el que mana és qui parla, no qui va
// escriure la fitxa primer.

export interface Variant {
  id: number;
  text: string;
  tif?: string | null;
  audio_url: string;
  speaker: string | null;
  variety: string | null;
  region: string | null;
  is_native?: boolean | null;
  /** De quina mena és: «so» (la mateixa paraula dita o escrita d'una altra manera) o «paraula»
   *  (al seu poble en diuen una altra). `null` quan qui ho va dir no ho va precisar (#332). */
  kind?: 'so' | 'paraula' | null;
}

//: Com es diu cada mena. Per a qui aprèn no són el mateix: la primera li diu com sona la
//: paraula que està estudiant, la segona li ensenya una paraula nova.
const TITOL: Record<string, string> = {
  so: 'La mateixa paraula, dita d’una altra manera',
  paraula: 'Al seu poble en diuen una altra cosa',
  '': 'També es diu',
};

export default function SentenceVariants({ variants, size = 'md' }: { variants?: Variant[] | null; size?: 'sm' | 'md' }) {
  if (!variants || variants.length === 0) return null;
  const fs = size === 'sm' ? 13 : 14.5;
  // Un sinònim no és una variant dialectal, i van per separat (#332). El que ningú no ha
  // precisat es queda com estava: «també es diu», sense inventar-se de quina mena és.
  const menes = ['so', 'paraula', ''].filter((k) => variants.some((v) => (v.kind || '') === k));
  return (
    <div style={{ marginTop: 6, paddingTop: 6, borderTop: '1px dashed var(--border)' }}>
      {menes.map((mena) => (
        <Grup key={mena || 'cap'} titol={TITOL[mena]} fs={fs}
              quines={variants.filter((v) => (v.kind || '') === mena)} />
      ))}
    </div>
  );
}

function Grup({ titol, quines, fs }: { titol: string; quines: Variant[]; fs: number }) {
  return (
    <>
      <div style={{ fontSize: 10.5, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 3 }}>
        {titol}
      </div>
      {quines.map((v) => (
        <div key={v.id} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
          <span style={{ flex: 1, minWidth: 0 }}>
            <span lang="shi" style={{ fontWeight: 700, fontSize: fs, color: 'var(--brand-1)' }}>{v.text}</span>
            {v.tif && (
              <span lang="shi" style={{ display: 'block', fontFamily: 'var(--font-tifinagh)', fontSize: fs - 2.5, color: 'var(--text-muted)', opacity: 0.85, lineHeight: 1.35 }}>
                {v.tif}
              </span>
            )}
            <span style={{ display: 'block', fontSize: 11, color: 'var(--text-muted)' }}>
              {v.speaker || 'sense nom'}
              <span style={{ opacity: 0.6 }}>
                {v.variety ? ` · ${v.variety}` : ''}{v.region ? ` · ${v.region}` : ''}
              </span>
            </span>
          </span>
          <button onClick={() => new Audio(getMediaUrl(v.audio_url)).play().catch(() => {})}
                  aria-label={`Escolta com ho diu ${v.speaker || 'aquesta veu'}`} title="Escolta-la"
                  style={{ width: 28, height: 28, borderRadius: '50%', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--brand-1)', cursor: 'pointer', flexShrink: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
            <FaPlay size={9} />
          </button>
        </div>
      ))}
    </>
  );
}
