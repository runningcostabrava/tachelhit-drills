// Un sol reproductor per a tota l'app, perquè el sistema el pugui seguir (#342).
//
// Abans cada pantalla feia `new Audio(url)` per a cada tall: un element que no és al document i
// que no declara res. Per a Android i iOS això no és *una reproducció de mèdia*, és *una pàgina
// que fa soroll* — i la callen quan la pàgina deixa de ser visible. Per això, en apagar-se la
// pantalla del telèfon, la història emmudia.
//
// Tres coses canvien aquí, i les tres calen:
//
//   1. **Un sol element**, dins el document, al qual se li canvia el `src`. És el que el sistema
//      sap seguir d'una pista a la següent.
//   2. **`MediaSession`**: dir què sona i qui ho diu, perquè surti a la pantalla de bloqueig i
//      els botons de l'auricular facin el que han de fer.
//   3. **Cap `setTimeout` a la cadena**: la línia següent s'engega des de l'`ended`. Un WebView
//      de segon pla estrangola els temporitzadors —un silenci de 350 ms es pot convertir en un
//      minut— de manera que una fila que espera un rellotge de JS no arriba mai a la segona
//      línia, encara que la primera hagi sonat sencera.
//
// El que això NO arregla: l'app encara no té permís de sonar amb l'aplicació al fons de debò
// (`UIBackgroundModes` a iOS, servei en primer pla a Android). Això canvia el que l'app demana en
// instal·lar-se i espera una decisió del propietari. El que sí que queda arreglat és el cas
// habitual: la pantalla que s'apaga sola mentre escoltes.

let el: HTMLAudioElement | null = null;

/** L'element, creat una sola vegada i deixat al document. */
function element(): HTMLAudioElement {
  if (el) return el;
  const a = document.createElement('audio');
  a.preload = 'auto';
  a.setAttribute('playsinline', '');      // iOS: sonar sense obrir el reproductor a pantalla completa
  a.style.display = 'none';
  document.body.appendChild(a);
  el = a;
  return a;
}

/**
 * Sona una adreça i espera que s'acabi.
 *
 * Resol tant si acaba com si falla com si algú l'atura: una fila que espera una reproducció
 * aturada es penjaria per sempre, i aturar ha de voler dir seguir endavant, no quedar-se clavat.
 */
export function say(url: string): Promise<void> {
  const net = (url || '').trim();
  if (!net) return Promise.resolve();
  const a = element();
  a.pause();
  return new Promise<void>((resolve) => {
    let fet = false;
    const prou = () => {
      if (fet) return;
      fet = true;
      a.removeEventListener('ended', prou);
      a.removeEventListener('error', prou);
      a.removeEventListener('pause', prou);
      resolve();
    };
    a.addEventListener('ended', prou);
    a.addEventListener('error', prou);
    a.addEventListener('pause', prou);
    a.src = net;
    a.currentTime = 0;
    a.play().catch(prou);
  });
}

/** Atura el que soni. La promesa de `say()` es resol tota sola. */
export function stop() {
  if (el) el.pause();
}

/**
 * El silenci entre dues línies.
 *
 * Amb la pantalla encesa és una pausa per respirar. Amb la pantalla apagada, un temporitzador no
 * és de fiar, de manera que **no se n'espera cap**: val més encadenar de seguida que arriscar-se
 * que la història no continuï.
 */
export function gap(ms: number): Promise<void> {
  if (typeof document !== 'undefined' && document.hidden) return Promise.resolve();
  return new Promise((r) => setTimeout(r, ms));
}

export interface Ara {
  title: string;
  artist?: string;
  album?: string;
  onPlay?: () => void;
  onPause?: () => void;
  onNext?: () => void;
  onPrev?: () => void;
}

/** Què sona, per a la pantalla de bloqueig i els botons de l'auricular. */
export function nowPlaying(ara: Ara | null) {
  if (typeof navigator === 'undefined' || !('mediaSession' in navigator)) return;
  const ms = navigator.mediaSession;
  try {
    if (!ara) {
      ms.playbackState = 'none';
      ms.metadata = null;
      return;
    }
    ms.metadata = new MediaMetadata({
      title: ara.title,
      artist: ara.artist || '',
      album: ara.album || '',
    });
    ms.playbackState = 'playing';
    ms.setActionHandler('play', ara.onPlay ? () => ara.onPlay?.() : null);
    ms.setActionHandler('pause', ara.onPause ? () => ara.onPause?.() : null);
    ms.setActionHandler('nexttrack', ara.onNext ? () => ara.onNext?.() : null);
    ms.setActionHandler('previoustrack', ara.onPrev ? () => ara.onPrev?.() : null);
  } catch { /* el navegador no en sap */ }
}

type Lock = { release: () => Promise<void> };
let lock: Lock | null = null;

/**
 * Demanar que la pantalla no s'apagui mentre es llegeix.
 *
 * No sempre es concedeix, i el sistema la pot retirar sol quan la pestanya deixa de veure's; per
 * això la reproducció no en depèn. És una ajuda, no la solució: la solució és que la veu aguanti
 * encara que la pantalla marxi.
 */
export function keepAwake(on: boolean) {
  const nav = navigator as Navigator & {
    wakeLock?: { request: (t: 'screen') => Promise<Lock> };
  };
  if (on && nav.wakeLock && !lock) {
    nav.wakeLock.request('screen').then((l) => { lock = l; }).catch(() => {});
  }
  if (!on && lock) {
    lock.release().catch(() => {});
    lock = null;
  }
}
