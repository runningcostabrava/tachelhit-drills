// Quan l'app s'actualitza i tu tens la pestanya oberta.
//
// El web es serveix en trossos amb el seu resum al nom (`web-hZDKL4pJ.js`), i es demanen quan
// fan falta: una ruta que s'obre, un connector de Capacitor que es desperta el primer cop que
// prems el micròfon. Si entremig s'ha desplegat una versió nova, aquells noms ja no existeixen i
// la petició mor amb un «Failed to fetch dynamically imported module».
//
// Això no és un error de l'usuari ni del seu micròfon, i dir-li el missatge del navegador tal
// qual —que és el que passava— no l'ajuda gens. El que li passa és que té una app vella a la mà,
// i l'única sortida és recarregar.
//
// NO es recarrega sol. Qui està escrivint un drill té text a la pantalla que encara no s'ha
// desat, i una recàrrega automàtica se l'enduria. S'ofereix, i decideix la persona.

const SIGNS = [
  'failed to fetch dynamically imported module',
  'error loading dynamically imported module',
  'importing a module script failed',
  'unable to preload css',
  'chunkloaderror',
];

/** Això és una app vella demanant un tros que el servidor ja no té? */
export function isStaleBuildError(e: unknown): boolean {
  const text = [
    (e as { message?: string })?.message,
    typeof e === 'string' ? e : '',
    (e as { toString?: () => string })?.toString?.(),
  ].filter(Boolean).join(' ').toLowerCase();
  return SIGNS.some((s) => text.includes(s));
}

let stale = false;
const listeners = new Set<(v: boolean) => void>();

/** Diu-ho una vegada: a partir d'aquí la pantalla ensenya la barra fins que es recarregui. */
export function noteStaleBuild(): void {
  if (stale) return;
  stale = true;
  listeners.forEach((l) => l(true));
}

export function subscribeStaleBuild(l: (v: boolean) => void): () => void {
  listeners.add(l);
  l(stale);
  return () => { listeners.delete(l); };
}

/** Enganxa'l un cop a l'arrencada. Vite avisa pel seu compte; la resta cau als errors globals. */
export function watchForStaleBuild(): void {
  // el senyal propi de Vite quan un tros no es pot precarregar
  window.addEventListener('vite:preloadError', () => noteStaleBuild());
  window.addEventListener('unhandledrejection', (ev) => {
    if (isStaleBuildError((ev as PromiseRejectionEvent).reason)) noteStaleBuild();
  });
  window.addEventListener('error', (ev) => {
    if (isStaleBuildError((ev as ErrorEvent).error || (ev as ErrorEvent).message)) noteStaleBuild();
  });
}
