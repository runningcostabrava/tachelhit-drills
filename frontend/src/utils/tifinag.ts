// Les dues cares d'una frase amaziga: el tifinag i el llatí (#339).
//
// Regla del propietari: **quan tenim una transcripció ha d'anar sempre en tifinag i en llatí, i
// el tifinag ha de tenir el lloc de més importància.** Fins ara el projecte feia el contrari
// sense pensar-hi: el camp del Mètode es diu literalment «la frase en tifinag per posar-la SOTA
// la llatina», i a dinou pantalles el tifinag era la línia petita i grisa de sota.
//
// Això es calcula aquí i no al servidor per dues raons mesurades: al servidor costa 247 µs per
// frase —un segon sencer per a les 4.221 de la llista de drills, a cada petició— i al mòbil, que
// és una app de Capacitor, la deixaria sense els dos alfabets quan no hi ha connexió.
//
// La taula no s'escriu aquí: la genera `backend/tools/genera_tifinag.py` des de
// `backend/transliteration.py`, i una prova torna a generar-la i falla si no coincideixen. Dues
// taules escrites a mà divergeixen, i quan divergeixen el que llegeix qui aprèn deixa de ser el
// que diu qui parla.
//
// Transliterar **no és traduir**: és la mateixa paraula amb unes altres lletres, i és
// determinista. Per això no va a `*_suggested` ni demana el permís de ningú, i no toca mai el
// text que va escriure el parlant.

import { ENTRADA, LLATI, TIFINAG } from './tifinag.data';

// Les claus llargues primer, perquè els dígrafs guanyin les lletres soltes: «gh» ha de fer ɣ i
// no g+h, i «ⴳⵯ» ha de fer gʷ i no ⴳ.
const CLAUS = Object.keys(ENTRADA).sort((a, b) => b.length - a.length);

export interface Formes {
  /** La frase en tifinag. */
  tif: string;
  /** La frase en llatí acadèmic. */
  lat: string;
}

/**
 * Les dues cares d'una frase, vingui de l'alfabet que vingui.
 *
 * S'hi pot posar el que la gent escriu de debò —el llatí de teclat («gh», «3», «ou»), el llatí
 * acadèmic (ɣ, ɛ, ḥ) o el tifinag—, perquè la taula d'entrada els coneix tots tres. El que no
 * és una lletra (els espais, els signes, els números) es queda al llatí i marxa del tifinag,
 * que no en té.
 */
export function formes(cru: string): Formes {
  const text = (cru || '').normalize('NFC').toLowerCase();
  const tif: string[] = [];
  const lat: string[] = [];
  let i = 0;
  while (i < text.length) {
    const clau = CLAUS.find((k) => text.startsWith(k, i));
    if (clau === undefined) {
      const c = text[i];
      lat.push(c);
      if (/\s/.test(c)) tif.push(' ');
      i += 1;
      continue;
    }
    const so = ENTRADA[clau];
    lat.push(LLATI[so] ?? so);
    tif.push(TIFINAG[so] ?? '');
    i += clau.length;
  }
  return { tif: tif.join('').trim(), lat: lat.join('').trim() };
}

/** Ja està escrita en tifinag? (hi ha alguna lletra del bloc tifinag d'Unicode) */
export function esTifinag(text: string): boolean {
  return /[ⴰ-⵿]/.test(text || '');
}

/**
 * Les dues cares d'una frase, **respectant el que va escriure el parlant**.
 *
 * La cara que coincideix amb l'alfabet de l'original es torna tal com la van escriure, lletra per
 * lletra: el transliterador no li ha de «netejar» res. L'altra cara es calcula. Si el parlant va
 * escriure «sġix» amb la g i el punt a part, el que es veu en llatí és el que va escriure ell;
 * el tifinag sí que surt del càlcul, perquè no n'hi havia.
 */
export function duesCares(original: string, latDesat?: string | null): Formes {
  const net = (original || '').trim();
  if (!net) return { tif: '', lat: '' };
  const f = formes(net);
  if (esTifinag(net)) return { tif: net, lat: (latDesat || '').trim() || f.lat };
  // Un tros sense cap lletra —el buit d'un exercici, uns punts, un signe— no es pot transliterar:
  // no en surt res, i la ratlla tifinag es quedava sense aquell tros. A l'exercici de l'estat
  // d'annexió, que és «g ······», la ratlla de dalt deia «ⴳ» i prou, i semblava una errada.
  // Es deixa igual a les dues cares, que és el que s'ha de veure.
  if (!f.tif) return { tif: net, lat: net };
  return { tif: f.tif, lat: net };
}

/** Les mateixes dues cares, però paraula per paraula, perquè es puguin encendre d'una en una. */
export function caresPerParaula(original: string, latDesat?: string | null): Formes[] {
  const paraules = (original || '').trim().split(/\s+/).filter(Boolean);
  const lat = (latDesat || '').trim().split(/\s+/).filter(Boolean);
  return paraules.map((p, i) => duesCares(p, lat.length === paraules.length ? lat[i] : null));
}
