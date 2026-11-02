/**
 * La cua de veus: una presa es desa al dispositiu primer, i puja sola (#370).
 *
 * Fins ara gravar i desar eren una sola cosa que bloquejava: mentre la presa pujava a Cloudinary
 * i s'escrivia a la base de dades, qui havia gravat esperava amb la pantalla aturada. A mig
 * poble, amb la cobertura que va i ve, això vol dir perdre la presa — i una presa perduda és una
 * veu que ningú no tornarà a gravar.
 *
 * Aquí la presa es guarda al dispositiu abans de res i la pujada va al seu ritme per darrere.
 * Sense connexió també es pot gravar: la presa espera a la cua i puja quan torna el senyal.
 *
 * **Per què no va a la cua que ja existeix.** `OfflineSyncManager` desa la seva cua a
 * `Preferences`, que al web és `localStorage`: uns 5 MB per a tot l'origen, compartits amb la
 * còpia de la biblioteca. Un àudio en base64 allà dins se la menja de pressa i, quan s'omple,
 * el que es perd no és la cua: és la biblioteca. Les preses viuen a IndexedDB, que no té aquest
 * sostre, i allà hi caben com a blob, sense engreixar-les un terç passant-les a text.
 */
import { API_BASE } from '../config';
import { esborranysAmb, llegeixIAvisa } from './lectura';

const BD = 'veus-pendents';
const MAGATZEM = 'preses';
/** Després de tants intents fallats, la presa es queda però deixa d'intentar-ho sola. */
const MAX_INTENTS = 6;

export interface PresaPendent {
  id: string;
  drillId: number;
  /** El nom que es veurà, per poder dir QUINA frase espera i no només quantes. */
  frase: string;
  blob: Blob;
  tipus: string;
  text?: string;
  variety?: string;
  region?: string;
  isNative?: boolean | null;
  creada: number;
  intents: number;
  ultimError?: string;
}

