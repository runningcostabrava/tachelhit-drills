# Lector per plantilles del tifinag imprès (#622, #457) — primera prova: el conte del gat d'aslmdtv

Fet el 15-11-2026 per un agent sobre el vídeo `ZlG8Bp_rwKc` (aslmdtv, «ⵜⵓⵍⵍⵉⵙⵜ: ⴰⵎⵓⵛⵛ ⴰⴱⵕⴱⴰⵛ»).
Cap model, cap servei extern: numpy + PIL + scipy.ndimage i els ulls. El codi és a
`tools/ocr_tifinag/` i es fa córrer dins d'una carpeta de treball que tingui el vídeo:
`fotogrames.py` → `glifs.py` → etiquetar `grups_full.png` a `etiquetes.json` → `transcriu.py`.
Les dades (fotogrames, línies, grups, transcripció) són a
`C:\Users\josep\Veus-tachelhit\_escoltats\aslmdtv\ocr_ZlG8Bp_rwKc\`. Material de tercers: es
llegeix i es mesura; res a la biblioteca sense permís.

## Què s'ha fet i amb quins números

| Pas | Guió | Resultat |
|---|---|---|
| Fotogrames cada 0,5 s | `fotogrames.py` | 1.355 fotogrames (677 s) → `fot/` |
| Text vermell per fotograma | `fotogrames.py` | 1.031 trams → `linies.json`, `linies/NNN.png` |
| Pàgines | `fotogrames.py` + `glifs.py` | 40 "pàgines" detectades, **20 reals** (les altres 20 són el fotograma de transició entre pàgina i pàgina, 0,5 s) |
| Files de text | `glifs.py` | **140 files**, 849 paraules |
| Glifs | `glifs.py` | **3.552 glifs** segmentats |
| Grups | `glifs.py` (enllaç mitjà, semblança ≥ 0,90) | **75 grups** → `grups/grupNN.png`, `grups.json`, `grups_full.png` |
| Etiquetes | a ull | `etiquetes.json`: 28 lletres + 6 signes |
| Transcripció | `transcriu.py` | `transcripcio.json` (140 files amb de/a), `conte.txt` (tifinag + llatí) |
| Plantilles | `plantilles.py` | `plantilles.npz` (35 imatges mitjanes 32×32) per als altres vídeos |

Temps d'execució: `fotogrames.py` ~35 s, `glifs.py` ~15 s, `transcriu.py` < 2 s.

## La sorpresa: el vermell no és «la línia que es llegeix»

En aquest vídeo el vermell **s'acumula lletra a lletra** (karaoke): cada 0,5 s hi ha una lletra o
paraula més en vermell, i només es reinicia quan canvia la pàgina. Per això surten 1.031 trams
i no ~140. El pipeline ho aprofita: el **darrer tram de cada pàgina** conté tot el text de la pàgina
i és l'únic que es segmenta; els altres trams només serveixen per datar cada fila
(`de` = primer tram on la fila té vermell, `a` = primer tram on la fila és sencera). Les «línies
repetides en molts fotogrames» queden fusionades així, sense cap heurística de text.

## Trampes trobades (i com s'han resolt)

1. **El criteri r>150, g<90, b<90 trenca les lletres.** El nucli del traç és (216,0,0) però l'halo
   antialiàsat arriba a (240,168,144); amb el criteri estricte els glifs sortien a trossos i es
   perdien paraules senceres. Vermell = `r>120 & r-g>40 & r-b>40` (el text negre dona 0 píxels).
2. **Amb l'halo, les lletres veïnes es toquen** i els components connexos ajunten paraules senceres
   (la primera passada tenia grups com «ⵓⵎⵓⵛⵛ» sencer). Solució: el retall es desa a tres nivells
   (nucli / halo / fons); se segmenta pel nucli i la forma es pren amb l'halo.
3. **El punt interior de ⵙ (i de ⴹ/ⵟ) fa 3-7 píxels** i el filtre de «< 8 píxels = soroll» el
   llençava: ⵙ sortia com ⵔ. Es rescaten els components petits que cauen dins la caixa d'un glif.
4. **Els dos punts «:» i el punt «.» no existien** per la mateixa raó (components de 2-5 px, sense
   glif que els englobi). Es rescaten els components ≥ 3 px a la banda vertical d'un glif acceptat.
5. **«:» vs ⵓ**: tots dos són dos punts verticals. Es distingeixen per forma: ⵓ són dos anellets
   buits, «:» són dos punts plens i més petits (grup propi, 30 ocurrències, 12 com a paraula sola).
6. **Coma, punt i cometes són el mateix dibuix petit**; es resolen per posició a la fila (a dalt =
   cometa, a baix = coma, o punt si és molt baixet). La cometa d'obertura sovint se solapa amb la
   lletra següent i surt com un glif compost («"ⵎ», «"ⵓ», «"ⵍ»): s'etiqueten així.
7. **«!» vs ⵏ**: la barra i el punt de sota se solapen horitzontalment i s'ajunten; es desa el
   nombre de peces del glif i una barra de dues peces amb la de sota petita és «!».
8. **ⴱ vs ⵙ** (cercle amb barra / cercle amb punt) i **ⵟ vs ⴹ** (E amb signe dins / E plana) només
   se separen amb llindar de semblança ≥ 0,90 i enllaç mitjà; amb l'agrupament «per líder» a 0,80
   es barrejaven.
9. **La font**: ⵉ és la Σ (no la I), ⵊ és la I amb serifs, ⵍ són dues barres unides per una
   diagonal (И), ⴳ és el rellotge de sorra amb barres, ⵖ és la Y, ⵕ és la Q. Ho vaig comprovar
   contra l'alfabet IRCAM dibuixat amb la font Ebrima de Windows (`referencia_gran.png`) i contra
   paraules conegudes (ⵢⴰⵏ ⵡⴰⵙⵙ, ⵓⵔⴳⴰⵣ, ⵍⵍⵉⴳ, ⵉⵙⵇⵙⴰ, ⴰⴱⵕⴱⴰⵛ del títol).

## Etiquetes: segures i dubtoses

- **Lletres vistes (28):** ⵜ 440, ⴰ 434, ⵉ 328, ⵏ 266, ⵓ 225, ⵙ 181, ⴷ 164, ⴳ 140, ⵎ 112, ⵛ 100,
  ⵕ 96, ⵔ 93, ⴼ 87, ⴹ 85, ⵍ 83, ⴱ 80, ⵖ 76, ⵡ 66, ⴽ 66, ⵣ 54, ⵢ 46, ⵊ 44, ⵟ 43, ⴻ 24, ⵇ 23, ⵥ 14,
  ⵃ 5, ⵀ 1. Signes: «,» 49, «.» 30, «:» 30, «"» 22, «?» 12, «!» 10.
- **Mai vistes al vídeo:** ⵄ ⵅ ⵚ ⵯ (ni ⴳⵯ ni ⴽⵯ). No hi ha cap plantilla d'aquestes.
- **Segures:** 70 grups (3.506 glifs). Totes surten en paraules reconeixibles i la forma coincideix
  amb l'IRCAM.
- **Dubtoses:**
  - **ⵊ** (4 grups, 44 glifs, 25 files afectades): la «I amb serifs» és la forma IRCAM de ⵊ i quadra
    amb ⵓⵊⴹⵉⴹ (*ajḍiḍ*, ocell, en tamazight de l'Atles), però surt també a ⵓⴳⵍⵉⴷⵊ, ⵉⵊⵊⵉⵊ i
    ⵊⵕⴰⵏ, que no sé llegir. Cap altra lletra de l'alfabet té aquesta forma; la deixo com a ⵊ i
    marcada a `dubtes` de cada fila.
  - **g52** (2 glifs): grup barrejat, un ⵟ i una ⴹ; a la pàgina 8 «ⵜⵎⵟⵟⵓⵟⵜ» l'últim ⵟ segurament
    és ⴹ.
- Grups de **trossos**: una ⴷ i una ⴰ partides en dos components (g58+g59, g71+g72) s'etiqueten
  «lletra» + «» perquè el transcriptor no les dupliqui.

## Comprovació a ull (5 files, llavor 1114, `comprova.py`)

| Fila | Pàgina | Glifs | Transcripció | Bé/total |
|---|---|---|---|---|
| 64 | 16 | 31 | ⵓⴳⵍⵉⴷⵊ ⵉⵙⵜⵜⵓⵜⵜⵉ ⴰⴼⵔⵉⵡⵏ ⵏⵏⵙ ⴳⴼ ⵓⴳⴹⵉⴹ, | 31/31 |
| 114 | 27 | 24 | ⵎⴰⴳ ⴰⵢⵍⵍⵉⴳ ⵜⵕⵥⵉⴷ ⵜⵉⴼⵉⵍⵜ ⵏⵏⴽ? | 24/24 |
| 115 | 27 | 14 | ⵉⵔⴰⵔ ⴰⵙ ⴷ ⵎⴻⵎⵎⵉⵙ: | 14/14 |
| 130 | 31 | 13 | ⵜⵙⵃⵉⵍⵍⴻⵍ ⵖⵉⴼⵉ. | 13/13 |
| 135 | 34 | 41 | ⵏⵏⴽ, ⵜⵛⴷ ⴰⵙ ⵜⵜ ⵉ ⵓⵎⵓⵛⵛ ⴰⴷ ⵜⵜ ⵉⵜⵜⵛ, ⵉⴷ ⴽⵢⵢⵉⵏ ⴰ ⴰⵔⴳⴰⵣ ⴰⴷ | 41/41 |

**123/123 lletres i signes** (les imatges són a `fulls/comprova_0..4.png`). La fila 64 conté la ⵊ
dubtosa: la *forma* és la que és; el dubte és quina lletra representa, no si s'ha llegit bé.

## Errors que sí que he trobat (escombrant les fórmules que el conte repeteix)

El conte és acumulatiu («ⴳⴼ ⵜⵖⵕⵕⴰⴼⵜ ⵜⴻⵜⵜⵓⵜⵜⵉ ⵉⴷⴷⵖ ⴰⵎⵓⵛⵛ ⴰⴱⵕⴱⴰⵛ ⵉⵜⵢⴰⴱⴱⵉ ⴰⵙ ⵓⴱⵕⴹⵓⴹ…» surt 9 cops),
i vaig mirar al fotograma cada repetició que no quadrava:

- **ⵉⵜⵢⴰⵙⴱⵉ** (pàgina 18): al llibre hi ha ⵉⵜⵢⴰⴱⴱⵉ; una ⴱ (⊖) ha caigut al grup de ⵙ (⊙). **1 glif
  malament de 3.552.**
- **ⵜⵎⵟⵟⵓⵟⵜ** (pàgina 8): probablement ⵜⵎⵟⵟⵓⴹⵜ (el grup barrejat g52). **1 glif probable.**
- Tot el que semblava error i **no ho era** (el llibre ho escriu així): ⵉⵜⵜⵢⴰⴱⴱⴰ, ⵜⵓⵜⵜⵓⵜⵜⵉ,
  ⵉⵜⵖⵕⵕⴰⴼⵜ, ⵉⵙⵜⵓⵜⵜⵉ, ⵉⵙⵙ ⵉⴳ, ⵜⵎⵟⵟⵓⴹⵟ, ⵜⴰⴹⵡⵡⴰⵕⵟ, «ⵉⵊⵕⴰⵏ!,». Lliçó: mesurar contra el fotograma,
  no contra el que «hauria de dir».
- Decisions tipogràfiques meves, no del llibre: trec l'espai abans de «, . : ? !» (el llibre escriu
  «ⵏⵏⵙ :») i en poso un després si segueix una lletra; una cometa partida en dues meitats es
  fusiona en una.

Estimació honesta de l'encert global: ≥ 99,5 % dels glifs (2 errors coneguts; el mostreig de
123 no n'ha trobat cap), **més el dubte sistemàtic sobre quina lletra és la «I»** (44 glifs).

## Observacions sobre el text

- Pàgines reals: 20 (14,5 s → 665,5 s). La fila més llarga té 41 glifs; les pàgines tenen de
  3 a 10 files.
- El conte està escrit més aviat en **tamazight de l'Atles central** que en tachelhit:
  *ajḍiḍ* (ocell), *memmis* (el seu fill), *tettutti*, *mag ayllig*… Val la pena saber-ho abans
  d'incorporar-ne el lèxic a l'app.
- El llatí de `conte.txt` surt de `to_forms()["clean_latin"]` del projecte: ⵛ → š, ⵖ → ɣ, etc.

## Què caldria per llegir els altres 19 vídeos del canal

1. **Comprovar la font.** Tot el que hi ha aquí és per a *aquesta* tipografia (traç ~2 px, caixa
   alta ~16 px a 640×360). Si el canal fa servir la mateixa maqueta de llibre escolar, les
   `plantilles.npz` serveixen tal qual; si no, cal repetir el pas d'etiquetar (una hora amb
   `grups_full.png` i `paraules.py`).
2. **Un classificador per plantilla** (`llegeix.py`, no fet): per a cada glif nou, la plantilla amb
   correlació màxima; si cap passa de ~0,85, glif nou → mosaic per etiquetar. Les regles de
   `transcriu.py` (coma/cometa per posició, «!» per peces, «:» per forma) s'hi han de portar.
3. **Si el vídeo no té karaoke vermell** (text negre fix), cal la mateixa cadena amb màscara de
   negre (`min(r,g,b) < 110`) i detectar les pàgines per canvi de contingut; es perd la datació
   per lletra, però el text surt igual. Si hi ha vermell, la datació per fila surt gratis.
4. **El que encara no sap fer:** ⵯ (no n'hi ha cap exemple), ⵄ ⵅ ⵚ (cap exemple), text sobre fons
   no blanc (el filtre d'anell descarta tot el que no seu sobre paper), lletres partides per
   compressió (apareixen com a grups d'1 exemplar: 19 dels 75 grups són singletons, gairebé tots
   trossos o variants).
5. **Els dos punts febles mesurats:** ⴱ/ⵙ (1 confusió en 261) i ⵟ/ⴹ (1 en 128). Es podria afegir
   una segona passada amb plantilles només d'aquests parells a resolució doble.
6. **Validació:** el mateix protocol d'aquí (5 files a l'atzar amb llavor fixa + escombrada de
   repeticions) per a cada vídeo nou, abans de comptar-ne res com a text.

## Fitxers de treball (no demanats, però útils)

`zoom.py` (retall d'una pàgina amb caixes i número de grup), `zoom_fot.py` (retall del fotograma en
color), `paraules.py` (paraules senceres per grup o per text), `context.py` (on surt un grup),
`full_linies.py` (fulls de contacte dels trams), `referencia*.py` (alfabet IRCAM amb Ebrima),
`sonda*.py` (histogrames de color que van destapar l'halo). Les imatges de revisió són a `fulls/`.

## Segon i tercer vídeo (`llegeix.py`, plantilles del primer)

`llegeix.py <vídeo>` fa la cadena sencera i classifica cada glif per **plantilla més propera**
(`plantilles.npz`, correlació sobre la imatge 32×32). Dues passades: la primera amb les plantilles
del vídeo 1 (llindar 0,80), la segona amb **plantilles adaptades** = mitjana dels glifs acceptats a
la primera (mateixa lletra, altra mida i gruix). Cada fila de cada pàgina se segmenta en fins a 12
trams i es queda **la versió amb més glifs acceptats** (animacions d'entrada, subratllat damunt les
lletres, transicions). Els glifs rebutjats van a `nous_<vídeo>.png` (+ `nous_<vídeo>.json`) i
`afegeix_plantilla.py <vídeo> <nouNN> <lletra>` els incorpora a les plantilles.

| | MTDbi14_5cU («ⵜⵉⵔⴰⵔⵜ ⵏ ⵜⵉⵖⵉⵍⵜ», nivell 3) | ihZ5sVr482o («ⴰⵎⵓⴷⴷⵓ ⵏ ⵟⴰⵕⵉⵇ», nivell 1) |
|---|---|---|
| Durada / fotogrames | 627 s / 1.253 | 563 s / 1.125 |
| Font | la mateixa, caixa alta 12-13 px (vídeo 1: 16) | la mateixa, caixa alta 17-21 px; portada i crèdits en una altra |
| Mode | **vermell**: la pàgina surt negra i les línies es tornen vermelles en llegir-les (línia a línia, no lletra a lletra); subratllat vermell sota la paraula llegida | **negre**: text negre fix, subratllat vermell mòbil; 8 files llegides 6-7 vegades |
| Trams / pàgines reals | 615 / 19 | 247 / 20 |
| Glifs classificats (tots els trams) | 18.056 | 7.067 |
| Glifs a les versions triades | 4.450 | 1.547 |
| **Acceptats per les plantilles** (llindar 0,85) | **4.406 (99,0 %)** | **1.473 (95,2 %)** |
| a 0,80 / 0,90 | 99,1 % / 97,6 % | 96,6 % / 94,1 % |
| Glifs nous (grups) | 44 (14): trossos de lletra, punts minúsculs, «!» enganxat a una cometa, brossa d'imatge. **Cap lletra nova** | 74 (42): **ⵄ** (10 exemplars, lletra nova), portada/crèdits en una altra font, 4 glifs d'un dibuix de gos, trossos |
| Files finals / glifs únics / nous | 51 / 2.079 / 11 | 50 / 921 / 38 |
| Lletres distintes al text | 26 | 24 (amb ⵄ, 6 cops) |
| **Comprovació a ull** (5 files, llavor 1114) | **235/242** | **96/101** |
| ⵯ ⵄ ⵅ ⵚ | cap | **ⵄ sí** (ⵄⵣⵣⴰⵏ, *ɛzzan*); ⵯ ⵅ ⵚ cap |

**Llindar:** 0,85. A 0,80 l'acceptació gairebé no puja i hi entren trossos i brossa; a 0,90 es
perden 2-3 punts de lletres bones (sobretot ⵔ ⵙ ⴰ en lletra petita). Sense la segona passada
adaptada, a 0,85 només s'acceptava el 86 % (vídeo 2) i el 84 % (vídeo 3).

**Els 7 errors del vídeo 2 (de 242):** 4 signes de puntuació no detectats («!» «,» «;» de 1-2 px
en lletra de 13 px), 1 punt sortit com □, ⵉⵏⵏⴰ→ⵉⵜⵏⴰ (ⵏ+subratllat llegit ⵜ), ⴽⵢⵢ→ⵍⵢⵢ (cometa
d'obertura enganxada a la ⴽ, que no té plantilla composta). **Els 5 del vídeo 3 (de 101):** una ⵏ
rebutjada (ⵡⴰⵏ→ⵡⴰ□, 3 cops al text) i 4 □ d'un dibuix dins la columna de text. Cap lletra
llegida com una altra lletra, llevat del cas de la cometa.

**Què ha calgut canviar en el camí (i per què):**
1. El subratllat vermell toca les lletres: s'esborren les tirades horitzontals ≥ 20 px **del nucli**
   (fer-ho sobre l'halo esborrava traços de lletres veïnes: 4.527 → 4.184 glifs).
2. Lletra petita: el nucli vermell passa a `g<115,b<115` perquè els arcs prims de ⵔ ⵙ ⴰ no es
   partissin en «( )». Una regla de «fusió de meitats» es va provar i **es va treure**: ajuntava ⵏⵏ
   en una ⵍ (`--repara=1` la torna a activar; no la facis servir).
3. La **millor versió de cada fila** entre 12 trams: és el que ha fet passar el vídeo 2 del 92 % al
   99 %; les files a mig escriure (animació) i les subratllades perden sempre.
4. Mode per presència de vermell (≥ 25 % dels fotogrames), no per recompte de glifs: el vídeo 2 té
   pàgines negres abans de llegir-les.
5. L'anell de «paper blanc» ignora ara l'halo d'1 px al voltant del text: una ⵏ de 2 px d'ample
   queia sota el 85 % de blanc (ⵢⴰ ⵡⴰⵙⵙ sense la ⵏ en totes les repeticions). Això és a
   `fotogrames.py` i afecta també el vídeo 1, que **no s'ha tornat a passar** (els resultats del
   primer informe són amb el criteri antic).
6. Files que són un tros d'una altra de la mateixa pàgina, o amb < 3 lletres, fora.

**Pendent:** detector de dibuix dins la columna de text (el gos), plantilles compostes «cometa +
ⴽ/ⵙ/ⵜ…» o millor separar la cometa abans de classificar, puntuació d'1-2 px en lletra de 13 px, i
el títol/crèdits en una altra font (ara surten com □ i es descarten sols). Els textos són en
tamazight de l'Atles central com el primer (*ɛzzan dri imudar*, *skkur*, *tiɣilt*).

## El nostre lector d'ASR sobre el text llegit (15-11, nit)

Amb la transcripció per plantilles del conte del gat com a veritat (`tools/lm/zouhir_mesura.py`,
pista `tif` = files amb temps del karaoke; pista `pag` = pàgines senceres):

| unitat | n | CER greedy | CER feix + lèxic | WER feix |
|---|---|---|---|---|
| fila (temps del karaoke) | 140 | 0,384 | 0,373 | 0,763 |
| **pàgina** (temps fiables, −0,5 s / +1,5 s) | 20 | **0,276** | 0,304 | 0,699 |

Els temps del karaoke van per darrere de la veu i tallen les files: la mesura bona és la de
pàgina. Nivell de Zouhir (0,22-0,33) en una varietat mai vista pel model. El lèxic al feix
tampoc no hi ajuda (com a Zouhir): el pes es revisa amb el test gran. Per a H4 cal tallar per
fila amb l'alineador del Space, no amb el karaoke.

## El lot del canal (16-11, matí; `lot.py`, `corpus.py`)

`lot.py [quants]` fa el canal d'un vídeo en un: baixa (yt-dlp, client android), `llegeix.py`,
`comprova.py` sobre 3 files (llavor 1114), apunta els números a `lot_estat.json` i esborra el mp4
i els fotogrames. `corpus.py` ajunta totes les transcripcions a `corpus_aslmdtv.json` i regenera
la taula a l'informe. Dels 63 vídeos amb títol en tifinag, 13 llegits (els 3 primers + 10 del lot):

| vídeo | mode | pàg. | glifs triats | acceptats | files | a ull | notes |
|---|---|---|---|---|---|---|---|
| o5xWviSCRF8 | vermell | 29 | 177 | 94,9 % | 9 | 14/15 | lletres soltes ⵜ ⵎ ⴳ |
| 7ZWFXQNmNME | vermell | 22 | 321 | 95,3 % | 28 | 21/21 | |
| OTwsywhExOA | vermell | 51 | 295 | 89,5 % | 16 | 10/19 → les ⴽⵯ bé amb la regla nova | **ⵯ, lletra nova** (16) |
| ZX8o-g4yHwk | negre | 8 | 766 | 95,8 % | 40 | 72/73 | |
| z6L6zGYmkkU | vermell | 16 | 44 | 72,7 % | 4 | 10/12 | escriure ⵍ ⵡ soltes: gairebé sense text |
| EA2PwuXroPw | negre | 41 | 3.096 | 69,1 % | 103 | 33/35 | diàleg bo; el 69 % són 60 s de rètols sobre dibuix (filtrats) |
| 4_2DUAo9aGQ | negre | 38 | 3.281 | 72,1 % | 99 | 37/42 | mateix text que l'anterior |
| -SVf_yOmRb8 | negre | 23 | 1.009 | 91,5 % | 45 | 65/65 | a la 1a passada sortia buit (rètols vermells del dibuix) |
| QFQqZdiMIFE | vermell | 7 | 694 | 87,5 % | 15 | 82/96 | títol en lletra ombrejada (5/14) |
| AH-2VjGwmHo | vermell | 10 | 206 | 96,6 % | 7 | 18/19 | una coma que era el cursor |

**Corpus: 571 files de 13 vídeos, 2.921 paraules, 11.706 glifs, 30 lletres distintes**, 101 files
amb algun □ (camps: vídeo, títol, mena, pàgina, fila, de, a, tifinag, llatí, dubtes). Els vídeos
amb text de pàgina van del 91 al 97 % de glifs acceptats i de 65/65 a 72/73 a ull; els que baixen
del 90 % ho fan per brossa de dibuixos, títols ombrejats o requadres, no per una font diferent.

**ⵯ (labialització)** apareix en dues formes: signe petit alçat rere ⴳ/ⴽ i doble tick; plantilla
(56 exemplars) més regla de posició. ⵄ ja hi era; **ⵅ i ⵚ no han aparegut encara** en 13 vídeos.
Tres correccions del camí: mode negre si el vermell no hi és tant com el negre (abans tres
diàlegs sortien buits); files de brossa fora (< 3 lletres o < 60 % de glifs acceptats, també al
corpus); ⵯ. Errors que queden: «:» de rèplica llegit com a cometa, puntuació d'1-2 px, files
captades a mig animar-se, rètols en una altra font (□ i es descarten).

Material de tercers (#622): el corpus es cataloga (`Veus-tachelhit\_escoltats\aslmdtv\ocr\`), res
a la biblioteca ni al model sense permís.

### El canal sencer (16-11, migdia): 63 vídeos, 1.034 files, 5.215 paraules

Lot acabat: els 63 vídeos amb títol en tifinag, cap baixada fallida, uns 30-70 s per vídeo. La
taula completa és a `tools/ocr_tifinag/lot_estat.json` (per vídeo: mena, mode, pàgines, glifs,
acceptats, files, a ull i nota) i al `INFORME.md` de la carpeta durable.

**Corpus `corpus_aslmdtv.json`: 1.034 files de 46 vídeos, 5.215 paraules, 20.962 glifs, 30 lletres
distintes**; 225 files duen algun □. Rares: ⵯ 131, ⵀ 50, ⵃ 25, ⵄ 6. **ⵅ i ⵚ no apareixen en cap
vídeo del canal**, ni als de lletres que les anuncien al títol (hi surten soltes amb dibuix, no en
text): el llibre escolar no les fa servir en el text corrent.

**On és el text de debò**: 17 vídeos amb ≥ 5 files i ≥ 85 % de glifs acceptats, que sumen la
quasi totalitat del corpus: els tres primers (conte del gat 140, 51, 48), el conte ⴰⵡⵍⴽ ⴰⵎⴰⵔⵉⵔ
(106), dues lectures amb el mateix text (92/84), vuit lectures més (10-44 files cadascuna) i la
cançó ⴱⵓⵙⴰⵍⵎ (55 files, 98 % acceptats). A ull, en aquests 17: **1.312 de 1.374 glifs, 95,5 %**.

**La resta del canal no és text**: 20 vídeos de lletres soltes, números i exercicis amb dibuix
(0-2 files), 3 classes de didàctica en àrab, i 9 fora de l'abast del lector per la forma, no per
la llengua: quatre fonts que no coneix (contorn rosa `5g8RjeTJioY`, contorn vermell `K4XK3GB7_kI`,
rodona manuscrita `ID_xZaneDyo`, graella infantil `HtAC0IZGq2c`), diapositives de pal sec
(`-Gqm1vfnCzg`), bafarades de color (`Eunlkgrf6oU`: el text no seu sobre blanc i l'anell el
descarta), lletra gegant sobre pauta (`3x9jKLeDfBo`) i caixes d'exercici en lletra prima
(`ZhQgHYUECDs`). Errors recurrents per a la propera iteració: «:» i «1)» d'inici de rèplica
llegits com a cometa, ⵀ→ⵙ, ⵕ→ⵙ, la ⴰ petita perduda sobre fons de color, puntuació d'1-2 px,
files captades a mig animar-se.

**Què val això.** És el primer text imprès en tifinag de l'Atles central que tenim llegit amb la
seva veu al costat (el karaoke en diu els temps, encara que vagin per darrere de la parla). Serveix
de tercera veritat per al lector quan s'alineï amb el Space, i de text real per al lèxic i el
glossador. El canal queda **tancat com a font**: el que hi havia per llegir, llegit. Pendent de
l'amo: permís de l'autor abans que res d'això entreni el model servit o entri a la biblioteca.
