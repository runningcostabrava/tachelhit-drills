import { api, baixaPerOffline } from '../api';

/**
 * El curs sencer al telèfon (#506, ADR 0008, pas 4).
 *
 * Fins ara, sense connexió només s'obrien les pantalles que algú ja havia visitat: la resta eren
 * una pantalla d'error. En Pablo (31-10): «the gramatica, metode and histories should work».
 *
 * Aquí es demanen totes, un cop, i es desen al cau de lectura marcades com a fixes (`fix`): no
 * caduquen als 30 dies ni compten per al sostre de 300 còpies. El que pesa —les veus— no és
 * aquí: són drills i van per `audioLocal`.
 *
 * D'una en una i no totes alhora: el servidor és un Render de 512 MB i una ventada de dues-centes
 * peticions l'ha tombat més d'un cop (ADR 0008, #539). Es pot aturar i reprendre; el que ja és
 * baixat no es torna a demanar perquè tornar-ho a demanar és barat i sempre el deixa més fresc.
 */

export interface ProgresCurs {
  total: number;
  fetes: number;
  fallades: number;
  /** Què s'està baixant ara, per ensenyar-ho: «Gramàtica · el perfectiu». */
  ara: string;
  corrent: boolean;
}

let aturar = false;
let tanda: Promise<ProgresCurs> | null = null;

export function aturaCurs() { aturar = true; }
export function baixantCurs(): boolean { return !!tanda; }

/** Les pantalles del curs, amb el nom que es veu mentre es baixen. */
async function pantalles(): Promise<{ path: string; nom: string }[]> {
  const fora: { path: string; nom: string }[] = [
    { path: '/grammar', nom: 'Gramàtica' },
    { path: '/method/', nom: 'Mètode' },
    { path: '/stories', nom: 'Històries' },
    { path: '/alfabet', nom: 'Sons' },
    { path: '/alfabet/parelles?per_so=4', nom: 'Sons · parelles' },
  ];
  const mira = async <T>(f: () => Promise<T>): Promise<T | null> => f().catch(() => null);

  const g = await mira(() => api.grammarUnits());
  for (const u of g?.units || []) {
    fora.push({ path: `/grammar/${u.slug}?limit=60`, nom: `Gramàtica · ${u.title}` });
    fora.push({ path: `/grammar/${u.slug}/lesson`, nom: `Gramàtica · ${u.title} · la lliçó` });
    fora.push({ path: `/grammar/${u.slug}/deep?limit=60`, nom: `Gramàtica · ${u.title} · a fons` });
  }

  const m = await mira(() => api.methodIndex());
  for (const c of m?.chapters || []) {
    fora.push({ path: `/method/${encodeURIComponent(c.slug)}`, nom: `Mètode · ${c.title}` });
  }

  const s = await mira(() => api.stories());
  for (const h of s?.stories || []) {
    fora.push({ path: `/stories/${encodeURIComponent(h.slug)}`, nom: `Històries · ${h.title}` });
  }

  const a = await mira(() => api.alfabet());
  // Exactament el camí que demana la pantalla, `limit` inclòs: el cau va per l'adreça sencera, i
  // un `limit` diferent seria una altra entrada i la pantalla no la trobaria.
  for (const l of a?.lletres || []) {
    fora.push({ path: `/alfabet/${encodeURIComponent(l.tif)}?limit=12`, nom: `Sons · ${l.tif} ${l.lat}` });
  }
  return fora;
}

/**
 * Baixa el curs sencer. `passa` es crida a cada pantalla perquè es vegi per on va.
 * Si ja n'hi ha una de corrent, s'hi enganxa.
 */
export async function baixaElCurs(passa?: (p: ProgresCurs) => void): Promise<ProgresCurs> {
  if (tanda) return tanda;
  aturar = false;
  tanda = (async () => {
    const p: ProgresCurs = { total: 0, fetes: 0, fallades: 0, ara: 'Mirant què hi ha…', corrent: true };
    passa?.({ ...p });
    const llista = await pantalles();
    p.total = llista.length;
    passa?.({ ...p });
    for (const { path, nom } of llista) {
      if (aturar) break;
      p.ara = nom;
      passa?.({ ...p });
      if (await baixaPerOffline(path)) p.fetes++;
      else p.fallades++;
      passa?.({ ...p });
    }
    return { ...p, ara: '', corrent: false };
  })().finally(() => { tanda = null; aturar = false; });
  return tanda;
}
