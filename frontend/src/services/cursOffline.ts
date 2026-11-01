import { api, baixaPerOffline } from '../api';

/**
 * El curs sencer al telèfon (#506, ADR 0008, pas 4).
 *
 * Fins ara, sense connexió només s'obrien les pantalles que algú ja havia visitat: la resta eren
 * una pantalla d'error. En Pablo (31-10): «the gramatica, metode and histories should work», i
 * després «comprova que és capaç de descarregar tot, que tot és accessible» —d'aquí que hi entri
 * també la Pràctica, que s'havia quedat fora.
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
  /** Les parts que no s'han pogut ni llistar: aquelles no són a la baixada i cal dir-ho. */
  sense: string[];
}

let aturar = false;
let tanda: Promise<ProgresCurs> | null = null;

export function aturaCurs() { aturar = true; }
export function baixantCurs(): boolean { return !!tanda; }

/**
 * Les pantalles del curs, amb el nom que es veu mentre es baixen.
 *
 * `sense` recull les llistes que NO s'han pogut demanar. Abans això s'empassava en silenci: si
 * `/grammar` fallava —i el servidor es queixa més del que voldríem—, les 23 unitats no entraven a
 * la llista i la baixada deia «fet» sense elles. L'amo ho va veure l'1-11-2026: la seva baixada
 * tenia 189 pantalles de les 331 que havia de tenir, i res no ho deia.
 *
 * Ara es prova tres vegades, amb espera entremig, i el que segueixi sense venir es diu pel seu
 * nom. Val més una baixada incompleta i dita que una d'incompleta i callada.
 */
async function pantalles(sense: string[]): Promise<{ path: string; nom: string }[]> {
  const fora: { path: string; nom: string }[] = [
    { path: '/grammar', nom: 'Gramàtica' },
    { path: '/method/', nom: 'Mètode' },
    { path: '/stories', nom: 'Històries' },
    { path: '/alfabet', nom: 'Sons' },
    { path: '/alfabet/parelles?per_so=4', nom: 'Sons · parelles' },
  ];
  const espera = (ms: number) => new Promise((r) => setTimeout(r, ms));
  const mira = async <T>(nom: string, f: () => Promise<T>): Promise<T | null> => {
    for (let i = 0; i < 3; i++) {
      try { return await f(); } catch { if (i < 2) await espera(3000 * (i + 1)); }
    }
    sense.push(nom);
    return null;
  };

  const g = await mira('Gramàtica', () => api.grammarUnits());
  for (const u of g?.units || []) {
    fora.push({ path: `/grammar/${u.slug}?limit=60`, nom: `Gramàtica · ${u.title}` });
    fora.push({ path: `/grammar/${u.slug}/lesson`, nom: `Gramàtica · ${u.title} · la lliçó` });
    fora.push({ path: `/grammar/${u.slug}/deep?limit=60`, nom: `Gramàtica · ${u.title} · a fons` });
  }

  const m = await mira('Mètode', () => api.methodIndex());
  for (const c of m?.chapters || []) {
    fora.push({ path: `/method/${encodeURIComponent(c.slug)}`, nom: `Mètode · ${c.title}` });
  }

  const s = await mira('Històries', () => api.stories());
  for (const h of s?.stories || []) {
    fora.push({ path: `/stories/${encodeURIComponent(h.slug)}`, nom: `Històries · ${h.title}` });
  }

  const a = await mira('Sons', () => api.alfabet());
  // Exactament el camí que demana la pantalla, `limit` inclòs: el cau va per l'adreça sencera, i
  // un `limit` diferent seria una altra entrada i la pantalla no la trobaria.
  for (const l of a?.lletres || []) {
    fora.push({ path: `/alfabet/${encodeURIComponent(l.tif)}?limit=12`, nom: `Sons · ${l.tif} ${l.lat}` });
  }

  // La Pràctica, sencera.
  //
  // El primer intent només baixava la portada i els passos de cada llista, i l'amo ho va notar de
  // seguida: «per què no tots els continguts de pràctica es descarreguen?». Perquè la pantalla no
  // té una porta sinó quatre —per dia de gravació, per tema, per unitat i per llista—, i cada
  // una obre una SESSIÓ que es demana a `/practice/session` amb la seva consulta. Aquelles no hi
  // eren.
  //
  // Es poden baixar perquè el servidor les tria sempre igual: la mateixa consulta dona les
  // mateixes frases, en el mateix ordre (`practice_mod.session_rows`). Són 104 portes —19 dies,
  // 29 temes, 23 unitats, 33 llistes— de deu frases cadascuna: poca cosa.
  //
  // L'adreça s'ha de construir EXACTAMENT com la fa la pantalla, perquè el cau va per adreça
  // sencera: les claus en aquest ordre i `limit` al final (`PracticeSession.tsx`).
  const sessio = (parts: [string, string][], nom: string) => {
    const q = new URLSearchParams();
    for (const [k, v] of parts) q.set(k, v);
    q.set('limit', '10');
    fora.push({ path: `/practice/session?${q.toString()}`, nom });
  };

  fora.push({ path: '/practice/collections', nom: 'Pràctica' });
  fora.push({ path: '/tests/', nom: 'Pràctica · les llistes' });
  const pr = await mira('Pràctica', () => api.practiceCollections());
  for (const u of pr?.units || []) sessio([['unit', u.slug]], `Pràctica · ${u.title}`);
  for (const t of pr?.topics || []) sessio([['topic', t.slug]], `Pràctica · ${t.label}`);
  for (const d of pr?.days || []) sessio([['day', d.day], ['speaker', d.speaker]], `Pràctica · ${d.speaker}`);
  for (const l of pr?.lists || []) {
    fora.push({ path: `/tests/${l.id}/steps`, nom: `Pràctica · ${l.title}` });
    sessio([['test_id', String(l.id)]], `Pràctica · ${l.title}`);
    // La porta que ensenya la llista sencera. Només per a les llistes: un tema o una unitat en
    // pot tenir centenars de frases, i aquelles ja són a la còpia de la biblioteca.
    const g = new URLSearchParams();
    g.set('test_id', String(l.id));
    g.set('with_voice', 'false');
    g.set('limit', '400');
    fora.push({ path: `/practice/session?${g.toString()}`, nom: `Pràctica · ${l.title} (la llista)` });
  }
  // El que NO es pot baixar, i és per una raó i no per oblit: la pràctica del dia (`daily=1`) i
  // el repàs espaiat surten de `/reviews/due`, que el servidor calcula al moment segons què t'ha
  // tocat a tu i quan; demà no seria el mateix. Això vol la seva pròpia cua (#506, pas 6).
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
    const p: ProgresCurs = { total: 0, fetes: 0, fallades: 0, ara: 'Mirant què hi ha…', corrent: true, sense: [] };
    passa?.({ ...p });
    const llista = await pantalles(p.sense);
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
