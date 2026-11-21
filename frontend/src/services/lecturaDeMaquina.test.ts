/**
 * La regla del #557: el text del parlant és sagrat (ADR 0003).
 *
 * Això és el que es va trencar de debò. La graella ho feia bé i l'editor del telèfon escrivia la
 * lectura de la màquina damunt del text d'una persona. L'issue demanava «una prova que ho
 * guardi», i no hi havia on posar-la (#574): aquesta és la primera.
 */
import { describe, expect, it } from 'vitest'
import { onVaLaLectura, queDirDeLaLectura } from './lecturaDeMaquina'

describe('on va una lectura de màquina', () => {
  it('amb text del parlant, va a suggeriment i no el toca', () => {
    expect(onVaLaLectura('tamazirt inu', 'tamazight nu')).toEqual({
      text_tachelhit_suggested: 'tamazight nu',
    })
  })

  it('amb el camp buit, la lectura pot ocupar el camp bo', () => {
    expect(onVaLaLectura('', 'tamazight nu')).toEqual({ text_tachelhit: 'tamazight nu' })
    expect(onVaLaLectura(null, 'x')).toEqual({ text_tachelhit: 'x' })
    expect(onVaLaLectura(undefined, 'x')).toEqual({ text_tachelhit: 'x' })
  })

  it('un camp amb només espais compta com a buit, i un amb un sol signe NO', () => {
    expect(onVaLaLectura('   \n\t ', 'x')).toEqual({ text_tachelhit: 'x' })
    //: algú ha escrit alguna cosa, per poca que sigui: no es trepitja
    expect(onVaLaLectura('?', 'x')).toEqual({ text_tachelhit_suggested: 'x' })
  })

  it('el tifinag del parlant tampoc no es trepitja', () => {
    //: el camp del parlant és en tifinag a 3.478 drills (#468); la lectura arriba en llatí
    expect(onVaLaLectura('ⵜⴰⵎⴰⵣⵉⵖⵜ', 'tamazight')).toEqual({
      text_tachelhit_suggested: 'tamazight',
    })
  })
})

describe('què se n\'ha de dir a qui l\'ha demanada', () => {
  it('quan hi havia text, es diu que es manté i quin és', () => {
    const diu = queDirDeLaLectura('tamazirt inu', 'tamazight nu')
    expect(diu).toContain('suggeriment')
    expect(diu).toContain('tamazirt inu')
  })

  it('quan no hi havia res, es diu desada i prou', () => {
    expect(queDirDeLaLectura('', 'tamazight nu')).toBe('Transcripció desada: tamazight nu')
  })
})
