import axios from 'axios';
import { Network } from '@capacitor/network';
import { API_BASE } from '../config';
import type { Drill } from '../types';
import { drillsLocals, sincronitza } from './biblioteca';

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

/** Quantes se'n miren de cada vegada. Poques: això corre de fons i no ha de fer nosa. */
const CADA_COP = 8;
const MODEL_SIGNIFICAT = 'NLLB, des de la nostra lectura';

const enLinia = () => Network.getStatus().then((s) => s.connected).catch(() => false);

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
 * Demana la lectura de les que en falten i la desa. Torna quantes n'ha fet.
 * No llança mai: si el servidor no hi és, ja es tornarà a provar el cop següent.
 */
export async function posaLesLecturesQueFalten(limit = CADA_COP): Promise<number> {
  if (!(await enLinia())) return 0;
  const falten = (await lecturesQueFalten()).slice(0, limit);
  let fetes = 0;
  for (const d of falten) {
    try {
      const r = await axios.post(`${API_BASE}/transcribe/`, { audio_url: d.audio_url });
      const text = (r.data?.corrected_transcription || '').trim();
      if (!text) continue;
      const cos: Record<string, unknown> = { text_tachelhit_suggested: text, quiet: true };
      try {
        const tr = await axios.post(`${API_BASE}/translate`, {
          text, source_lang: 'shi', target_lang: 'ca',
        });
        const ca = (tr.data?.translated_text || '').trim();
        if (ca) {
          let esb: unknown[] = [];
          try {
            const vell = JSON.parse(d.esborranys || '[]');
            if (Array.isArray(vell)) esb = vell.filter((x) => (x as { model?: string })?.model !== MODEL_SIGNIFICAT);
          } catch { esb = []; }
          esb.push({ text: ca, model: MODEL_SIGNIFICAT, llengua: 'ca', de: 'la nostra lectura', lectura: text });
          cos.esborranys = JSON.stringify(esb);
        }
      } catch { /* sense significat, la lectura ja val per ella mateixa */ }
      await axios.put(`${API_BASE}/drills/${d.id}`, cos);
      fetes++;
    } catch { /* el cop següent */ }
  }
  if (fetes) await sincronitza().catch(() => {});
  return fetes;
}
