import axios from 'axios';
import { Network } from '@capacitor/network';
import { API_BASE } from '../config';
import { toast } from '../toast';
import { whyItFailed } from '../utils/errors';

// Demanar a la màquina què diu una gravació, i **dir sempre què ha passat** (#556).
//
// L'amo (2-11-2026): «when it records, if the transcription haven't happened, give me a message».
// Tenia tota la raó i el problema era pitjor del que semblava: hi havia quatre camins de
// gravació i tots quatre callaven. El creador de frases feia `catch {}` i llençava el motiu que
// donava el servidor; la repesca feia `catch {}` i no deia ni quantes n'havia fet; el diàleg de veus
// i el micròfon de la graella no demanaven cap lectura. Qui gravava veia «Escoltant el que has
// gravat…», l'avís s'apagava, i no hi havia manera de saber si hi havia lectura, si arribaria, o
// si no vindria mai.
//
// Això és l'únic lloc que crida `/transcribe/` **des d'un camí de gravació**. Hi ha dos botons
// més que el criden (`DrillsGrid` i `MobileDrillEditor`), i aquells es queden com són: són un
// «transcriu això» que has premut tu, i ja diuen sempre com ha anat.
//
// Torna per què no ha pogut, i si val la pena tornar-hi: no és el mateix no tenir senyal —la
// gravació és desada i la repesca la recollirà— que haver gravat dos segons de vent, que per
// molt que s'hi torni dirà el mateix.
//
// La lectura va a `text_tachelhit_suggested` i el seu significat a `esborranys`, mai als camps
// del parlant (ADR 0003).
//
// Des del #575, el servidor també desa pel seu compte **qui** ha llegit, **què** ha dit i
// **quan**, al mateix camp `esborranys`. Per això la resposta torna el camp ja desat i tot el que
// s'hi afegeixi des d'aquí ha de partir d'aquell, no de la còpia que tenia la pantalla: aquella
// és d'abans de la lectura, i desar-la esborraria el rastre.

/** Com es marca el significat que surt de la nostra pròpia lectura, i no de l'àrab ni d'una persona. */
export const MODEL_SIGNIFICAT = 'NLLB, des de la nostra lectura';

export type Lectura =
  | { ok: true; text: string; significat: string | null;
      /**
       * El camp `esborranys` de la frase tal com ha quedat **al servidor** després d'escriure-hi
       * aquesta lectura (#575), o `null` si no s'hi ha desat res.
       *
       * S'ha de fer servir com a base per a tot el que s'hi afegeixi després. La còpia que té la
       * pantalla és d'abans de la lectura, i desar-la trepitjaria el rastre que el servidor
       * acaba d'escriure: qui ha llegit, què ha dit i quan.
       */
      esborranys: string | null }
  | { ok: false; motiu: string; tornara: boolean };

const enLinia = () => Network.getStatus().then((s) => s.connected).catch(() => false);

/**
 * El que la màquina sent a `audioUrl`, i què en vol dir.
 *
 * No llança mai: el resultat sempre es pot ensenyar. Si la lectura surt, el significat és un
 * extra —quan el traductor no hi és, la lectura ja val per ella mateixa.
 *
 * `drillId` és de quina frase és aquesta gravació, i serveix per a dues coses: la seva varietat
 * tria el lector, i el servidor hi desa el rastre de qui ha llegit (#575). **Només s'hi passa
 * quan la gravació és la veu d'aquella frase**: si és una presa més, el rastre diria que la
 * frase s'ha llegit d'un so que no és el seu.
 */
export async function demanaLectura(audioUrl: string, drillId?: number): Promise<Lectura> {
  if (!(await enLinia())) {
    return { ok: false, tornara: true,
             motiu: 'Ara no hi ha senyal. La gravació és desada i es llegirà quan en torni.' };
  }
  let text = '';
  let esborranys: string | null = null;
  try {
    const r = await axios.post(`${API_BASE}/transcribe/`, { audio_url: audioUrl, drill_id: drillId });
    text = (r.data?.corrected_transcription || '').trim();
    esborranys = (r.data?.esborranys || '').trim() || null;
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status;
    // Un 502 vol dir que els lectors han escoltat i no hi han entès res: tornar-hi amb el mateix
    // fitxer donarà el mateix. Qualsevol altra cosa (500, temps esgotat, l'Space adormit) sí que
    // val la pena tornar-la a provar, i la repesca ho farà sola.
    return { ok: false, tornara: status !== 502,
             motiu: whyItFailed(err, 'No s’ha pogut llegir la gravació') };
  }
  if (!text) {
    // Un servidor d'abans del #556 contesta 200 amb la lectura buida. Es tracta igual.
    return { ok: false, tornara: false, motiu: 'Cap dels lectors no ha entès la gravació.' };
  }
  let significat: string | null = null;
  try {
    const tr = await axios.post(`${API_BASE}/translate`, {
      text, source_lang: 'shi', target_lang: 'ca',
    });
    significat = (tr.data?.translated_text || '').trim() || null;
  } catch { /* sense significat, la lectura ja val per ella mateixa */ }
  return { ok: true, text, significat, esborranys };
}

/**
 * Diu-ho. Sempre.
 *
 * Quan va bé l'avís recorda que allò és de la màquina i que s'ha de mirar; quan no, diu el motiu
 * i si tornarà a provar-se sola, perquè la pregunta que es fa qui acaba de gravar és «he de fer
 * res?».
 */
export function avisaDeLaLectura(r: Lectura): void {
  if (r.ok) {
    toast.info(`La màquina hi ha entès: «${r.text}». Mira-ho abans de donar-ho per bo.`);
  } else if (r.tornara) {
    toast.info(`Sense lectura de la màquina: ${r.motiu}`);
  } else {
    toast.error(`${r.motiu} La gravació és desada; si vols que es llegeixi, torna-la a dir més a prop.`);
  }
}

/** Les dues coses alhora, que és el que volen tots els camins de gravació. */
export async function llegeixIAvisa(audioUrl: string, drillId?: number): Promise<Lectura> {
  const r = await demanaLectura(audioUrl, drillId);
  avisaDeLaLectura(r);
  return r;
}

/**
 * Els esborranys d'una frase amb el significat d'aquesta lectura posat al seu lloc.
 *
 * Es treu el que hi hagués del mateix model —un significat vell d'una lectura vella no diu res—
 * i es desa amb la lectura d'on surt, perquè es pugui jutjar.
 *
 * `esborranysActuals` ha de ser el camp **tal com l'ha tornat la lectura** (`Lectura.esborranys`)
 * quan n'hi hagi: la còpia que té la pantalla és d'abans, i desar-la esborraria el rastre de qui
 * acaba de llegir (#575).
 */
export function esborranysAmb(esborranysActuals: string | null | undefined,
                              lectura: string, significat: string): string {
  let esb: unknown[] = [];
  try {
    const vell = JSON.parse(esborranysActuals || '[]');
    if (Array.isArray(vell)) {
      esb = vell.filter((x) => (x as { model?: string })?.model !== MODEL_SIGNIFICAT);
    }
  } catch { esb = []; }
  esb.push({ text: significat, model: MODEL_SIGNIFICAT, llengua: 'ca',
             de: 'la nostra lectura', lectura });
  return JSON.stringify(esb);
}
