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
export async function buida(): Promise<{ pujades: number; fallades: number }> {
  if (buidant) return { pujades: 0, fallades: 0 };
  buidant = true;
  let pujades = 0;
  let fallades = 0;
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
  return { pujades, fallades };
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
