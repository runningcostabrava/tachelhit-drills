import { useSyncExternalStore } from 'react';
import { Capacitor } from '@capacitor/core';
import { Directory, Filesystem } from '@capacitor/filesystem';
import { Network } from '@capacitor/network';
import { getMediaUrl, isNativeApp, thumb } from '../config';
import type { Drill } from '../types';

// L'àudio al dispositiu (#506, ADR 0008, pas 2).
//
// Abans es baixava tot sol a cada obertura, passant per base64, i gairebé cap pantalla no llegia
// el fitxer. Aquí només es baixa el que es demana, directament a disc, i totes les pantalles
// pregunten el mateix: `audioSrc` dins d'un gestor, `useAudioSrc` per pintar el botó.
//
// El fitxer es diu `media/<id>.<ext>`, pel drill i no per l'últim tros de l'URL (les de Wikimedia
// porten `?utm_…` al nom). Però es busca **per l'URL**, per dues raons: moltes pantalles només
// tenen l'URL a la mà (les línies del Mètode, les paraules de l'alfabet), i si algú torna a gravar
// un drill l'URL canvia i el fitxer vell ja no respon: mai no sonarà una veu que ja no és la bona.
//
// L'índex viu a IndexedDB, que a iOS es pot esborrar si el disc s'omple (ADR 0008). Llavors els
// fitxers hi són però no se sap de quin URL surten: es tornen a baixar i se substitueixen.

const BD = 'audios-baixats';
const AUDIOS = 'audios';
/**
 * La resta de mèdia d'un drill: el significat llegit en català i la imatge (#506).
 *
 * Va en un magatzem a part perquè el dels àudios té la frase per clau —un sol fitxer per frase—
 * i d'això n'hi ha tres. Aquí la clau és l'adreça, que és també com ho busquen les pantalles.
 * Afegir-lo no toca el que ja és baixat: la veu del parlant es queda on era.
 */
const EXTRES = 'extres';
const CARPETA = 'media';

/** `url` és la que té el drill, tal com surt de `getMediaUrl`, encara que se n'hagi baixat una altra. */
interface Baixat { id: number; url: string; fitxer: string }
interface Extra { url: string; fitxer: string }

/** Prou per trobar el so d'un drill; les pantalles del curs no porten el `Drill` sencer. */
type AmbVeu = Pick<Drill, 'id' | 'audio_url' | 'audio_tts_shi_url'>;
/** El que es baixa a part: el català llegit i la imatge. */
type AmbExtres = Pick<Drill, 'id' | 'audio_tts_url' | 'image_url'>;

export interface EstatAudio {
  /** El que s'ha de donar a `new Audio()`: el fitxer si hi és, l'URL si no. */
  src: string;
  baixat: boolean;
  /** Fals sense xarxa ni fitxer: el botó surt apagat. */
  disponible: boolean;
}

const perId = new Map<number, Baixat>();
const perUrl = new Map<string, Baixat>();
/** El català llegit i les imatges, per adreça. */
const extres = new Map<string, Extra>();
const enCurs = new Map<number, Promise<boolean>>();
const oients = new Set<() => void>();
/** Fins que la xarxa no digui el contrari: millor un botó encès que no fa res que l'app apagada. */
let enLinia = true;
/** Canvia a cada novetat, perquè React sàpiga quan ha de tornar a preguntar. */
let versio = 0;
/** La carpeta es calcula a cada arrencada: a iOS el camí absolut canvia en actualitzar l'app. */
let carpeta: string | null = null;
let llest: Promise<void> | null = null;
let bd: Promise<IDBDatabase | null> | null = null;

function avisa() {
  versio++;
  oients.forEach(o => o());
}

