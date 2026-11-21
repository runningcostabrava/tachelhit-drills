import type { Drill } from '../types';
import { formes } from './tifinag';

// Quines frases casen amb el que algú busca (#506).
//
// Això és la cerca del servidor (`GET /corpus/search`) feta aquí, perquè al telèfon s'ha de poder
// cercar sense xarxa: la còpia de la biblioteca ja hi és sencera. Les regles són les mateixes:
//  · el català, l'àrab i l'etiqueta es miren tal com s'escriuen;
//  · l'amazic es compara **pel so**, passant-ho tot al llatí acadèmic amb el nostre
//    transliterador, perquè «aghrum», «aɣrum» i «ⴰⵖⵔⵓⵎ» trobin la mateixa frase —és el que al
//    servidor fa `text_key`, que no baixa a la fitxa;
//  · el que el curs exclou —l'irlandès de les proves velles, el canal gravat en càmera— tampoc
//    no surt aquí.
//
// És una funció pura i viu sola perquè es pugui provar sense arrencar l'app.

/** Les mateixes exclusions que `backend/grammar.py`: si allà no compten, aquí tampoc. */
const ETIQUETES_FORA = ['irish'];
const CANAL_FORA = 'tamazight for all';

export const foraDeLaBiblioteca = (d: Partial<Drill>) =>
  ETIQUETES_FORA.some(t => (d.tag || '').toLowerCase().includes(t))
  || [d.author, d.source_channel, d.speaker].some(v => (v || '').toLowerCase().includes(CANAL_FORA));

/** La clau per comparar amazic: el mateix so, vingui de l'alfabet que vingui. */
const perSo = (s?: string | null) => {
  const net = (s || '').trim();
  if (!net) return '';
  try { return formes(net).lat; } catch { return net.toLowerCase(); }
};

const quan = (d: Partial<Drill>) => Date.parse(d.updated_at || d.date_created || '') || 0;

/**
 * Com de semblant és un camp al que s'ha escrit. 0 vol dir que no casa.
 *
 * En Pablo: «if I look for "enfadat" then "està enfadat" is more similar than "està molt
 * enfadat"». Les dues coses que ho decideixen són **on** cau el que busques i **quant** de la
 * frase ocupa: una frase que és just la paraula va primera, una que la porta al començament va
 * abans que una que la porta al mig, i entre dues iguals guanya la més curta, perquè la paraula
 * hi pesa més.
 */
function puntuaCamp(valor: string, consulta: string): number {
  if (!valor || !consulta) return 0;
  const on = valor.indexOf(consulta);
  if (on < 0) return 0;
  const abans = on === 0 || /[\s.,;:!?¿¡«»"'()\-–—]/.test(valor[on - 1]);
  const despres = on + consulta.length >= valor.length
    || /[\s.,;:!?¿¡«»"'()\-–—]/.test(valor[on + consulta.length]);
  const base = valor === consulta ? 100
    : on === 0 && despres ? 70
    : abans && despres ? 60
    : 40;
  // Quant de la frase és el que busques: «enfadat» dins de «està enfadat» pesa més que dins de
  // «està molt enfadat». Val com a màxim 20, de manera que no passa mai per davant de la base.
  return base + 20 * (consulta.length / valor.length);
}

/** La puntuació d'una frase: la del camp que hi casa millor. 0 vol dir que no hi surt. */
export function puntua(d: Partial<Drill>, consulta: string): number {
  if (foraDeLaBiblioteca(d)) return 0;
  const planer = consulta.trim().toLowerCase();
  if (!planer) return 0;
  const so = perSo(consulta);
  let millor = 0;
  for (const v of [d.text_catalan, d.text_catalan_suggested, d.text_arabic, d.tag]) {
    millor = Math.max(millor, puntuaCamp((v || '').trim().toLowerCase(), planer));
  }
  if (so) {
    for (const v of [d.text_tachelhit, d.text_tachelhit_latin, d.text_tachelhit_suggested]) {
      if ((v || '').trim()) millor = Math.max(millor, puntuaCamp(perSo(v), so));
    }
  }
  return millor;
}

/**
 * Ordena per semblança: el que s'assembla més, primer.
 *
 * Entre dues igual de semblants passa davant la que té veu —una frase que no sona no serveix per
 * aprendre-la— i, si encara empaten, la més nova. S'aplica tant a la còpia del telèfon com a la
 * resposta del servidor, que ve ordenada per data, perquè l'ordre que es veu sigui el mateix.
 */
export function ordena<T extends Partial<Drill>>(drills: T[], consulta: string): T[] {
  const amb = drills.map((d) => ({ d, p: puntua(d, consulta) }));
  amb.sort((a, b) => {
    if (b.p !== a.p) return b.p - a.p;
    const va = (a.d.audio_url || '').trim() ? 1 : 0;
    const vb = (b.d.audio_url || '').trim() ? 1 : 0;
    if (va !== vb) return vb - va;
    return quan(b.d) - quan(a.d);
  });
  return amb.map((x) => x.d);
}

/** Les frases que casen amb el que es busca, les més semblants primer. */
export function filtra<T extends Partial<Drill>>(drills: T[], consulta: string, limit = 40): T[] {
  if (!consulta.trim()) return [];
  const casen = drills.filter((d) => puntua(d, consulta) > 0);
  return ordena(casen, consulta).slice(0, limit);
}
