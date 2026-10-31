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

/** Les frases que casen amb el que es busca, les últimes primer. */
export function filtra<T extends Partial<Drill>>(drills: T[], consulta: string, limit = 40): T[] {
  const planer = consulta.trim().toLowerCase();
  if (!planer) return [];
  const so = perSo(consulta);
  const casen = drills.filter((d) => {
    if (foraDeLaBiblioteca(d)) return false;
    if ([d.text_catalan, d.text_catalan_suggested, d.text_arabic, d.tag]
      .some(v => (v || '').toLowerCase().includes(planer))) return true;
    return !!so && [d.text_tachelhit, d.text_tachelhit_latin, d.text_tachelhit_suggested]
      .some(v => !!(v || '').trim() && perSo(v).includes(so));
  });
  return casen.sort((a, b) => quan(b) - quan(a)).slice(0, limit);
}
