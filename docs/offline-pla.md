# Pla: l'app sense connexió (#506)

Com es posa en pràctica l'[ADR 0008](adr/0008-l-app-funciona-sense-connexio.md) **si s'accepta**.
Cada pas és un PR petit, que es pot fusionar sol i deixa l'app millor que abans. Cap pas no
comença abans que l'ADR estigui acceptada.

**Com es prova cada criteri.** A Android i a iOS (dispositiu o simulador): obrir l'app amb xarxa,
deixar acabar la sincronització, posar el **mode avió**, tancar l'app del tot (treure-la de les
recents) i tornar-la a obrir. Cap criteri no val si només s'ha provat amb l'app oberta.

## Pas 0 — Mesurar el que falta

- Contar, sense baixar res en bloc, quants àudios són `webm` i `flac` i quant pesen de veritat:
  una consulta a la base de dades local o a la de producció (només lectura) i, per a la mida,
  l'API d'administració de Cloudinary (`resources` per prefix, 500 per crida).
- Provar a iOS si un `webm` i un `flac` sonen des de `Filesystem` amb `convertFileSrc`.
- Mesurar el JSON de les pantalles del curs (`/grammar`, 23 unitats, `/method/`, capítols,
  `/stories`, `/alfabet`).

**Criteri:** un comentari a #506 amb les xifres i la llista de formats que no sonen a iOS. Sense
codi.

## Pas 1 — La biblioteca a IndexedDB, incremental

- Un mòdul `services/biblioteca.ts`: un magatzem IndexedDB `drills` (clau `id`, índex
  `updated_at`) i un registre `sync` amb la data de l'última sincronització.
