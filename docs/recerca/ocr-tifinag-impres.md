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
