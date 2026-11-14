# Entendre la veu de Tamazight For All — registre de recerca

Issue de referència: #601. Aquest fitxer és el quadern: cada hipòtesi amb la seva predicció,
la mesura que la va confirmar o matar, i el que se'n va aprendre. S'escriu perquè les
sessions següents no tornin a provar el que ja és mort, i perquè les lliçons de mètode no es
perdin amb el context.

## L'objectiu i la cadena

Entendre el que diu un home que explica lingüística amaziga **en amazic estàndard**, en 440
vídeos d'un canal de YouTube (25 escoltats fins ara, dues hores). La cadena, amb el que es
perd a cada graó:

| graó | com va (14-11-2026) | mesura |
|---|---|---|
| àudio → trossos pels silencis | bé | certesa 0,914 contra 0,84 amb talls fixos |
| tros → text amazic (ASR, MMS + adaptador shi) | **el mur**: ~40 % de les paraules no existeixen | 60,9 % reconegudes pel diccionari |
| text → glosses | 61 %, i una derivada de cada tres és falsa | 40 jutjades a mà |
| glosses → català | **9 de 40 bones, 16 a mitges, 15 falses** | auditor independent, llavor 1114 |

**El 8 % dels trossos amb text porta un català de què es pugui fiar algú.** Cap tros no és
«segur»: l'escala de tres graons té el de dalt buit (0 segur, 543 probable, 902 no s'entén).

## La lliçó de mètode del 14-11, abans de res

**Una mesura de l'entrada no diu res del resultat.** Es van arreglar tres errades de glossa
(245 aparicions que mentien amb seguretat, 985 segones lectures noves) i es van publicar amb
aquells números. L'auditor va tornar a jutjar la mateixa mostra de 40 amb el codi nou:
**9 bones abans, 9 bones després.** Els canvis havien caigut sobre paraules que el model ja
encertava pel seu compte. Des de llavors, tota millora es mesura **tornant a jutjar la mateixa
mostra**, no comptant glosses.

I una segona: **dues fonts d'acord no són una prova.** `inna` rep l'anglès «Mom» i el francès
«mère» d'acord, i és fals: aquí vol dir «va dir». L'acord entre fonts és un senyal, no un
veredicte.

## Hipòtesis mortes (no tornar-hi)

| hipòtesi | predicció | mesura | veredicte |
|---|---|---|---|
| El model fet per a l'estàndard (`/transcribe`, zgh) llegirà millor que el nostre adaptador de taixelhit | més paraules reconegudes | 58 talls idèntics, tifinag transliterat: shi 62,9 % / 0,884; zgh 57,0 % / 0,613, i esmicola (616 mots contra 448) | **morta** |
| Els subtítols automàtics del YouTube (`ar-orig`) donen una segona transcripció | text alineat | 38 paraules en 497 s, gairebé tot soroll | **morta** |
| L'alfabet (`ġ`/`ε` de l'ASR contra `ɣ`/`ɛ` del lèxic) perd un mot de cada cinc | més troballes traduint lletres | el lèxic ja normalitza: 0 formes noves, −68 | **morta** |
| Les paraules enganxades llargues són el problema | — | 1,7 % dels mots passen de 12 lletres | **morta** |
| Les repeticions són el problema | — | 1,1 % amb un grup de 3 repetit, i algunes són de debò | **morta** |
| Buscar la forma sabuda més semblant a cada perduda | més glosses | `hmmu`→«voltor» (és un nom d'home), `nkkwni` «nosaltres»→`nkkin` «jo» | **morta: fabrica** |
| Votar entre tres retalls de la mateixa imatge (Baba Ali) | menys error | 0,167, pitjor que el millor retall sol (0,100) | **morta** |
| Les glosses `=` falses són l'error dominant | predirien el veredicte | bo 11 %, a mitges 25 %, fals 20 %: no prediuen res | **morta** |
| Les variants empaquetades amb guions (`macc-micc-maccann`) són invisibles a l'índex | partir-les destaparia formes | `mac` es troba i diu «mais»: el problema és col·lisió de sentits, no visibilitat | **morta** (la prova primera era invàlida: mirava l'índex equivocat) |
| Traduir la classe sencera dona més català que tros a tros | més trossos amb frase | 40 contra 35 —però 11 eren fragments buits; amb la regla honesta, 29 contra 35 | **morta en quantitat**, viva en qualitat (no inventa) |

## La primera mesura contra veritat humana (14-11)

29 versos de dues cançons del canal amb la lletra transcrita a mà en tifinag (pista `la`),
tallats pels temps del subtítol i passats pels dos models del Space:

| model | CER | WER |
|---|---|---|
| **shi** (MMS + el nostre adaptador de taixelhit) | **0,307** | 0,809 |
| zgh (`ayymen/stt_zgh_fastconformer_ctc_small`) | 0,486 | 0,938 |