function obre(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(BD, 1);
    req.onupgradeneeded = () => {
      if (!req.result.objectStoreNames.contains(MAGATZEM)) {
        req.result.createObjectStore(MAGATZEM, { keyPath: 'id' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function fes<T>(mode: IDBTransactionMode, feina: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return obre().then((db) => new Promise<T>((resolve, reject) => {
    const tx = db.transaction(MAGATZEM, mode);
    const req = feina(tx.objectStore(MAGATZEM));
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
    tx.oncomplete = () => db.close();
  }));
}

/** Qui vulgui pintar quantes n'hi ha esperant. */
type Oient = (n: number) => void;
const oients = new Set<Oient>();

export function escolta(o: Oient): () => void {
  oients.add(o);
  pendents().then(o).catch(() => {});
  return () => { oients.delete(o); };
}

async function avisa() {
  const n = await pendents().catch(() => 0);
  oients.forEach((o) => { try { o(n); } catch { /* un oient trencat no atura la cua */ } });
}

export async function pendents(): Promise<number> {
  try {
    const totes = await fes<PresaPendent[]>('readonly', (s) => s.getAll() as IDBRequest<PresaPendent[]>);
    return totes.length;
  } catch {
    return 0;   // sense IndexedDB (finestra privada, permisos) la cua no existeix i no es menteix
  }
}

export async function llista(): Promise<PresaPendent[]> {
  try {
    return await fes<PresaPendent[]>('readonly', (s) => s.getAll() as IDBRequest<PresaPendent[]>);
  } catch {
    return [];
  }
}

/**
 * Desa una presa i prova de pujar-la de seguida.
 *
 * Torna tan bon punt és al dispositiu: qui ha gravat ja pot seguir, i la pujada no el fa esperar.
 */
export async function afegeix(p: Omit<PresaPendent, 'id' | 'creada' | 'intents'>): Promise<string> {
  const id = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  await fes('readwrite', (s) => s.put({ ...p, id, creada: Date.now(), intents: 0 }));
  avisa();
  buida().catch(() => {});
  return id;
}

export async function oblida(id: string) {
  await fes('readwrite', (s) => s.delete(id));
  avisa();
}

let buidant = false;

/**
 * Puja el que hi hagi a la cua, d'una en una.
 *
 * D'una en una i no totes alhora: són fitxers, sovint amb una cobertura dolenta, i sis pujades
 * en paral·lel en una barra de senyal es fan nosa i fallen totes.
 */
export async function buida(): Promise<{ pujades: number; fallades: number; llegides: number }> {
  if (buidant) return { pujades: 0, fallades: 0, llegides: 0 };
  buidant = true;
  let pujades = 0;
  let fallades = 0;
  // Les que han pujat en aquesta passada, per demanar-ne la lectura després. Es fa fora del
  // bucle de pujada: una presa pujada no ha d'esperar que la màquina llegeixi l'anterior.
  const pujat: { drillId: number; audioUrl: string; esPrincipal: boolean }[] = [];
  try {
    for (const p of await llista()) {
      if (p.intents >= MAX_INTENTS) continue;
      try {
        const ext = p.tipus.includes('webm') ? 'webm' : p.tipus.includes('mp4') ? 'mp4' : 'ogg';
        const fd = new FormData();
        fd.append('file', p.blob, `take_${p.drillId}.${ext}`);
        if (p.text) fd.append('text', p.text);
        if (p.variety) fd.append('variety', p.variety);
        if (p.region) fd.append('region', p.region);
        if (p.isNative !== undefined && p.isNative !== null) fd.append('is_native', String(p.isNative));
        const res = await fetch(`${API_BASE}/drills/${p.drillId}/recordings`, { method: 'POST', body: fd });
        if (!res.ok) {
          const detall = await res.json().catch(() => ({} as { detail?: string }));
          throw new Error(detall.detail || `el servidor ha dit ${res.status}`);
        }
        const desada = await res.json().catch(() => null) as
          { audio_url?: string; es_principal?: boolean } | null;
        if (desada?.audio_url) {
          pujat.push({ drillId: p.drillId, audioUrl: desada.audio_url,
                       esPrincipal: !!desada.es_principal });
        }
        await fes('readwrite', (s) => s.delete(p.id));
        pujades += 1;
      } catch (e) {
        // La presa es queda. Un error no li ha de costar la veu a ningú.
        const msg = e instanceof Error ? e.message : 'no s\'ha pogut pujar';
        await fes('readwrite', (s) => s.put({ ...p, intents: p.intents + 1, ultimError: msg }));
        fallades += 1;
      }
    }
  } finally {
    buidant = false;
    avisa();
  }
  return { pujades, fallades, llegides: await lesLlegeix(pujat) };
}

/**
 * I què hi ha entès la màquina de cada presa que ha pujat (#556).
 *
 * Aquest camí —el micròfon que es manté premut a la graella— no demanava cap lectura, i la
 * repesca tampoc no l'agafava: només mira les frases de les quals ets l'autor, i aquí es grava
 * damunt de targetes que són d'altri. Qui prem el micròfon i veu «Veu desada» no sabia si
 * s'entenia res del que havia dit.
 *
 * Amb sostre, i a posta: cada lectura són uns cinc segons de servidor, i obrir l'app amb deu
 * preses a la cua no ha de disparar deu crides ni deu avisos. Les que queden fora les recull la
 * repesca si són teves.
 */
const MAX_LECTURES = 3;

async function lesLlegeix(pujat: { drillId: number; audioUrl: string; esPrincipal: boolean }[]) {
  let llegides = 0;
  for (const q of pujat.slice(0, MAX_LECTURES)) {
    const r = await llegeixIAvisa(q.audioUrl);
    if (!r.ok) continue;
    llegides += 1;
    // Es desa només quan aquesta presa és la veu de la targeta: si no,
    // `text_tachelhit_suggested` parlaria d'una altra gravació.
    if (!q.esPrincipal) continue;
    const cos: Record<string, unknown> = { text_tachelhit_suggested: r.text, quiet: true };
    if (r.significat) cos.esborranys = esborranysAmb(null, r.text, r.significat);
    try {
      await fetch(`${API_BASE}/drills/${q.drillId}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cos),
      });
    } catch { /* la lectura ja s'ha dit; desar-la pot esperar la repesca */ }
  }
  return llegides;
}

/** Torna a provar les que s'havien rendit. */
export async function tornaHiProvar() {
  for (const p of await llista()) {
    if (p.intents >= MAX_INTENTS) await fes('readwrite', (s) => s.put({ ...p, intents: 0 }));
  }
  return buida();
}

/**
 * Engegar la cua: quan torna el senyal, i en obrir l'app.
 *
 * El que fa que una presa no es perdi per tancar l'app és que la cua sigui al dispositiu; el que
 * fa que no es quedi allà per sempre és que algú la miri en tornar a obrir-la.
 */
export function engega() {
  if (typeof window === 'undefined') return;
  window.addEventListener('online', () => { buida().catch(() => {}); });
  buida().catch(() => {});
}
