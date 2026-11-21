import type { Drill } from '../types';
import { bibliotecaAlDia, drillsLocals } from './biblioteca';
import { filtra } from '../utils/casaFrase';

// Cercar una frase a la còpia del telèfon (#506).
//
// En Pablo, amb l'app al telèfon: «in this phone the offline is not working, I can not search
// phrase». I era cert: «Cerca una frase» només preguntava a `GET /corpus/search`, o sigui que
// sense xarxa no hi havia cerca —ni amb xarxa dolenta, perquè la petició es queda penjada i la
// pantalla amb ella. Mentrestant el telèfon ja tenia la biblioteca sencera a disc: 18 MB a
// IndexedDB i prop d'un giga de veus.
//
// Qui casa amb què és a `utils/casaFrase.ts`, que és pur i es pot provar sol. Aquí només hi ha
// d'on surten les frases.

export { filtra };

/**
 * La còpia del telèfon, sense esperar la xarxa.
 *
 * Si encara no hi ha res desat —app acabada d'instal·lar— sí que es prova de baixar-la: val més
 * esperar una vegada que dir que la biblioteca és buida.
 */
export async function copiaDelTelefon(): Promise<Drill[]> {
  const d = await drillsLocals().catch(() => [] as Drill[]);
  if (d.length) return d;
  return bibliotecaAlDia<Drill>().catch(() => [] as Drill[]);
}

/** Cerca a la còpia del telèfon. No toca la xarxa si ja hi ha còpia. */
export async function cercaLocal(consulta: string, limit = 40): Promise<Drill[]> {
  return filtra(await copiaDelTelefon(), consulta, limit);
}
