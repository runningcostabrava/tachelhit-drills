import { Preferences } from '@capacitor/preferences';
import axios from 'axios';
import { API_BASE } from '../config';
import type { Drill } from '../types';
import { fetchAllDrills } from './fetchAllDrills';

// La biblioteca al dispositiu (#506, ADR 0008, pas 1).
//
// Abans cada obertura baixava tots els drills, en 17 pàgines, i els desava a `Preferences`, que al
// web és localStorage: 5 MB per a 14,7 MB de JSON. Aquí la còpia viu a IndexedDB, i després de la
// primera baixada només es demana el que ha canviat. Si IndexedDB no hi és (finestra privada), la
// còpia dura el que dura la pàgina: l'app ha de funcionar igualment.

const BD = 'biblioteca';
const DRILLS = 'drills';
const SYNC = 'sync';
const CLAU_MARCA = 'ultima';
/** La còpia antiga. Es porta aquí una sola vegada i s'esborra. */
const CLAU_ANTIGA = 'cached_drills';
/** El sostre de `GET /drills/tombstones`: si s'hi arriba, n'hi pot haver més que no veiem. */
const SOSTRE_TOMBSTONES = 2000;
/** Un drill desat mentre es baixava pot portar una hora anterior a la del que s'ha rebut. */
const MARGE_MS = 60_000;
/** Quant val una sincronització per a qui només vol la biblioteca en obrir. */
export const OBERTURA_MS = 30_000;

interface Tombstone { drill_id: number; deleted_at: string }

let bd: Promise<IDBDatabase | null> | null = null;
const memoria = new Map<number, Drill>();
let marcaMemoria: string | null = null;
let enCurs: Promise<void> | null = null;
let acabadaA = 0;

function obre(): Promise<IDBDatabase | null> {
  bd ??= new Promise(resolve => {
    try {
      const req = indexedDB.open(BD, 1);
      req.onupgradeneeded = () => {
        req.result.createObjectStore(DRILLS, { keyPath: 'id' });
        req.result.createObjectStore(SYNC);
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

function promesa<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function acabada(tx: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error);
  });
}

async function escriu(canvis: { buida?: boolean; desa?: Drill[]; treu?: number[]; marca?: string }) {
  const db = await obre();
  if (!db) {
    if (canvis.buida) memoria.clear();
    canvis.desa?.forEach(d => memoria.set(d.id, d));
    canvis.treu?.forEach(id => memoria.delete(id));
    if (canvis.marca) marcaMemoria = canvis.marca;
    return;
  }
  // Una sola transacció: si el dispositiu cau a mig escriure, la marca no avança sense les files.
  const tx = db.transaction([DRILLS, SYNC], 'readwrite');
  const drills = tx.objectStore(DRILLS);
  if (canvis.buida) drills.clear();
  canvis.desa?.forEach(d => drills.put(d));
  canvis.treu?.forEach(id => drills.delete(id));
  if (canvis.marca) tx.objectStore(SYNC).put(canvis.marca, CLAU_MARCA);
  await acabada(tx);
}

async function marcaDesada(): Promise<string | null> {
  const db = await obre();
  if (!db) return marcaMemoria;
  const valor = await promesa(db.transaction(SYNC).objectStore(SYNC).get(CLAU_MARCA));
  return typeof valor === 'string' ? valor : null;
}

/** El servidor desa hores UTC sense zona; `Date` les llegiria com a locals. */
const instant = (s: string) => Date.parse(/(z|[+-]\d\d:\d\d)$/i.test(s) ? s : `${s}Z`);

/** La marca surt de les hores del servidor, mai del rellotge del telèfon. */
function novaMarca(anterior: string | null, drills: Drill[], morts: Tombstone[]): string | null {
  const hores = [
    ...drills.map(d => instant(d.updated_at || d.date_created)),
    ...morts.map(t => instant(t.deleted_at)),
  ].filter(Number.isFinite);
  if (!hores.length) return anterior;
  // Una fila amb data futura no pot deixar la marca per davant de tot el que vingui després.
  const nova = Math.min(Math.max(...hores), Date.now()) - MARGE_MS;
  return anterior && instant(anterior) >= nova ? anterior : new Date(nova).toISOString();
}

async function baixadaSencera() {
  const drills = await fetchAllDrills();
  await escriu({ buida: true, desa: drills, marca: novaMarca(null, drills, []) ?? undefined });
}

async function baixadaDelta(marca: string) {
  const [drills, morts] = await Promise.all([
    fetchAllDrills({ since: marca }),
    axios.get<Tombstone[]>(`${API_BASE}/drills/tombstones`, { params: { since: marca } }).then(r => r.data),
  ]);
  if (morts.length >= SOSTRE_TOMBSTONES) return baixadaSencera();
  const vius = new Set(drills.map(d => d.id));
  await escriu({
    desa: drills,
    treu: morts.map(t => t.drill_id).filter(id => !vius.has(id)),
    marca: novaMarca(marca, drills, morts) ?? undefined,
  });
}

/** La còpia de `Preferences` passa aquí una vegada: sense marca, la xarxa la substituirà. */
async function migra() {
  const { value } = await Preferences.get({ key: CLAU_ANTIGA });
  if (value === null) return;
  try {
    if (!(await drillsLocals()).length) await escriu({ desa: JSON.parse(value) });
  } catch (e) {
    console.warn('[Biblioteca] La còpia antiga no es pot llegir:', e);
  }
  await Preferences.remove({ key: CLAU_ANTIGA });
}

/** Tot el que hi ha al dispositiu. No toca la xarxa. */
export async function drillsLocals(): Promise<Drill[]> {
  const db = await obre();
  return db ? promesa(db.transaction(DRILLS).objectStore(DRILLS).getAll()) : [...memoria.values()];
}

/** Desa o substitueix files sense tocar la marca: és la feina d'un canvi local. */
export const desaDrills = (drills: Drill[]) => escriu({ desa: drills });

export const treuDrill = (id: number) => escriu({ treu: [id] });

/**
 * Posa la còpia al dia. Falla sense xarxa, i la còpia es queda com estava.
 * En obrir l'app, tant l'app com la pantalla ho demanen: amb `recent` (ms), n'hi ha prou amb una
 * sincronització acabada fa menys d'això. Després d'una escriptura no s'ha de passar.
 */
export function sincronitza(recent = 0): Promise<void> {
  if (!enCurs && recent && Date.now() - acabadaA < recent) return Promise.resolve();
  enCurs ??= (async () => {
    await migra();
    const marca = await marcaDesada();
    await (marca ? baixadaDelta(marca) : baixadaSencera());
    acabadaA = Date.now();
  })().finally(() => { enCurs = null; });
  return enCurs;
}
