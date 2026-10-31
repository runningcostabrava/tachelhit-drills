import { useSyncExternalStore } from 'react';
import { Capacitor } from '@capacitor/core';
import { Directory, Filesystem } from '@capacitor/filesystem';
import { Network } from '@capacitor/network';
import { getMediaUrl, isNativeApp } from '../config';
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
const CARPETA = 'media';

/** `url` és la que té el drill, tal com surt de `getMediaUrl`, encara que se n'hagi baixat una altra. */
interface Baixat { id: number; url: string; fitxer: string }

/** Prou per trobar el so d'un drill; les pantalles del curs no porten el `Drill` sencer. */
type AmbVeu = Pick<Drill, 'id' | 'audio_url' | 'audio_tts_shi_url'>;

export interface EstatAudio {
  /** El que s'ha de donar a `new Audio()`: el fitxer si hi és, l'URL si no. */
  src: string;
  baixat: boolean;
  /** Fals sense xarxa ni fitxer: el botó surt apagat. */
  disponible: boolean;
}

const perId = new Map<number, Baixat>();
const perUrl = new Map<string, Baixat>();
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
      const req = indexedDB.open(BD, 1);
      req.onupgradeneeded = () => { req.result.createObjectStore(AUDIOS, { keyPath: 'id' }); };
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

/** Sense IndexedDB el fitxer val mentre duri la sessió: el pitjor cas és tornar-lo a baixar. */
async function escriuIndex(fila: Baixat) {
  const db = await obre();
  db?.transaction(AUDIOS, 'readwrite').objectStore(AUDIOS).put(fila);
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
  const noms = await Filesystem.readdir({ path: CARPETA, directory: Directory.Data })
    .then(r => new Set(r.files.map(f => f.name)))
    .catch(() => new Set<string>());
  (await indexDesat()).filter(f => noms.has(f.fitxer)).forEach(registra);
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
  const fila = perUrl.get(clau(url));
  return fila && carpeta ? Capacitor.convertFileSrc(`${carpeta}/${fila.fitxer}`) : null;
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

/** Quantes veus hi ha al disc i quant ocupen. Es compta la carpeta, no l'índex: és el que val. */
export async function resumAudios(): Promise<{ fitxers: number; bytes: number }> {
  if (!isNativeApp()) return { fitxers: 0, bytes: 0 };
  await engegaAudios();
  const r = await Filesystem.readdir({ path: CARPETA, directory: Directory.Data }).catch(() => null);
  if (!r) return { fitxers: 0, bytes: 0 };
  return { fitxers: r.files.length, bytes: r.files.reduce((n, f) => n + (f.size || 0), 0) };
}

/** Esborra totes les veus del disc i l'índex: els botons tornen a dir «sense baixar». */
export async function alliberaAudios(): Promise<void> {
  if (!isNativeApp()) return;
  aturar = true;
  await Filesystem.rmdir({ path: CARPETA, directory: Directory.Data, recursive: true }).catch(() => {});
  perId.clear();
  perUrl.clear();
  const base = await obre();
  if (base) {
    await new Promise<void>(resolve => {
      const tx = base.transaction(AUDIOS, 'readwrite');
      tx.objectStore(AUDIOS).clear();
      tx.oncomplete = () => resolve();
      tx.onerror = () => resolve();
    });
  }
  avisa();
}
