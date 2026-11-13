/**
 * El veredicte d'una lectura de màquina (`draft_check.py`) i a qui es pot ensenyar.
 *
 * El que importa aquí: un veredicte val només per a la lectura sobre la qual s'ha calculat. Si la
 * lectura ha canviat, el veredicte ja no és seu i la frase torna a ser «sense comprovar» — si
 * no, un «sí» vell beneiria una lectura nova que ningú no ha mirat.
 */
import { describe, expect, it } from 'vitest'
import { draftUsable, draftVerdict } from './drafts'

const amb = (text_tachelhit_suggested: string, check?: object | string) => ({
  text_tachelhit_suggested,
  draft_check: typeof check === 'string' || check === undefined ? check : JSON.stringify(check),
})

describe('draftVerdict', () => {
  it('sense lectura o sense comprovació, no hi ha veredicte', () => {
    expect(draftVerdict(null)).toBe('unchecked')
    expect(draftVerdict(undefined)).toBe('unchecked')
    expect(draftVerdict(amb('', { draft: '', verdict: 'yes' }))).toBe('unchecked')
    expect(draftVerdict(amb('tamazight'))).toBe('unchecked')
    //: el servidor envia null, que el tipus de Drill no diu; es comporta igual
    expect(draftVerdict({ text_tachelhit_suggested: 'tamazight',
                          draft_check: null as unknown as undefined })).toBe('unchecked')
  })

  it('el veredicte de la MATEIXA lectura val', () => {
    for (const v of ['yes', 'roughly', 'no'] as const) {
      expect(draftVerdict(amb('tamazight nu', { draft: 'tamazight nu', verdict: v }))).toBe(v)
    }
  })

  it('si la lectura ha canviat, el veredicte vell no val', () => {
    expect(draftVerdict(amb('una altra cosa', { draft: 'tamazight nu', verdict: 'yes' })))
      .toBe('unchecked')
  })

  it('les marques de dubte de la lectura no compten per casar-la', () => {
    //: la lectura es desa amb claudàtors i variants; la comprovació es va fer sobre el text net
    expect(draftVerdict(amb('[?tamazight nu]', { draft: 'tamazight nu', verdict: 'yes' })))
      .toBe('yes')
    expect(draftVerdict(amb('tamazight nu|tamazirt inu', { draft: 'tamazight nu', verdict: 'no' })))
      .toBe('no')
    expect(draftVerdict(amb('tamazight nu · tamazirt', { draft: 'tamazight nu', verdict: 'yes' })))
      .toBe('yes')
  })

  it('un veredicte que no reconeixem, o un JSON trencat, no es creu', () => {
    expect(draftVerdict(amb('x', { draft: 'x', verdict: 'potser' }))).toBe('unchecked')
    expect(draftVerdict(amb('x', 'no sóc json'))).toBe('unchecked')
  })
})

describe('draftUsable', () => {
  it('només s\'amaga el que la comprovació ha dit que NO', () => {
    expect(draftUsable(amb('x', { draft: 'x', verdict: 'no' }))).toBe(false)
    expect(draftUsable(amb('x', { draft: 'x', verdict: 'yes' }))).toBe(true)
    expect(draftUsable(amb('x', { draft: 'x', verdict: 'roughly' }))).toBe(true)
    //: sense comprovar NO és amagar: la majoria de la biblioteca és així
    expect(draftUsable(amb('x'))).toBe(true)
  })

  it('un «no» vell deixa de manar quan la lectura canvia', () => {
    expect(draftUsable(amb('lectura nova', { draft: 'lectura vella', verdict: 'no' }))).toBe(true)
  })
})
