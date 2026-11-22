import { execSync } from 'node:child_process'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Quina versió és aquesta.
//
// L'1-11-2026 l'amo deia «still not done» d'una cosa que ja era feta, i la baixada del curs li
// parava a 189 pantalles quan n'havien de sortir 331. Totes dues coses tenien la mateixa causa:
// el telèfon portava una versió antiga, i no hi havia manera de saber-ho ni mirant la pantalla.
// 189 era, clavat, el compte que donava el codi d'abans d'aquell dia.
//
// Això hi posa el dia i el commit a dins, i «Al telèfon» ho ensenya. Amb un APK que es comparteix
// a mà i s'instal·la des del navegador, saber què tens instal·lat no és un luxe.
const ara = new Date().toISOString().slice(0, 16).replace('T', ' ')
let commit = 'sense git'
try {
  commit = execSync('git rev-parse --short HEAD', { encoding: 'utf8' }).trim()
} catch { /* fora d'un clon de git: el dia ja diu prou */ }

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    __VERSIO__: JSON.stringify(`${ara} · ${commit}`),
  },
})
