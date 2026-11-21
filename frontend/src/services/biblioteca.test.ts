/**
 * La còpia al dispositiu: que una baixada sencera no s'endugui el que encara no ha pujat (#568).
 *
 * Això va esborrar una gravació feta pel camp. Una baixada sencera buida la botiga, i una frase
 * feta al telèfon no té cap fila del servidor que la torni a posar: passa quan no hi ha marca de
 * sincronització —la primera obertura, o si la marca es perd—, que és just quan menys s'espera.
 *
 * Sense IndexedDB (aquí no n'hi ha: `environment: 'node'`), la biblioteca es queda a la memòria i
 * l'app ha de funcionar igual. Això és el camí que es prova, i és el mateix codi.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Drill } from '../types'

//: el mòdul de configuració es toca `window` en carregar-se; aquí només fa falta l'adreça
vi.mock('../config', () => ({ API_BASE: 'http://proves', isNativeApp: () => false }))
//: la còpia vella vivia a Preferences; aquí no n'hi ha cap per migrar
vi.mock('@capacitor/preferences', () => ({ Preferences: {
  get: vi.fn(async () => ({ value: null })),
  remove: vi.fn(async () => undefined),
} }))

const delServidor = vi.hoisted(() => vi.fn())
vi.mock('./fetchAllDrills', () => ({ fetchAllDrills: delServidor }))
vi.mock('axios', () => ({ default: { get: vi.fn(async () => ({ data: [] })) } }))

const fila = (id: number, text: string): Drill => ({
  id, text_tachelhit: text, text_catalan: text,
  updated_at: '2026-11-12T10:00:00',
} as Drill)

/** El número d'una frase feta al telèfon: surt del rellotge, no del servidor. */
const DEL_TELEFON = Date.now() * 1000

describe('la còpia al dispositiu', () => {
  beforeEach(() => {
    vi.resetModules()
    delServidor.mockReset()
  })

  it('un número de telèfon és provisional i un del servidor no', async () => {
    const { esProvisional } = await import('./biblioteca')
    expect(esProvisional(DEL_TELEFON)).toBe(true)
    expect(esProvisional(12_202)).toBe(false)
    expect(esProvisional(999_999)).toBe(false)
    expect(esProvisional(1_000_000)).toBe(true)
  })

  it('una baixada sencera NO s\'endú la frase feta al telèfon', async () => {
    const bib = await import('./biblioteca')
    //: una gravació feta pel camp, encara sense pujar
    await bib.desaDrills([fila(DEL_TELEFON, 'gravada pel camp')])
    delServidor.mockResolvedValue([fila(1, 'del servidor')])

    //: sense marca de sincronització: la primera obertura, i la que buida la botiga
    await bib.sincronitza()

    const queda = await bib.drillsLocals()
    expect(queda.map(d => d.id).sort()).toEqual([1, DEL_TELEFON].sort())
    expect(queda.find(d => d.id === DEL_TELEFON)?.text_tachelhit).toBe('gravada pel camp')
  })

  it('i si el servidor ja la té, no en queden dues', async () => {
    const bib = await import('./biblioteca')
    await bib.desaDrills([fila(DEL_TELEFON, 'gravada pel camp')])
    //: ha pujat i el servidor l'ha tornada amb el mateix número
    delServidor.mockResolvedValue([fila(DEL_TELEFON, 'gravada pel camp')])

    await bib.sincronitza()

    expect((await bib.drillsLocals()).filter(d => d.id === DEL_TELEFON)).toHaveLength(1)
  })

  it('una frase del servidor que ja no hi és, sí que se\'n va', async () => {
    const bib = await import('./biblioteca')
    await bib.desaDrills([fila(7, 'esborrada al servidor')])
    delServidor.mockResolvedValue([fila(1, 'del servidor')])

    await bib.sincronitza()

    expect((await bib.drillsLocals()).map(d => d.id)).toEqual([1])
  })

  it('si la xarxa falla, la còpia es queda com estava', async () => {
    const bib = await import('./biblioteca')
    await bib.desaDrills([fila(DEL_TELEFON, 'gravada pel camp'), fila(3, 'del servidor')])
    delServidor.mockRejectedValue(new Error('sense xarxa'))

    await expect(bib.sincronitza()).rejects.toThrow('sense xarxa')

    expect((await bib.drillsLocals()).map(d => d.id).sort()).toEqual([3, DEL_TELEFON].sort())
  })
})
