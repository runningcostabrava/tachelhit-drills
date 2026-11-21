/**
 * Les portades de la portada no poden dependre de ningú de fora (#693).
 *
 * Les sis estaven escrites a mà apuntant a Cloudinary, que el 5 de desembre de 2026 esborra el
 * compte. Van quedar fora de la mudança a R2 del #577 perquè aquella movia el que la base de
 * dades esmentava a les frases, i aquestes viuen al codi.
 *
 * Que els fitxers hi siguin no cal provar-ho: són `import`, i un que falti no compila. El que
 * es prova aquí és el que una compilació verda no veuria —que l'adreça torni a ser de fora, o
 * que algú les passi per `/mitjans/`, que és l'API adormida i mataria el motiu de tenir-les.
 */
import { describe, expect, it } from 'vitest';
import { PORTES } from './portes';

describe('les portades de la portada', () => {
  it('són les sis', () => {
    expect(Object.keys(PORTES).sort()).toEqual(
      ['capture', 'grammar', 'library', 'method', 'practice', 'stories'],
    );
  });

  it('no surten de cap servei de fora', () => {
    for (const [nom, adreca] of Object.entries(PORTES)) {
      expect(adreca, nom).not.toMatch(/^https?:\/\//);
    }
  });

  it('no passen per l\'API', () => {
    for (const [nom, adreca] of Object.entries(PORTES)) {
      expect(adreca, nom).not.toMatch(/\/mitjans\//);
    }
  });
});
