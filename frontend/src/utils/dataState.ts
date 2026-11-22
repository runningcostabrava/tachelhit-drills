/**
 * Què està passant amb les dades, perquè la pantalla ho pugui dir.
 *
 * Dues coses que fins ara no es veien i que han de veure's:
 *
 *  · el servidor triga a despertar-se (Render gratuït s'adorm als 15 minuts) i la pantalla es
 *    queda en blanc sense dir per què;
 *  · s'ensenya una còpia desada perquè la xarxa va lenta, i si després arriba una cosa diferent
 *    ningú no ho diu. Ensenyar una cosa vella sense avisar seria el mateix pecat que el botó
 *    que deia «escolta el capítol» i feia sonar una altra cosa.
 *
 * És un bus d'esdeveniments de `window` i prou: qui vulgui ensenyar-ho s'hi apunta, i si no
 * s'hi apunta ningú no passa res.
 */

/** Per què s'ensenya una còpia: el servidor va lent, o no s'hi ha pogut arribar. */
export type StaleWhy = 'slow' | 'offline';

export type DataEvent =
  /** No hi ha res per ensenyar i el servidor no contesta encara. */
  | { kind: 'waking'; on: boolean }
  /** S'està ensenyant una còpia desada d'aquest camí, i per què. */
  | { kind: 'stale'; path: string; at: number; why: StaleWhy }
  /** La xarxa ha portat dades diferents de les que s'ensenyen. */
  | { kind: 'fresh'; path: string };

const NAME = 'td:data';

function emit(detail: DataEvent) {
  try {
    window.dispatchEvent(new CustomEvent<DataEvent>(NAME, { detail }));
  } catch { /* fora del navegador: no passa res */ }
}

// Quantes peticions esperen alhora sense res per ensenyar. Es compten perquè una pantalla en
// demana tres o quatre a la vegada: si la primera que acaba apagués l'avís, l'avís parpellejaria
// mentre les altres encara esperen.
let waiting = 0;

export function markWaking(on: boolean) {
  const before = waiting;
  waiting = Math.max(0, waiting + (on ? 1 : -1));
  if (before === 0 && waiting > 0) emit({ kind: 'waking', on: true });
  if (before > 0 && waiting === 0) emit({ kind: 'waking', on: false });
}
export function markStale(path: string, at: number, why: StaleWhy) { emit({ kind: 'stale', path, at, why }); }
export function markFresh(path: string) { emit({ kind: 'fresh', path }); }

export function onData(cb: (e: DataEvent) => void): () => void {
  const h = (e: Event) => cb((e as CustomEvent<DataEvent>).detail);
  window.addEventListener(NAME, h);
  return () => window.removeEventListener(NAME, h);
}

/** «fa 3 minuts», per dir de quan és el que s'ensenya. */
export function howLongAgo(at: number): string {
  const s = Math.max(0, Math.round((Date.now() - at) / 1000));
  if (s < 90) return 'fa un moment';
  const m = Math.round(s / 60);
  if (m < 60) return `fa ${m} minuts`;
  const h = Math.round(m / 60);
  if (h < 24) return h === 1 ? 'fa una hora' : `fa ${h} hores`;
  const d = Math.round(h / 24);
  return d === 1 ? 'd’ahir' : `fa ${d} dies`;
}
