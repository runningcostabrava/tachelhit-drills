# ADR 0008: L'app mòbil funciona sense connexió, tret de la IA

- **Estat:** proposta
- **Data:** 2026-10-30
- **Decideix:** Pablo (propietari)
- **Issue:** #506

## El problema

En Pablo vol que l'app del mòbil (Android i iOS, Capacitor) funcioni sencera sense connexió: la
biblioteca, el curs de gramàtica, el Mètode, les Històries, la pràctica, el repàs espaiat i
`/start`. Només la IA (ASR, traducció, revisió amb IA, xat, captura de vídeo) pot demanar xarxa,
i ho ha de dir. L'abast ja ho deia («Funcionar al web i al mòbil, i també sense connexió»), però
avui no és veritat.

### Què hi ha avui (mirat al codi de `main`, f49515c)

Hi ha **tres** magatzems locals que no es coneixen entre ells, i cap no fa el que demana l'issue:

| peça | on desa | què fa | per què no n'hi ha prou |
|---|---|---|---|
| `OfflineSyncManager` | `Preferences` (al web `localStorage`, a Android `SharedPreferences`, a iOS `UserDefaults`) | a cada obertura es baixa **tota** la biblioteca (`fetchAllDrills`, 17 pàgines de 500) i la desa com un sol JSON; després, al mòbil, baixa **tot** l'àudio i les imatges a `Filesystem` en segon pla | un JSON de ~9 MB dins de `SharedPreferences`/`UserDefaults`, reescrit sencer cada vegada; l'àudio es baixa sense preguntar ni mirar si és dades mòbils; i **gairebé cap pantalla no llegeix els fitxers baixats** (només `MobileDrillEditor` i `TestTaking` criden `getLocalMediaUrl`) |
| `utils/readCache.ts` | IndexedDB `tachelhit-read-cache` | desa l'última resposta de cada `GET` que passa per `api.ts` (màx. 300 entrades, 30 dies) i la serveix si la xarxa falla | només hi ha el que s'ha visitat; les escriptures (`POST`) fora de línia fallen i prou; no toca l'àudio; les crides que van per `axios` no hi passen |
| `cuaDeVeus.ts` | IndexedDB `veus-pendents` | les preses gravades esperen al dispositiu i pugen soles (#370) | funciona; és el model a seguir per a la resta d'escriptures |

A més: el JavaScript de l'app ja viu dins de l'APK/IPA (`webDir: 'dist'`, sense `server.url`), de
manera que obrir l'app sense xarxa ja carrega la closca; no hi ha cap service worker ni
`vite-plugin-pwa`. El servidor ja té el que cal per a una sincronització incremental i no
s'utilitza: `GET /drills/?since=` (canviats des d'una data, per `updated_at`, indexat),
`GET /drills/tombstones?since=` (esborrats) i `POST /reviews/grade-batch` (notes del repàs fetes
fora de línia, idempotent per `graded_at`). El frontend no en crida cap.

### Què es trenca avui, pantalla per pantalla (mode avió, després d'haver-la obert amb xarxa)

