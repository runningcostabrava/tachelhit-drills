/**
 * Recordar quin fitxer de vídeo correspon a cada episodi del visor privat (#695).
 *
 * Una pàgina web NO pot obrir un camí del disc (`E:\...`): el navegador no deixa llegir res sense
 * que algú hi posi el dit, i això no es pot envoltar. El que sí que es pot és recordar el fitxer
 * que ja s'ha triat un cop: el navegador en guarda una nansa («handle») que sobreviu a tancar la
 * pestanya, i en tornar només cal un clic per donar-li permís un altre cop.
 *
 * El fitxer no es copia enlloc ni puja enlloc: la nansa és un apuntador del navegador al disc de
 * qui mira. El vídeo de la SNRT no surt del seu ordinador, que és la condició del permís.
 *
 * Només hi és al Chrome i derivats (`showOpenFilePicker`). Al Firefox i al Safari no existeix i
 * el visor es queda amb el `<input type="file">` de sempre: `potRecordar()` ho diu.
 */

const BD = 'snrt-video';
const MAGATZEM = 'nanses';

interface NansaFitxer {
  name: string;
  getFile(): Promise<File>;
  queryPermission?(d: { mode: 'read' }): Promise<PermissionState>;
  requestPermission?(d: { mode: 'read' }): Promise<PermissionState>;
}

export function potRecordar(): boolean {
  return typeof window !== 'undefined' && 'showOpenFilePicker' in window && 'indexedDB' in window;
}

function obre(): Promise<IDBDatabase> {
  return new Promise((si, no) => {
    const p = indexedDB.open(BD, 1);
    p.onupgradeneeded = () => { p.result.createObjectStore(MAGATZEM); };
    p.onsuccess = () => si(p.result);
    p.onerror = () => no(p.error);
  });
}

async function amb<T>(mode: IDBTransactionMode, fes: (s: IDBObjectStore) => IDBRequest): Promise<T | null> {
  try {
    const db = await obre();
    return await new Promise<T | null>((si) => {
      const r = fes(db.transaction(MAGATZEM, mode).objectStore(MAGATZEM));
      r.onsuccess = () => si((r.result as T) ?? null);
      r.onerror = () => si(null);
    });
  } catch {
    // Finestra privada, emmagatzematge bloquejat, quota plena: es pot viure sense recordar-ho.
    return null;
  }
}

export const desaNansa = (slug: string, n: unknown) => amb<void>('readwrite', (s) => s.put(n, slug));
export const llegeixNansa = (slug: string) => amb<NansaFitxer>('readonly', (s) => s.get(slug));
export const oblidaNansa = (slug: string) => amb<void>('readwrite', (s) => s.delete(slug));

/**
 * El fitxer d'una nansa desada, si el navegador encara hi dona permís.
 *
 * `demana` ha de ser `true` NOMÉS dins d'un clic: `requestPermission()` sense un gest de qui mira
 * el rebutja el navegador. Sense clic només es mira si el permís ja hi és (`queryPermission`), i
 * si no hi és es torna `null` perquè el visor n'ofereixi el botó.
 */
export async function fitxerDeLaNansa(n: NansaFitxer, demana: boolean): Promise<File | null> {
  try {
    const estat = (await n.queryPermission?.({ mode: 'read' })) ?? 'granted';
    if (estat !== 'granted') {
      if (!demana) return null;
      if (((await n.requestPermission?.({ mode: 'read' })) ?? 'denied') !== 'granted') return null;
    }
    return await n.getFile();
  } catch {
    // La nansa pot haver quedat orfe: el fitxer s'ha mogut o s'ha esborrat.
    return null;
  }
}

/** Obre el triador del sistema i torna la nansa, per poder-la recordar. */
export async function triaFitxer(): Promise<NansaFitxer | null> {
  try {
    const w = window as unknown as {
      showOpenFilePicker(o: unknown): Promise<NansaFitxer[]>;
    };
    const [n] = await w.showOpenFilePicker({
      types: [{ description: 'Vídeo', accept: { 'video/*': ['.mp4', '.mkv', '.webm', '.mov', '.m4v'] } }],
      multiple: false,
    });
    return n ?? null;
  } catch {
    // Qui mira ha tancat el triador: no és cap error.
    return null;
  }
}