Confirma amb veritat humana el que el diccionari deia com a vara indirecta: el nostre
adaptador llegeix l'amazic estàndard millor que el model fet per a l'estàndard. **És cantat,
no parlat** (música, vocals allargades): el número és pessimista per al professor. El WER és
alt sobretot per espais —`ar saqquln` ↔ `arsaqqull`—, que el CER compta com a poca cosa.
Dada que reforça H1: `illa ar ittrgigi` surt `illa ar ittrgig` (CER 0,06): la còpula l'ASR
la sent bé; el que la perdia era el diccionari. Fitxers: `canal/veritat_cancons.json`.

## Hipòtesis vives

**H1 · L'error dominant és que la glossa entrega els noms i es menja el verb.** Mesura de
l'auditor: 171 de les 220 aparicions de la còpula (`iga`, `tga`, `illa`, `tlla`, `llan`…)
arribaven absents o com a nom («Juniper», «Obligation», «action de pleurer»); «voler» 0 de 11
bones; `maša` («però») 93 vegades «Seek, Search». *Predicció:* amb la taula
`FORMES_GRAMATICALS` (paradigmes del manual del Peace Corps Marroc 2007 + diccionari
d'Oulhaj), els «a mitges» baixen i els «bons» pugen en tornar a jutjar la mostra de 40.
*Estat:* taula feta el 14-11; **pendent de la mesura de resultat** (re-judici de l'auditor).

*La raó mecànica, trobada per l'auditor:* les 77.412 formes conjugades de l'IRCAM **no
contenen ni una forma de `ili`, `g`, `ini` ni `iri`** — els quatre verbs més freqüents del
corpus (`sawl` «parlar» en té 41, i per això `sawlġ` sí que es glossa). Cap regla de
morfologia no pot trobar el que no hi és. La taula a mà no és una millora opcional: és
l'única via. Correccions de l'auditor incorporades: `g` vol dir «ser» **i** «fer» i cap
glossa no pot dir només «és»; `tga` és 3a femenina i també 2a; `tgi` és sobretot el negatiu
darrere d'`ur`; `lla` és també marca de progressiu a l'Atles; `ga` i `lan` no són lexemes
sinó l'ASR menjant-se una lletra, i van al normalitzador, no a la taula.

**H2 · Córrer dos mètodes i quedar-se l'acord.** Tros a tros i classe sencera coincideixen
en 16 de 92; aquells 16 són els fiables. *Predicció:* la precisió de l'acord és molt més alta
que la de qualsevol dels dos sols. *Estat:* pendent de jutjar els 16.

**H3 · Descodificar amb el lèxic a dins** (cerca en feix + llista de formes). Ataca el mur
del graó 2. *Estat:* no començat; demana ruta nova al Space.

**H4 · Adaptar l'ASR amb l'àudio del canal sense text** (preentrenament autosupervisat sobre
les 440 peces del mateix parlant). *Estat:* catàleg del canal en marxa; demana GPU i decisió
de llicència.

**H5 · El canal té subtítols humans en alguns vídeos.** *Estat (14-11, 184 de 440 mirats):*
**confirmada.** 11 vídeos amb àrab i anglès humans —10 cançons i 1 conte—, 27 minuts. I dos
d'ells (`X7_kAT8_J64`, `o21uxEQoczE`) duen una pista `la` que és **l'amazic transcrit en
tifinag a mà, amb temps**: «ⴰⵎⵖⴰⵔ ⵏⵏⵖ ⵉⵣⵡⴰⵔ» ↔ «Our leader moved forward». Això és àudio ↔
text amazic ↔ traducció, els tres humans i alineats: la primera **vara de veritat** que tenim
per a l'ASR en amazic estàndard, i parelles de traducció de debò. Cantat, no parlat: mesura la
llengua, no la veu del professor. Fitxers a `scratchpad/canal/subs_humans/`.

## El que bloqueja

- **Deu minuts transcrits per un parlant.** Sense això tota mesura és indirecta. Serien
  alhora la vara i la primera llavor d'entrenament.
- **Llicència.** Material de tercers, `license` buit. Catalogar sí; entrenar-hi i servir-ho,
  no sense permís escrit.

## Fonts consultades

- Peace Corps Morocco, *Tamazight Textbook* (2007): paradigmes de `g`, `ili`, `iri`;
  preposicions; `walaynni`/`walakin` «però»; `digs` «dins d'allò».
- Diccionari d'Oulhaj (al lèxic del projecte): `macc-micc-maccann` pos=conj. «But»;
  `mac` «cependant, mais»; `sawal` consta `pos: n.` «Tick» amb exemple `ar ukan tesawal`.
- Wikipedia, *Central Atlas Tamazight*: còpula sovint absent; `g` com a còpula.