| pantalla | d'on treu les dades | sense connexió |
|---|---|---|
| Biblioteca `/drills` | `fetchAllDrills` per `axios`; si falla, la còpia de `Preferences` | la llista surt (de la còpia), però **cap àudio no sona**: es reprodueix l'URL de Cloudinary, no el fitxer baixat. Al web, la còpia sovint és la «lleugera» o no hi és (5 MB de `localStorage`) |
| Cerca `/cerca` | `api.corpusSearch` al servidor | només surten les cerques idèntiques a una d'abans; no cerca res en local |
| Gramàtica `/grammar/*` | `api.grammarUnits`, `grammarUnit`, `grammarLesson`, `grammarDeep` | les unitats visitades s'obren (cau de lectura); les no visitades, error; l'àudio no sona |
| Mètode `/metode/:slug` | `api.methodIndex`, `api.methodChapter` | igual: només capítols visitats, sense so. L'àudio del CD (`/method/cd/…`) **tampoc no sona amb xarxa a producció**: el servidor de Render no té el CD (7 línies indexades) |
| Històries `/stories/:slug` | `api.stories`, `api.story` | només les visitades; sense so |
| Pràctica `/tests`, `/tests/sessio` | `api.practiceCollections`, `practiceSession`, `practiceSteps`; `PublicTestView` per `axios` | la sessió la munta el servidor: sense xarxa, o la mateixa sessió d'abans o res; `PublicTestView` no té cap còpia |
| Repàs espaiat | `api.reviewsDue`, `api.reviewGrade` | la cua d'avui només si s'havia demanat igual; **les notes es perden** (`reviewGrade(...).catch(() => {})`) |
| `/start` | `api.drill(id)` per a cada paraula | les paraules visitades surten; sense so |
| Inici `/` | `api.home`, `reviewStats`, `reviewStreak` | la còpia d'abans, si n'hi ha |
| IA (copilot, ASR, traducció, revisió, captura) | servidor + Spaces | error genèric o pantalla que es queda esperant; cap missatge no diu «cal xarxa» |

### Les mides (mesurades el 30-10-2026 amb 6 peticions petites a producció)

