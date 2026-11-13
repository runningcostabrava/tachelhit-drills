/**
 * Quina línia del subtítol s'ha de veure en aquest segon.
 *
 * Viu aquí i no dins del visor perquè és una REGLA, i les regles es proven. La va canviar la
 * mesura del 13-11-2026 i no un criteri: val més que la pròxima vegada caigui una prova que no
 * pas que algú se'n torni a adonar mirant la pantalla.
 *
 * ## Les marques són les de la VEU, no les del subtítol
 *
 * El segon de cada línia és el que va escriure qui va fer els talls de so: el moment en què
 * comença a parlar. El subtítol de la pantalla no surt en aquell segon, surt **abans** — el
 * subtítol espera l'actor, no al revés.
 *
 * Comprovat a l'episodi 2 contra la imatge del vídeo: al segon 1610 la pantalla ja diu
 * «يا لحظك يا بابا علي», que és la nostra línia del 269 (vídeo 1609,9), i qui mirava veia el
 * text a dalt i la banda buida a sota. Per això s'encén {@link AVANCADA} segons abans.
 *
 * Tres segons surten de les dades: a l'episodi 2, el 45 % de les línies en tenen una altra a
 * menys de tres segons, de manera que això gairebé no encavalca res; i quan dues són
 * candidates es queda **la darrera**, que és la que la pantalla ja ensenya.
 *
 * El final no cal tocar-lo: el servidor ja allarga cada línia fins que comença la següent
 * (`MAX_DURADA`, 6 s a `backend/baba_ali.py`).
 *
 * ## I el desplaçament NO està malament
 *
 * Abans de canviar això es va comprovar: vuit línies de l'episodi 2, escampades, i a totes
 * vuit la pantalla diu al segon que el visor prediu exactament el que tenim desat. El
 * desplaçament és bo; el que fallava era l'encesa.
 */
export const AVANCADA = 3;

/** El mínim que ha de tenir una línia per poder-hi buscar. */
export interface LiniaAmbTemps {
  t: number;
  fi: number;
}

/**
 * L'índex de la línia que s'ha de veure, o -1 si no n'hi ha cap.
 *
 * `linies` ha d'anar ordenada per `t`, que és com la serveix l'API. Es busca per bisecció: amb
 * 335 línies i cinc comptes per segon, recórrer-les totes cada vegada es nota al mòbil.
 */
export function liniaAra(linies: readonly LiniaAmbTemps[], quan: number): number {
  if (!linies.length || quan < 0) return -1;
  let a = 0;
  let b = linies.length - 1;
  let trobada = -1;
  while (a <= b) {
    const m = (a + b) >> 1;
    if (linies[m].t - AVANCADA <= quan) { trobada = m; a = m + 1; } else { b = m - 1; }
  }
  if (trobada < 0) return -1;
  // El 0,4 és el que es triga a refrescar el rellotge: sense ell, la línia parpelleja al final.
  return quan <= linies[trobada].fi + 0.4 ? trobada : -1;
}
