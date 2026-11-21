/**
 * On va una lectura de màquina (ADR 0003: el text del parlant és sagrat).
 *
 * La regla és d'una línia i és sempre la mateixa: **si hi ha text d'una persona, la lectura de la
 * màquina no el toca** — va a `text_tachelhit_suggested`, perquè algú hi digui la seva. Només
 * quan el camp és buit —la frase acaba de néixer d'una gravació i ningú no hi ha escrit res— la
 * lectura pot ocupar el camp bo.
 *
 * Viu aquí, i no repetida a cada pantalla, perquè això és exactament el que va fallar: la graella
 * ho feia bé i l'editor del mòbil escrivia damunt del text del parlant sense mirar-s'hi (#557).
 * Qui afegeixi una tercera pantalla que transcrigui, que cridi aquesta funció i no hi pensi més.
 */
export type OnVaLaLectura =
  | { text_tachelhit: string }
  | { text_tachelhit_suggested: string };

/** El camp on desar la lectura, segons si el parlant ja hi havia escrit. */
export function onVaLaLectura(textDelParlant: string | null | undefined, lectura: string): OnVaLaLectura {
  return (textDelParlant || '').trim()
    ? { text_tachelhit_suggested: lectura }
    : { text_tachelhit: lectura };
}

/** Si la lectura ha anat a suggeriment, què se n'ha de dir a qui l'ha demanada. */
export function queDirDeLaLectura(textDelParlant: string | null | undefined, lectura: string): string {
  const seu = (textDelParlant || '').trim();
  return seu
    ? `Desada com a suggeriment (es manté «${seu}»): ${lectura}`
    : `Transcripció desada: ${lectura}`;
}
