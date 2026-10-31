import type { Drill } from '../types';

// El que ha escrit la màquina, entre parèntesis i dit (#546).
//
// L'amo (31-10): «tots els drills han de ser transcrits; si ja estan transcrits, la transcripció
// amb el nostre model ha d'anar entre parèntesis, i la traducció al català amb el nostre model
// des de la transcripció ha d'anar entre parèntesis».
//
// Dues línies, mai al lloc del parlant:
//  · **la nostra lectura** — el que el nostre ASR sent a la gravació (`text_tachelhit_suggested`);
//  · **el que diu la nostra lectura** — el significat d'AQUELLA lectura, no de la frase
//    (`esborranys`, amb el model que l'ha fet).
//
// El segon surt sovint malament, i és volgut que es vegi. Mesurat el 31-10 amb vuit línies de
// Baba Ali: on el subtítol àrab deia «Posa aquí l'empremta del palmell», la lectura traduïda deia
// «lluitador de la tecnologia». El motiu és conegut i està apuntat: l'ASR enganxa les paraules i
// cap traductor no les entén. Veure-ho al costat del bo és el que deixa jutjar fins on arriba el
// model avui; amagar-ho només ho faria semblar millor del que és.
//
// Els parèntesis i el gris fan la feina de dir «això no ho ha escrit ningú»: el text del parlant
// és sagrat i no es toca mai (ADR 0003).

/** El significat que la màquina treu de la SEVA pròpia lectura, si n'hi ha. */
export function significatDeLaLectura(d: Partial<Drill>): string {
  try {
    const esb = JSON.parse(d.esborranys || '[]');
    if (!Array.isArray(esb)) return '';
    const e = esb.find((x) => x && x.llengua === 'ca' && /lectura/i.test(String(x.de || x.model || '')));
    return String(e?.text || '').trim();
  } catch {
    return '';
  }
}

export default function LaMaquina({ drill, nomesSignificat }: {
  drill: Partial<Drill>;
  /** Quan la pantalla ja ensenya la lectura pel seu compte, aquí només hi va el significat. */
  nomesSignificat?: boolean;
}) {
  const lectura = (drill.text_tachelhit_suggested || '').trim();
  const escrit = (drill.text_tachelhit || '').trim();
  const significat = significatDeLaLectura(drill);
  // La lectura només es diu quan hi ha el text del parlant al costat: sense ell, les pantalles
  // ja la mostren com la proposta que és, i repetir-la dues vegades confon.
  const diuLectura = !nomesSignificat && !!lectura && !!escrit;
  if (!diuLectura && !significat) return null;
  return (
    <div style={caixa}>
      {diuLectura && (
        <div lang="shi">({lectura}) <span style={qui}>la nostra lectura</span></div>
      )}
      {significat && (
        <div>({significat}) <span style={qui}>el que diu la nostra lectura</span></div>
      )}
    </div>
  );
}

const caixa: React.CSSProperties = {
  fontSize: 12.5, color: 'var(--text-muted)', fontStyle: 'italic',
  lineHeight: 1.45, marginTop: 3, display: 'flex', flexDirection: 'column', gap: 1,
};
const qui: React.CSSProperties = {
  fontSize: 10.5, fontStyle: 'normal', letterSpacing: '.03em', textTransform: 'uppercase', opacity: 0.8,
};
