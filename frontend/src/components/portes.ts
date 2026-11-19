/**
 * Els dibuixos de les sis portes, dins de la compilació (#693).
 *
 * Fins al 19-11-2026 eren sis adreces de Cloudinary escrites a mà. Cloudinary esborra el compte
 * el 5 de desembre, i la resta dels mitjans van a R2. Aquestes NO: els fitxers de R2 es demanen
 * per `/mitjans/...`, que els serveix la mateixa API gratuïta que s'adorm, i tenir les portes
 * sabudes de memòria servia justament perquè la portada no hagués d'esperar-la. Posades a R2, el
 * remei hauria mort amb la malaltia.
 *
 * Importades i no escrites com a ruta: si un fitxer canvia de nom o desapareix, no es compila.
 * Val més que peti aquí que no pas una portada amb sis forats.
 *
 * Aquest mòdul no toca el navegador —ni `document` ni `window`— perquè es pugui carregar a les
 * proves, que corren amb `environment: 'node'`. Les adreces que en surten són relatives; qui les
 * faci servir les ha de resoldre, perquè `getMediaUrl` posa la base de l'API davant de qualsevol
 * ruta relativa i aquestes no són de l'API.
 */
import capture from '../assets/portes/porta-capture.webp';
import grammar from '../assets/portes/porta-grammar.webp';
import library from '../assets/portes/porta-library.webp';
import method from '../assets/portes/porta-method.webp';
import practice from '../assets/portes/porta-practice.webp';
import stories from '../assets/portes/porta-stories.webp';

export const PORTES: Record<string, string> = {
  method,
  grammar,
  practice,
  library,
  stories,
  capture,
};
