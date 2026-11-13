import { describe, expect, it } from 'vitest';
import { AVANCADA, liniaAra } from './liniaAra';

/**
 * La regla de quina línia es veu, i per què s'encén abans de la marca.
 *
 * El 13-11-2026 en Pablo mirava l'episodi 2 i veia el subtítol a la pantalla i la banda buida a
 * sota. No era el desplaçament —es van comprovar vuit línies contra la imatge i les vuit casen—:
 * era que les nostres marques són les de la VEU i el subtítol surt abans.
 */

// L'episodi 2 de debò: la línia del 269 («Quina sort, Baba Ali!») i la d'abans.
const EPISODI_2 = [
  { t: 256, fi: 258.95 },
  { t: 259, fi: 265.0 },
  { t: 269, fi: 273.95 },
  { t: 274, fi: 279.95 },
];

describe('quina línia es veu', () => {
  it("s'encén abans de la marca, que és quan el subtítol surt a la pantalla", () => {
    // El cas d'en Pablo: al segon 267 la pantalla ja ensenya la línia del 269.
    expect(liniaAra(EPISODI_2, 267)).toBe(2);
    expect(liniaAra(EPISODI_2, 269)).toBe(2);
  });

  it("no s'encén tan aviat com per trepitjar la línia d'abans", () => {
    // Al 264 encara sona la del 259, i la del 269 és a cinc segons: no ha de guanyar.
    expect(liniaAra(EPISODI_2, 264)).toBe(1);
  });

  it('quan dues podrien ser, es queda la darrera', () => {
    // A 259 hi caben la del 256 (fins al 258,95 + marge) i la del 259. La pantalla ja ensenya
    // la nova.
    expect(liniaAra(EPISODI_2, 259)).toBe(1);
  });

  it("s'apaga quan la línia s'acaba, i no abans", () => {
    // Una línia que no en té cap altra a tocar: s'aguanta fins al final i llavors s'apaga.
    const sola = [{ t: 10, fi: 14 }];
    expect(liniaAra(sola, 13.9)).toBe(0);
    expect(liniaAra(sola, 14.3)).toBe(0);     // el marge del rellotge, que refresca cada 0,2 s
    expect(liniaAra(sola, 15)).toBe(-1);
  });

  it("al final d'una línia, si la següent ja és a la pantalla, guanya la següent", () => {
    // A 273,9 la del 269 encara no s'ha acabat (fi 273,95), però la del 274 fa tres segons que
    // és a la pantalla. Guanya la que es veu, no la que sona. Això és la regla, no un descuit.
    expect(liniaAra(EPISODI_2, 273.9)).toBe(3);
    expect(liniaAra(EPISODI_2, 279.95)).toBe(3);
  });

  it('entre una línia i la següent, quan hi ha un silenci llarg, no ensenya res', () => {
    const ambForat = [{ t: 10, fi: 14 }, { t: 100, fi: 104 }];
    expect(liniaAra(ambForat, 50)).toBe(-1);
    expect(liniaAra(ambForat, 20)).toBe(-1);
  });

  it('abans de la primera i després de la darrera, res', () => {
    expect(liniaAra(EPISODI_2, 0)).toBe(-1);
    expect(liniaAra(EPISODI_2, 300)).toBe(-1);
    expect(liniaAra(EPISODI_2, -5)).toBe(-1);
  });

  it('sense línies no peta', () => {
    expect(liniaAra([], 100)).toBe(-1);
  });

  it("l'avançada és de tres segons, i això és una decisió mesurada", () => {
    // Si algú la puja, trepitjarà la línia d'abans; si la baixa, tornarà el forat que es va
    // veure. El número ve de la distribució de l'episodi 2 (45 % de les línies tenen la
    // següent a menys de tres segons).
    expect(AVANCADA).toBe(3);
    expect(liniaAra([{ t: 100, fi: 104 }], 100 - AVANCADA)).toBe(0);
    expect(liniaAra([{ t: 100, fi: 104 }], 100 - AVANCADA - 0.5)).toBe(-1);
  });
});
