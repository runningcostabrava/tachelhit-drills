import { defineConfig } from 'vitest/config'

// Les proves del davant (#574).
//
// A part de `vite.config.ts` a posta: aquell porta el `define` de la versió i el connector de
// React, i executa `git rev-parse` cada vegada que es carrega. Les proves no en necessiten res, i
// la compilació que de debò es publica val més que no depengui d'un fitxer de proves.
//
// `environment: 'node'`: les primeres proves són de les REGLES, que són funcions pures. No hi ha
// `window` ni `document`, i això és una xarxa de seguretat i no un descuit: un mòdul que es toca
// el navegador en carregar-se petarà aquí, i és bo que peti — a l'APK es carrega igual de cec.
// El dia que es provi una pantalla caldrà jsdom, i serà una decisió escrita, no un accident.
export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
    // cada prova comença amb els dobles tal com els va deixar el fitxer, no com els va deixar
    // la prova anterior
    restoreMocks: true,
    clearMocks: true,
  },
})