- Primera vegada: `fetchAllDrills` (pàgines de 500, #489). Després:
  `GET /drills/?since=<última>&limit=500&offset=…` i `GET /drills/tombstones?since=<última>`.
  Si les tombstones arriben al sostre (2.000), baixada sencera.
- `App.tsx` i `DrillsResponsive` llegeixen d'aquí; la biblioteca deixa de baixar-se dues vegades.
- `cached_drills` de `Preferences` es buida un cop migrat (una sola vegada).

**Criteris:**
- En mode avió, `/drills` mostra els 8.389 drills (o els que hi hagi), i el filtre i l'ordre
  funcionen.
- Una segona obertura amb xarxa fa **una** petició `since` (més les tombstones), no 17: es veu
  al registre de xarxa.
- Esborrar un drill al servidor i sincronitzar: desapareix del telèfon.
- `Preferences` ja no té `cached_drills` (s'inspecciona amb les eines de Chrome / Safari).

## Pas 2 — L'àudio a disc, quan es demana

- La baixada passa a `Filesystem.downloadFile` (o `@capacitor/file-transfer`): directament a
  `Directory.Data/media/<id>.<ext>`, pel nom del drill i no per l'últim tros de l'URL (les URL de
  Wikimedia porten `?utm_…` al nom).
- Un sol `useAudioSrc(drill)` que torna el fitxer local si hi és i l'URL si no; totes les
  pantalles que fan `new Audio(getMediaUrl(...))` el fan servir.
- `syncAllMedia` deixa de córrer sol a cada obertura.
- Si el pas 0 diu que el `webm` no sona a iOS: es baixa la versió `f_mp3` de Cloudinary.

**Criteris:**
- En mode avió, qualsevol drill baixat sona a `/drills`, a la gramàtica, al Mètode, a les
  Històries, a la pràctica i a `/start`.
- Un drill que no s'ha baixat no fa cap error: el botó surt apagat i diu «sense baixar».
- Amb xarxa, obrir l'app no baixa cap àudio que no s'hagi demanat.

## Pas 3 — La pantalla «Sense connexió»

- A Perfil: quant ocupa el text i quant l'àudio, **per separat** (de `audio_bytes` si el pas 0
  l'ha afegit; si no, una estimació que ho diu), quant n'hi ha baixat, un interruptor «baixa
  l'àudio» i un altre «només amb wifi» (`Network.getStatus().connectionType`).
- Un botó per alliberar l'espai de l'àudio.
- Si el servidor ha de dir la mida: columna `audio_bytes` *nullable* (la sincronització de
  columnes l'afegeix sola) i un script d'una vegada que l'omple des de Cloudinary, en tandes.

**Criteris:**
- La pantalla mostra dues xifres, text i àudio, i la d'àudio coincideix (±10 %) amb el que ocupa
  la carpeta `media/` en acabar.
- Amb «només amb wifi» i dades mòbils, no es baixa cap àudio.
- «Allibera» deixa `media/` buida i els botons d'escoltar tornen a «sense baixar».

## Pas 4 — El curs com a paquet

- Després de la biblioteca, es demanen un cop totes les pantalles del curs: `/grammar`, cada
  unitat (lliçó i «a fons»), `/method/` i cada capítol, `/stories` i cada història, `/alfabet`
  i les seves lletres, i els drills de `/start`. Van al cau de lectura (`readCache`) marcades
  com a fixes: no caduquen ni compten per al sostre de 300.
- Es tornen a demanar només si el servidor diu que han canviat (empremta o `updated_at`).

**Criteris:**
- En mode avió, s'obren **totes** les unitats de gramàtica, tots els capítols del Mètode, totes
  les Històries i `/start`, incloses les que no s'havien visitat mai.
- Els exemples de cada pantalla sonen (pas 2).

## Pas 5 — Pràctica i repàs sense xarxa

- La sessió de pràctica es munta en local amb els drills de la biblioteca quan no hi ha xarxa
  (amb xarxa, mana el servidor).
- Repàs: es baixa la cua dels pròxims dies (`/reviews/due` amb un `limit` més gran) i les notes
  van a una cua IndexedDB que s'envia a `POST /reviews/grade-batch` amb `graded_at`.
- `PublicTestView` passa d'`axios` a `api.ts`, perquè també quedi al cau.

**Criteris:**
- En mode avió es pot fer una sessió de pràctica sencera i un repàs de 10 targetes.
- En tornar la xarxa, les notes arriben al servidor amb l'hora en què es van posar (es mira
  `review_logs`), i tornar a enviar la cua no les duplica.
- El comptador de pendents de dalt compta les notes que esperen.

## Pas 6 — Una sola cua d'escriptures

- Les accions de drills (`CREATE`, `UPDATE`, `UPLOAD_MEDIA`, `DELETE`) deixen `Preferences` i
  van a IndexedDB, al costat de les preses (`cuaDeVeus`) i les notes.
- Un `UPDATE` fet sense xarxa sobre un drill que ha canviat al servidor des de la còpia
  (`updated_at` diferent) no s'envia: queda a la llista de «no enviats» i ho diu. El text d'un
  parlant no es trepitja mai sense que una persona ho vegi.

**Criteris:**
- En mode avió, crear un drill amb veu i editar-ne un altre; en tornar la xarxa, tots dos són al
  servidor.
- Un conflicte provocat a propòsit (editar el mateix drill al web mentrestant) no s'envia i es veu
  a la llista.
- `Preferences` ja no té `sync_queue`.

## Pas 7 — La IA diu que necessita xarxa

- Un `useEnLinia()` i un component `CalXarxa` amb un sol missatge («Això necessita connexió»).
- Copilot, ASR i comprovació de pronúncia, traducció, revisió amb IA, captura de vídeo,
  `/afegeix` amb traducció i la cerca al servidor: botó desactivat i el missatge, sense fer cap
  petició.

**Criteris:**
- En mode avió, cada una d'aquestes funcions mostra el missatge i cap no es queda «carregant».
- Cap error vermell a la consola en obrir-les sense xarxa.

## Pas 8 — Prova sencera i tancament

- La passada de mode avió dels passos 1–7, seguida, a Android i a iOS, amb captures.
- L'abast (`docs/SCOPE.md`) diu exactament què funciona sense connexió.
- Es retiren `OfflineSyncManager` (el que en quedi), `utils/offlineCache.ts` i les crides a
  `syncAllMedia`.

**Criteri:** els criteris d'acceptació de #506, tots, marcats al mateix issue amb la captura que
ho prova; `Closes #506`.
