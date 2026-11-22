/**
 * El cau de lectura: l'última resposta de cada pantalla, desada al telèfon.
 *
 * Fins ara `api.ts` demanava TOTES les peticions amb `cache: 'no-store'`. El motiu era bo —una
 * llista demanada just després d'escriure-hi ha d'arribar del servidor— però la regla valia per
 * a tot, i el resultat era que el telèfon es tornava a baixar cada pantalla cada vegada. Amb el
 * servidor adormit (Render gratuït s'adorm als 15 minuts), això vol dir trenta segons de
 * pantalla buida per començar.
 *
 * Aquí no es canvia qui mana: mana la xarxa. El que es desa és l'última resposta, per tenir què
 * ensenyar mentre el servidor es desperta i per seguir funcionant sense connexió.
 *
 * ON ES DESA. A IndexedDB i no al `localStorage`, perquè la biblioteca sencera són megabytes i
 * el `localStorage` en vol menys de cinc; i no a la Cache API, que demana context segur i a
 * l'Android de Capacitor no sempre el tenim. Si el navegador no en té (mode privat, permisos),
 * tot plegat es queda en no fer res: cap funció d'aquest mòdul no llença mai.
 *
 * DE QUI ÉS. La clau porta el testimoni de qui ho ha demanat: dues persones al mateix telèfon no
 * s'han de veure les llistes l'una de l'altra.
 */

const DB_NAME = 'tachelhit-read-cache';
const DB_VERSION = 1;
const STORE = 'responses';

/** Quant temps es guarda una còpia abans de considerar-la escombraries. */
const MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000;

/** Quantes còpies es guarden. Les més velles cauen primer. */
const MAX_ENTRIES = 300;

export interface CachedRead {
  key: string;
  path: string;
  body: unknown;
  at: number;
  /** Per saber si el que ha arribat després és el mateix o una altra cosa. */
  fingerprint: string;
  /**
   * Una pantalla del curs baixada a posta per tenir-la sense connexió (#506, pas 4).
   *
   * No caduca als 30 dies i no compta per al sostre de 300: qui ha demanat el curs sencer no ha
   * de perdre el capítol 7 perquè després hagi mirat tres-centes frases. Només ho posa
   * `cursOffline`; una resposta que arriba pel camí normal no ho és mai.
   */
  fix?: boolean;
}

/**
 * Una empremta barata del que hi ha desat.
 *
 * No és per seguretat: és per no dir «hi ha dades noves» quan el que ha arribat és idèntic. Es
 * calcula sobre el JSON perquè és el que es desa, i una sola vegada per resposta.
 */
export function fingerprint(body: unknown): string {
  let s: string;
  try {
    s = JSON.stringify(body) ?? '';
  } catch {
    return '';
  }
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return `${s.length}.${(h >>> 0).toString(36)}`;
}

let dbPromise: Promise<IDBDatabase | null> | null = null;

function open(): Promise<IDBDatabase | null> {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve) => {
    try {
      if (typeof indexedDB === 'undefined') { resolve(null); return; }
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) {
          const store = db.createObjectStore(STORE, { keyPath: 'key' });
          store.createIndex('at', 'at');
          store.createIndex('path', 'path');
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
      // Un navegador que demana permís i no el rep es queda aquí per sempre: al cap d'un segon
      // es dóna per no disponible i l'app continua com si no n'hi hagués.
      setTimeout(() => resolve(null), 1000);
    } catch {
      resolve(null);
    }
  });
  return dbPromise;
}

function run<T>(mode: IDBTransactionMode, fn: (store: IDBObjectStore) => IDBRequest<T>): Promise<T | null> {
  return open().then((db) => {
    if (!db) return null;
    return new Promise<T | null>((resolve) => {
      try {
        const tx = db.transaction([STORE], mode);
        const req = fn(tx.objectStore(STORE));
        req.onsuccess = () => resolve(req.result as T);
        req.onerror = () => resolve(null);
        tx.onabort = () => resolve(null);
      } catch {
        resolve(null);
      }
    });
  });
}

