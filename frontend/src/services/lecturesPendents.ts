import axios from 'axios';
import { Network } from '@capacitor/network';
import { API_BASE } from '../config';
import type { Drill } from '../types';
import { drillsLocals, sincronitza } from './biblioteca';
import { demanaLectura, esborranysAmb } from './lectura';

// Les gravacions que han quedat sense la lectura de la màquina.
//
// L'amo (1-11-2026), després de gravar «hey bereber» i no veure-hi res: «has de revisar la
// gravació feta offline i/o online, no hi és?». Hi era: el fitxer de 2 segons havia pujat bé. El
// que no hi era és la lectura.
//
// El motiu, mirat al codi: `/transcribe/` només es demana **just després de gravar**, i només si
// en aquell moment hi ha xarxa. Qui grava sense senyal —que és el cas d'anar pel camp amb algú
// que parla la llengua, o sigui el cas per al qual existeix tot això— es queda sense: el fitxer
// puja sol quan torna el senyal, però ningú no torna mai a demanar-ne la lectura. Les quatre
// frases del 31-10 sí que en tenen, perquè es van gravar amb cobertura; la de l'endemà, no.
//
// Això ho repesca. Només les TEVES —les que porten el teu nom—, poques de cada vegada, i només
// amb xarxa: transcriure mitja biblioteca des d'un telèfon no és la seva feina, és la del
// servidor. El resultat va a `text_tachelhit_suggested` i el seu significat a `esborranys`, mai
// als camps del parlant (ADR 0003).
//
// I ara **explica què ha passat** (#556). Abans tornava un número que ningú no llegia i tenia
// tres camins muts: sense senyal, lectura buida i `catch {}`. Pitjor encara, qui no té el nom
// posat al telèfon no entrava ni a la primera línia —`user_name` buit vol dir cap frase— i això
// tampoc no ho deia ningú: una app acabada d'instal·lar no repescava res i semblava que sí.

/** Quantes se'n miren de cada vegada. Poques: això corre de fons i no ha de fer nosa. */
const CADA_COP = 8;

const enLinia = () => Network.getStatus().then((s) => s.connected).catch(() => false);

/** Per què la repesca no ha fet res, quan no n'ha fet. */
export type MotiuRepesca = 'sense-nom' | 'sense-senyal' | 'res-a-fer' | 'fet';

export interface Repesca {
  /** Quantes lectures ha desat aquesta passada. */
  fetes: number;
  /** Quantes gravacions teves segueixen sense lectura després d'això. */
  falten: number;
  /** Quantes ha intentat i no han pogut, amb senyal i tot. */
  fallades: number;
  motiu: MotiuRepesca;
}

/**
 * Les teves gravacions que encara no tenen lectura de màquina, **les últimes primer**.
 *
 * L'ordre no és capritxós: l'amo ho va demanar així («transcriu primer les últimes que es fan»),
 * i té raó. Qui acaba de gravar una frase amb algú al davant la vol mirar ARA, per saber si el
 * que ha quedat val o cal tornar-la a dir. Una de fa tres setmanes pot esperar.
 */
export async function lecturesQueFalten(): Promise<Drill[]> {
  const jo = (localStorage.getItem('user_name') || '').trim();
  if (!jo) return [];
  const locals = await drillsLocals().catch(() => [] as Drill[]);
  const quan = (d: Drill) => Date.parse(d.date_created || '') || d.id || 0;
  return locals
    .filter((d) => (d.author || '').trim() === jo
      && (d.audio_url || '').trim()
      && !(d.text_tachelhit_suggested || '').trim())
    .sort((a, b) => quan(b) - quan(a));
}

/**
 * Demana la lectura de les que en falten i la desa.
 *
 * No llança mai: si el servidor no hi és, ja es tornarà a provar el cop següent. El que torna
 * serveix per dir-ho —qui ho crida decideix si val la pena molestar— i distingeix «no hi havia
 * res a fer» de «no he pogut fer res», que abans eren el mateix zero.
 */
export async function posaLesLecturesQueFalten(limit = CADA_COP): Promise<Repesca> {
  if (!(localStorage.getItem('user_name') || '').trim()) {
    // Sense nom no se sap quines frases són teves, i la repesca no pot fer res. Es compten igual
    // les que esperen lectura, perquè avisar-ne només té sentit si n'hi ha cap.
    const locals = await drillsLocals().catch(() => [] as Drill[]);
    const orfes = locals.filter((d) => (d.audio_url || '').trim()
      && !(d.text_tachelhit_suggested || '').trim()).length;
    return { fetes: 0, falten: orfes, fallades: 0, motiu: 'sense-nom' };
  }
  if (!(await enLinia())) {
    const pendents = await lecturesQueFalten();
    return { fetes: 0, falten: pendents.length, fallades: 0, motiu: 'sense-senyal' };
  }
  const totes = await lecturesQueFalten();
  if (!totes.length) return { fetes: 0, falten: 0, fallades: 0, motiu: 'res-a-fer' };

  const falten = totes.slice(0, limit);
  let fetes = 0;
  let fallades = 0;
  for (const d of falten) {
    const r = await demanaLectura(d.audio_url as string);
    if (!r.ok) { fallades++; continue; }
    const cos: Record<string, unknown> = { text_tachelhit_suggested: r.text, quiet: true };
    if (r.significat) cos.esborranys = esborranysAmb(d.esborranys, r.text, r.significat);
    try {
      await axios.put(`${API_BASE}/drills/${d.id}`, cos);
      fetes++;
    } catch { fallades++; }
  }
  if (fetes) await sincronitza().catch(() => {});
  return { fetes, falten: totes.length - fetes, fallades, motiu: 'fet' };
}