function obre(): Promise<IDBDatabase | null> {
  bd ??= new Promise(resolve => {
    try {
      const req = indexedDB.open(BD, 2);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(AUDIOS)) db.createObjectStore(AUDIOS, { keyPath: 'id' });
        if (!db.objectStoreNames.contains(EXTRES)) db.createObjectStore(EXTRES, { keyPath: 'url' });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
      req.onblocked = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
  return bd;
}

async function indexDesat(): Promise<Baixat[]> {
  const db = await obre();
  if (!db) return [];
  return new Promise(resolve => {
    const req = db.transaction(AUDIOS).objectStore(AUDIOS).getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => resolve([]);
  });
}

async function extresDesats(): Promise<Extra[]> {
  const db = await obre();
  if (!db || !db.objectStoreNames.contains(EXTRES)) return [];
  return new Promise(resolve => {
    const req = db.transaction(EXTRES).objectStore(EXTRES).getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => resolve([]);
  });
}

/** Sense IndexedDB el fitxer val mentre duri la sessió: el pitjor cas és tornar-lo a baixar. */
async function escriuIndex(fila: Baixat) {
  const db = await obre();
  db?.transaction(AUDIOS, 'readwrite').objectStore(AUDIOS).put(fila);
}

async function escriuExtra(fila: Extra) {
  const db = await obre();
  if (db?.objectStoreNames.contains(EXTRES)) {
    db.transaction(EXTRES, 'readwrite').objectStore(EXTRES).put(fila);
  }
}

function registra(fila: Baixat) {
  const vella = perId.get(fila.id);
  if (vella) perUrl.delete(vella.url);
  perId.set(fila.id, fila);
  perUrl.set(fila.url, fila);
}

async function carrega() {
  const uri = await Filesystem.getUri({ path: CARPETA, directory: Directory.Data });
  carpeta = uri.uri;
  // La carpeta encara no existeix fins a la primera baixada.
  const llista = await Filesystem.readdir({ path: CARPETA, directory: Directory.Data })
    .then(r => r.files)
    .catch(() => [] as { name: string; size?: number }[]);
  const noms = new Set(llista.map(f => f.name));
  (await indexDesat()).filter(f => noms.has(f.fitxer)).forEach(registra);
  (await extresDesats()).filter(f => noms.has(f.fitxer)).forEach(f => extres.set(f.url, f));
  await treuLaRuna(llista);
}

/** Els noms que la versió d'ara sap fer: `<id>.<ext>`, `<id>-ca.<ext>`, `<id>-img.<ext>`. */
const NOM_BO = /^\d+(-ca|-img)?\.[a-z0-9]+$/i;

/**
 * Treu els fitxers que cap camí del codi d'ara no pot trobar mai.
 *
 * Una versió antiga desava els fitxers amb el nom de l'adreça —les de Wikimedia hi porten
 * `?utm_source=…` i tot— i la d'ara els desa pel número de la frase. Els vells s'hi van quedar:
 * al telèfon de l'amo eren **14.904 fitxers de 17.685**, la major part dels 936 MB, i el comptador
 * de la pantalla «Al telèfon» els comptava com si fossin veus: deia «17.685 de 10.844 · totes les
 * gravacions són al telèfon» quan només n'hi havia 2.781.
 *
 * Es mira NOMÉS el nom, no l'índex. Si algun dia IndexedDB s'esborra —a iOS pot passar si el disc
 * s'omple— l'índex queda buit i tots els fitxers semblarien orfes: esborrar-los per això seria
 * llençar un giga de veus bones. Un nom que la versió d'ara no sap fer, en canvi, és antic amb
 * índex o sense.
 */
async function treuLaRuna(llista: { name: string; size?: number }[]) {
  const vells = llista.filter(f => !NOM_BO.test(f.name));
  if (!vells.length) return;
  let fets = 0;
  for (const f of vells) {
    const ok = await Filesystem.deleteFile({ path: `${CARPETA}/${f.name}`, directory: Directory.Data })
      .then(() => true).catch(() => false);
    if (ok) fets++;
  }
  console.info(`[Mèdia] ${fets} fitxers d'una versió antiga, trets de ${CARPETA}`);
  avisa();
}

/** Una vegada, en obrir l'app. Els botons ja tornen a preguntar sols quan acaba. */
export function engegaAudios(): Promise<void> {
  llest ??= (async () => {
    const posa = (connectat: boolean) => {
      if (connectat !== enLinia) { enLinia = connectat; avisa(); }
    };
    Network.addListener('networkStatusChange', s => posa(s.connected)).catch(() => {});
    await Network.getStatus().then(s => posa(s.connected)).catch(() => {});
    if (!isNativeApp()) return;
    await carrega().catch(e => console.warn("[Àudio] L'índex no es pot llegir:", e));
    avisa();
  })();
  return llest;
}

/** La veu que es baixa d'un drill: la gravació d'una persona, i cap més.
 *
 *  La veu sintètica en amazic ja no sona enlloc (#532) i no s'ha de baixar: ocuparia disc per
 *  no sonar mai. `audio_tts_url` és el significat llegit en CATALÀ i tampoc no és aquesta veu. */
const veuDe = (d: Partial<AmbVeu>) => (d.audio_url || '').trim();

const clau = (url: string | null | undefined) => getMediaUrl((url || '').trim());

/** El fitxer d'aquesta adreça, ja a punt per a `new Audio()`, o `null` si no s'ha baixat. */
export function rutaLocal(url: string | null | undefined): string | null {
  const k = clau(url);
  const fila = perUrl.get(k) || extres.get(k);
  return fila && carpeta ? Capacitor.convertFileSrc(`${carpeta}/${fila.fitxer}`) : null;
}

/**
 * D'on surt una imatge: el fitxer del telèfon si ja és baixat, i si no la de Cloudinary retallada.
 *
 * `thumb` no toca un camí local —només reescriu adreces de Cloudinary—, però es demana el fitxer
 * primer perquè sense xarxa la retallada no existeix i la local sí.
 */
export function imatgeSrc(url: string | null | undefined, amplada: number): string {
  return rutaLocal(url) ?? thumb(clau(url), amplada);
}

/** Per a gestors i bucles, on un hook no hi cap. Si no hi ha fitxer ni xarxa, simplement no sona. */
export function audioSrc(url: string | null | undefined): string {
  return rutaLocal(url) ?? clau(url);
}

export function estatAudio(url: string | null | undefined): EstatAudio {
  const local = rutaLocal(url);
  if (local) return { src: local, baixat: true, disponible: true };
  const src = clau(url);
  // Una gravació que encara no ha pujat ja és al dispositiu, encara que no sigui a `media/`.
  return { src, baixat: false, disponible: !!src && (enLinia || /^(blob|data):/.test(src)) };
}

const subscriu = (oient: () => void) => {
  oients.add(oient);
  return () => { oients.delete(oient); };
};

/** Un sol lloc per preguntar d'on surt el so. Accepta un drill o, si només hi ha això, l'adreça. */
export function useAudioSrc(font: Partial<AmbVeu> | string | null | undefined): EstatAudio {
  useSyncExternalStore(subscriu, () => versio);
  return estatAudio(typeof font === 'string' || !font ? font : veuDe(font));
}

/** Fins que no se sàpiga què sona a iOS (pas 0, sense provar), es baixa en mp3. */
const NO_SEGUR = new Set(['webm', 'flac']);
const CLOUDINARY = /^(https:\/\/res\.cloudinary\.com\/[^/]+\/video\/upload\/)(.+)\.[a-z0-9]+$/i;

/**
 * Què es baixa d'una adreça i amb quina extensió es desa.
 *
 * El `webm` i el `flac` de Cloudinary es demanen en mp3 a tots els telèfons: un sol camí per
 * provar, i el fitxer val igual a Android i a iOS. Fora de Cloudinary no hi ha qui els converteixi
 * i es baixa l'original, que a Android sona i a iOS no ho sabem.
 */
export function aBaixar(url: string): { url: string; ext: string } {
  const net = url.split(/[?#]/)[0];
  const ext = /\.([a-z0-9]{2,5})$/i.exec(net)?.[1].toLowerCase() || 'mp3';
  const cld = NO_SEGUR.has(ext) ? CLOUDINARY.exec(net) : null;
  return cld ? { url: `${cld[1]}f_mp3/${cld[2]}.mp3`, ext: 'mp3' } : { url, ext };
}

async function baixa(id: number, font: string): Promise<boolean> {
  try {
    const { url, ext } = aBaixar(font);
    const fitxer = `${id}.${ext}`;
    const path = `${CARPETA}/${fitxer}`;
    await Filesystem.downloadFile({ url, path, directory: Directory.Data, recursive: true });
    const { size } = await Filesystem.stat({ path, directory: Directory.Data });
    if (!size) throw new Error('fitxer buit');
    const vella = perId.get(id);
    if (vella && vella.fitxer !== fitxer) {
      await Filesystem.deleteFile({ path: `${CARPETA}/${vella.fitxer}`, directory: Directory.Data }).catch(() => {});
    }
    const fila = { id, url: font, fitxer };
    registra(fila);
    await escriuIndex(fila);
    avisa();
    return true;
  } catch (e) {
    console.warn(`[Àudio] El drill ${id} no s'ha pogut baixar:`, e);
    return false;
  }
}

/**
 * Baixa la veu d'un drill. Només en surt de demanar-ho: res no ho crida sol.
 * Al web no fa res, perquè no hi ha disc on desar-la.
 */
export async function baixaAudio(d: AmbVeu): Promise<boolean> {
  if (!isNativeApp()) return false;
  const font = clau(veuDe(d));
  if (!/^https?:/.test(font)) return false;
  await engegaAudios();
  if (perUrl.has(font)) return true;
  let feina = enCurs.get(d.id);
  if (!feina) {
    feina = baixa(d.id, font).finally(() => { enCurs.delete(d.id); });
    enCurs.set(d.id, feina);
  }
  return feina;
}

// ─────────────────────────── Totes les veus, d'una tirada (#506, pas 3) ───────────────────────────
//
// En Pablo (31-10): «I need a system that have the audios, I should be able to download them all to
// the phone». Són unes 7.000 gravacions i ~0,3 GB: no es pot fer d'un sol cop a la memòria ni en
// paral·lel. Es baixen d'una en una (dues alhora com a molt), es pot aturar i reprendre, i el que
// ja hi és no es torna a demanar. El progrés es diu a mesura que va, no al final.

export interface ProgresAudios {
  /** Quantes tenen veu i s'han de baixar en total. */ total: number;
  /** Quantes ja són al disc. */ fetes: number;
  /** Quantes han fallat (es poden reintentar: n'hi ha prou de tornar a començar). */ fallades: number;
  /** Bytes que ocupa el que s'ha baixat en aquesta tanda. */ bytes: number;
  corrent: boolean;
}

let aturar = false;
let tanda: Promise<ProgresAudios> | null = null;

/** Atura la baixada que corre. El que ja és a disc s'hi queda. */
export function aturaBaixada() { aturar = true; }

export function baixantAudios(): boolean { return !!tanda; }

/**
 * Baixa la veu de tots els drills que en tenen i encara no són al disc.
 *
 * `avisa` es crida després de cada fitxer perquè la pantalla pugui dir per on va. Torna el
 * resum final. Si ja n'hi ha una de corrent, s'hi enganxa en comptes de començar-ne una altra.
 */
export async function baixaTotsElsAudios(
  drills: Partial<AmbVeu>[],
  passa?: (p: ProgresAudios) => void,
): Promise<ProgresAudios> {
  if (tanda) return tanda;
  aturar = false;
  tanda = (async () => {
    const p: ProgresAudios = { total: 0, fetes: 0, fallades: 0, bytes: 0, corrent: true };
    if (!isNativeApp()) return { ...p, corrent: false };
    await engegaAudios();
    const falten: { id: number; font: string }[] = [];
    for (const d of drills) {
      const font = clau(veuDe(d));
      if (!/^https?:/.test(font) || d.id == null) continue;
      p.total++;
      if (perUrl.has(font)) p.fetes++;
      else falten.push({ id: d.id, font });
    }
    passa?.({ ...p });
    for (const { id, font } of falten) {
      if (aturar) break;
      const ok = await baixa(id, font);
      if (ok) {
        p.fetes++;
        const fila = perId.get(id);
        if (fila) {
          const { size } = await Filesystem.stat({ path: `${CARPETA}/${fila.fitxer}`, directory: Directory.Data }).catch(() => ({ size: 0 }));
          p.bytes += size || 0;
        }
      } else p.fallades++;
      passa?.({ ...p });
    }
    return { ...p, corrent: false };
  })().finally(() => { tanda = null; aturar = false; avisa(); });
  return tanda;
}

// ──────────────── El català llegit i les imatges (#506: «que tot sigui accessible») ────────────────
//
// En Pablo (31-10): «comprova que és capaç de descarregar tot, que tot és accessible» i «make sure
// everything works offline in the phone». Faltaven dues coses: el significat llegit en CATALÀ
// —que és el que fa sonar «Escolta-la amb el català» a les Històries i la primera passada de la
// Pràctica— i les imatges de les targetes. Sense xarxa, l'un callava i les altres no es veien.
//
// Va a part de les veus perquè ocupa molt i no tothom el vol: es demana amb el seu botó. La veu
// sintètica en AMAZIC segueix sense baixar-se mai: no sona enlloc (#532) i ocuparia disc per no
// sonar.

export interface ProgresExtres {
  total: number;
  fetes: number;
  fallades: number;
  bytes: number;
  corrent: boolean;
  /** Què s'està baixant: «el català llegit» o «les imatges». */
  ara: string;
}

let aturarE = false;
let tandaE: Promise<ProgresExtres> | null = null;

export function baixantExtres(): boolean { return !!tandaE; }
export function aturaExtres() { aturarE = true; }

/** Baixa el que falta d'una llista d'adreces, amb el nom de fitxer que li toca. */
async function baixaExtra(nom: string, font: string): Promise<number> {
  try {
    const { url, ext } = aBaixar(font);
    const fitxer = `${nom}.${ext}`;
    const path = `${CARPETA}/${fitxer}`;
    await Filesystem.downloadFile({ url, path, directory: Directory.Data, recursive: true });
    const { size } = await Filesystem.stat({ path, directory: Directory.Data });
    if (!size) throw new Error('fitxer buit');
    const fila = { url: font, fitxer };
    extres.set(font, fila);
    await escriuExtra(fila);
    avisa();
    return size;
  } catch (e) {
    console.warn(`[Mèdia] ${nom} no s'ha pogut baixar:`, e);
    return -1;
  }
}

/**
 * Baixa el català llegit i les imatges de tots els drills que en tenen.
 *
 * D'un en un, es pot aturar i reprendre, i el que ja hi és no es torna a demanar — igual que les
 * veus, i pel mateix motiu: el servidor és un Render de 512 MB.
 */
export async function baixaExtresDeTot(
  drills: Partial<AmbExtres>[],
  passa?: (p: ProgresExtres) => void,
): Promise<ProgresExtres> {
  if (tandaE) return tandaE;
  aturarE = false;
  tandaE = (async () => {
    const p: ProgresExtres = { total: 0, fetes: 0, fallades: 0, bytes: 0, corrent: true, ara: '' };
    if (!isNativeApp()) return { ...p, corrent: false };
    await engegaAudios();
    const falten: { nom: string; font: string; qui: string }[] = [];
    for (const d of drills) {
      if (d.id == null) continue;
      for (const [camp, sufix, qui] of [
        ['audio_tts_url', 'ca', 'el català llegit'],
        ['image_url', 'img', 'les imatges'],
      ] as const) {
        const font = clau((d as Record<string, unknown>)[camp] as string | undefined);
        if (!/^https?:/.test(font)) continue;
        p.total++;
        if (extres.has(font)) p.fetes++;
        else falten.push({ nom: `${d.id}-${sufix}`, font, qui });
      }
    }
    passa?.({ ...p });
    for (const { nom, font, qui } of falten) {
      if (aturarE) break;
      p.ara = qui;
      const mida = await baixaExtra(nom, font);
      if (mida >= 0) { p.fetes++; p.bytes += mida; } else p.fallades++;
      passa?.({ ...p });
    }
    return { ...p, ara: '', corrent: false };
  })().finally(() => { tandaE = null; aturarE = false; avisa(); });
  return tandaE;
}

/**
 * Què hi ha al disc: quantes VEUS, quants extres, quants fitxers i quant ocupen.
 *
 * `veus` surt de l'índex i no de comptar la carpeta. Comptar la carpeta era el que hi havia, i
 * mentre només hi hagués veus anava bé; amb les imatges, el català llegit i les restes d'una
 * versió antiga, la pantalla deia «17.685 de 10.844 · totes les gravacions són al telèfon» amb
 * 2.781 veus de debò. Un comptador que menteix cap amunt és pitjor que no tenir-ne.
 */
export async function resumAudios(): Promise<{ fitxers: number; bytes: number; veus: number; extres: number }> {
  if (!isNativeApp()) return { fitxers: 0, bytes: 0, veus: 0, extres: 0 };
  await engegaAudios();
  const r = await Filesystem.readdir({ path: CARPETA, directory: Directory.Data }).catch(() => null);
  const buit = { fitxers: 0, bytes: 0, veus: perId.size, extres: extres.size };
  if (!r) return buit;
  return { ...buit, fitxers: r.files.length, bytes: r.files.reduce((n, f) => n + (f.size || 0), 0) };
}

/** Esborra totes les veus del disc i l'índex: els botons tornen a dir «sense baixar». */
export async function alliberaAudios(): Promise<void> {
  if (!isNativeApp()) return;
  aturar = true;
  aturarE = true;
  await Filesystem.rmdir({ path: CARPETA, directory: Directory.Data, recursive: true }).catch(() => {});
  perId.clear();
  perUrl.clear();
  extres.clear();
  const base = await obre();
  if (base) {
    await new Promise<void>(resolve => {
      const noms = base.objectStoreNames.contains(EXTRES) ? [AUDIOS, EXTRES] : [AUDIOS];
      const tx = base.transaction(noms, 'readwrite');
      noms.forEach(n => tx.objectStore(n).clear());
      tx.oncomplete = () => resolve();
      tx.onerror = () => resolve();
    });
  }
  avisa();
}