/** Qui demana. Dues persones al mateix telèfon no comparteixen cau. */
function who(): string {
  try {
    const t = localStorage.getItem('user_token') || '';
    if (!t) return 'anon';
    // No cal res criptogràfic: només que dos testimonis diferents donin claus diferents.
    let h = 0;
    for (let i = 0; i < t.length; i++) h = (h * 31 + t.charCodeAt(i)) | 0;
    return `u${(h >>> 0).toString(36)}`;
  } catch {
    return 'anon';
  }
}

function keyFor(path: string): string {
  return `${who()} ${path}`;
}

/** La còpia desada d'aquesta petició, si n'hi ha. */
export async function readCached(path: string): Promise<CachedRead | null> {
  const row = await run<CachedRead>('readonly', (s) => s.get(keyFor(path)) as IDBRequest<CachedRead>);
  if (!row) return null;
  if (!row.fix && Date.now() - row.at > MAX_AGE_MS) return null;
  return row;
}

/**
 * Desa l'última resposta. Si no es pot, no passa res.
 *
 * `fix` marca les pantalles del curs baixades a posta: no caduquen ni es poden. Una resposta
 * normal no treu mai la marca d'una de fixa —tornar a obrir el capítol amb xarxa l'actualitza i
 * l'ha de deixar igual de fixa.
 */
export async function writeCached(path: string, body: unknown, fix = false): Promise<void> {
  const key = keyFor(path);
  const abans = fix ? null : await run<CachedRead>('readonly', (s) => s.get(key) as IDBRequest<CachedRead>).catch(() => null);
  await run('readwrite', (s) => s.put({
    key, path, body, at: Date.now(), fingerprint: fingerprint(body), fix: fix || !!abans?.fix,
  }));
}

/**
 * Oblida tot el que penja d'un recurs. Es crida després d'escriure: és el cas que el
 * `cache: 'no-store'` protegia, i l'únic on una còpia vella faria mal de debò (una frase creada
 * correctament que no surt a la llista sembla una frase que no existeix).
 */
export async function dropCached(prefix: string): Promise<void> {
  const db = await open();
  if (!db) return;
  await new Promise<void>((resolve) => {
    try {
      const tx = db.transaction([STORE], 'readwrite');
      const store = tx.objectStore(STORE);
      const req = store.openCursor();
      req.onsuccess = () => {
        const cur = req.result;
        if (!cur) { resolve(); return; }
        const row = cur.value as CachedRead;
        if (typeof row.path === 'string' && row.path.startsWith(prefix)) cur.delete();
        cur.continue();
      };
      req.onerror = () => resolve();
      tx.onabort = () => resolve();
      tx.oncomplete = () => resolve();
    } catch {
      resolve();
    }
  });
}

/** El recurs d'un camí: `/drills/123/voice` → `/drills`. Escriure a dins buida tot el recurs. */
export function resourceOf(path: string): string {
  const clean = path.split('?')[0];
  const first = clean.split('/').filter(Boolean)[0];
  return first ? `/${first}` : clean;
}

/** Treu el que és vell o sobrer. Es crida un cop quan arrenca l'app. */
export async function prune(): Promise<void> {
  const db = await open();
  if (!db) return;
  await new Promise<void>((resolve) => {
    try {
      const tx = db.transaction([STORE], 'readwrite');
      const store = tx.objectStore(STORE);
      const req = store.index('at').openCursor();
      const fresh: IDBValidKey[] = [];
      req.onsuccess = () => {
        const cur = req.result;
        if (!cur) {
          // el cursor va de l'antic al modern: el que sobra del final són els més vells
          const extra = fresh.length - MAX_ENTRIES;
          if (extra > 0) fresh.slice(0, extra).forEach((k) => store.delete(k));
          resolve();
          return;
        }
        const row = cur.value as CachedRead;
        if (row.fix) { /* el curs baixat a posta no caduca ni compta (#506, pas 4) */ }
        else if (Date.now() - row.at > MAX_AGE_MS) cur.delete();
        else fresh.push(cur.primaryKey);
        cur.continue();
      };
      req.onerror = () => resolve();
      tx.onabort = () => resolve();
    } catch {
      resolve();
    }
  });
}

/** Buida-ho tot. Per a qui vulgui començar de zero des dels ajustos. */
export async function clearAll(): Promise<void> {
  await run('readwrite', (s) => s.clear());
}