- **Drills:** 8.389 (`X-Total-Count`), 7.170 amb àudio, 1.276 amb vídeo.
- **Text:** una pàgina de 500 fa 520 KB en JSON (1.039 B/drill) i **82 KB amb gzip** (el servidor
  ja comprimeix). Mostres d'altres trams: 741–1.296 B/drill. Tota la biblioteca: **~9 MB en
  JSON, ~1,4 MB per la xarxa**, en 17 peticions de 500 (#489: mai d'un cop).
- **Àudio:** 24 fitxers de Cloudinary mirats amb `HEAD`, de quatre trams de la biblioteca. Els
  mp3 recents (MTNRA, Common Voice, TutlAit) fan 10–110 KB, la majoria 15–35 KB; els `webm`
  antics (les primeres gravacions) fan 88–328 KB. Estimació per a 7.170 àudios: **entre 0,2 i
  0,45 GB, uns 0,3 GB**. El que pesa són els pocs centenars de `webm` antics.
- **Imatges:** 156 de 800 drills mostrejats en tenen; les il·lustracions de Cloudinary fan
  ~20–30 KB, però les fotos de Wikimedia fan 270–370 KB. No són al criteri de l'issue.
- **Formats:** n'hi ha en `mp3`, `webm` i `flac`. iOS no garanteix el `webm`: cal provar-ho al
  dispositiu abans de prometre que «tot sona».

## Les opcions

| opció | a favor | en contra |
|---|---|---|
| No fer res | cap cost | l'abast diu una cosa que no és veritat; i el que hi ha baixa ~0,3 GB d'àudio sense preguntar i no el fa servir |
| Només un service worker (Workbox / `vite-plugin-pwa`) que desi les respostes i l'àudio | una sola peça; serviria també al web | a iOS, el WKWebView de Capacitor serveix l'app per `capacitor://` i no hi corren service workers (només amb *App-Bound Domains*); la Cache API no té pressupost garantit; no resol ni la sincronització incremental ni la cua d'escriptures |
| **IndexedDB per a les dades + `Filesystem` de Capacitor per a l'àudio** | IndexedDB ja és el que fan servir `readCache` i `cuaDeVeus` (cap dependència nova si no es vol Dexie); funciona igual al web i al mòbil; l'àudio va a `Directory.Data`, que el sistema no esborra; `Filesystem.downloadFile` (o `@capacitor/file-transfer`, que el substitueix a les versions noves) baixa directament a disc, sense passar 300 MB per base64 com ara | a iOS, IndexedDB d'un WKWebView es pot esborrar si el disc s'omple: la còpia s'ha de poder refer amb una sincronització; cerca local feta a mà (8.400 files caben en memòria) |
| SQLite amb `@capacitor-community/sqlite` | una base de dades de debò, consultes i índexs; sòlid amb centenars de milers de files | plugin natiu nou per a Android i iOS (dues compilacions per provar), una altra API al web (wasm), migracions d'esquema pròpies; per a 8.400 files és massa eina |

## La decisió

**Proposta:** les dades a IndexedDB i l'àudio a `Filesystem`, amb una sincronització incremental
per `updated_at` i una sola cua d'escriptures, i el que hi ha ara a `Preferences` es retira.

Per què aquesta: és la que ja fa servir el codi que funciona (`readCache`, `cuaDeVeus`), és l'única
de les quatre que serveix igual a Android, a iOS i al web, i el servidor ja té `since`, les
tombstones i `grade-batch`. Un service worker no corre a iOS, i SQLite és una dependència nativa
per a un volum que IndexedDB porta de sobres.

## Què en ve al darrere

- **La baixada es demana, no s'imposa.** La pantalla «Sense connexió» diu quant ocupa el text
  (~1,4 MB per la xarxa, ~9 MB al telèfon) i quant l'àudio (~0,3 GB), separats, i deixa triar si
  es baixa l'àudio, i si només amb wifi. El que fa ara `syncAllMedia` —baixar-ho tot en segon pla
  a cada obertura— s'atura.
- **Mida real de l'àudio.** El servidor no sap quant pesa cada fitxer. O es desa
  (`audio_bytes`, columna *nullable*, omplerta un cop des de l'API de Cloudinary) o la pantalla
  ensenya una estimació i la xifra real a mesura que baixa. Proposo la columna: és barata i fa que
  el número sigui veritat.
- **Sincronització incremental.** La primera vegada, 17 pàgines de 500 com ara (#489). Després,
  `GET /drills/?since=<l'última>` i `GET /drills/tombstones?since=`. Les tombstones es tallen a
  2.000 files: si en falten (fa molt que no se sincronitza), es torna a baixar sencer. L'app deixa
  de baixar la biblioteca dues vegades a cada obertura.
- **Les pantalles del curs es baixen com a paquet.** Gramàtica (23 unitats, lliçó i «a fons»),
  Mètode (índex i capítols), Històries, l'alfabet i les paraules de `/start` es demanen totes un
  cop, després de la biblioteca, i queden al cau de lectura sense data de caducitat. El seu àudio
  surt de la biblioteca (són drills) i ja és a disc. La pràctica i el repàs es munten en local
  amb els drills baixats; quan hi ha xarxa, mana el servidor.
- **Una sola cua d'escriptures.** Les notes del repàs van a `POST /reviews/grade-batch` amb
  l'hora real; les preses continuen a `cuaDeVeus`; les altres accions de drills deixen
  `Preferences` i passen a IndexedDB. Res no es perd en silenci: el comptador de pendents de dalt
  compta totes les cues.
- **La IA, sense xarxa, diu que necessita xarxa.** Un missatge, el mateix a tot arreu, i el botó
  desactivat; mai una pantalla que es queda esperant.
- **El text del parlant no canvia.** Fora de línia es llegeix i s'escolta; cap edició feta sense
  xarxa no trepitja la del servidor sense que una persona ho vegi: si el drill ha canviat al
  servidor des de l'última còpia, la cua no l'envia i ho diu.
- **El que empitjora.** Un telèfon ple pot perdre la còpia d'IndexedDB a iOS i s'haurà de tornar a
  sincronitzar; ~0,3 GB és molt per a un mòbil petit; el `webm` antic potser no sona a iOS i caldrà
  convertir-lo a Cloudinary (una transformació `f_mp3` a l'URL); i hi ha una pantalla més que
  mantenir. El CD del Mètode no s'arregla aquí: no sona tampoc amb xarxa i és un altre issue.
- **El pla pas a pas** és a [`docs/offline-pla.md`](../offline-pla.md).
