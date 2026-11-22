# OCR del tifinag cremat de Tamazight TV (SNRT): mesura oficial

Ref #601. Data: 17-11-2026. Aquest document és el registre del que se sap i del que no sobre el lector de tifinag de la fàbrica
(`tools/snrt/fabrica/lector_tifinag.py`). Les xifres són les que en Pablo ha pogut revisar a mà; res d'aquí no s'ha mesurat
contra una font que no sigui humana.

## Què és el problema

Els subtítols de Tamazight TV porten dues línies cremades al vídeo: el tifinag a dalt i l'àrab a sota. El tifinag és **Tifinaghe-Ircam
Unicode** (la font oficial de l'IRCAM), blanca amb vora fosca d'1,5 px, cos de 28 px a 1080p (files 884–910, centrada a x ≈ 964).
La font es coneix i les dades es poden fabricar a voluntat, però el fons és un vídeo real: parets clares, reflexos, plecs, canvis de
color a mig mot, i JPEG.

## La mesura oficial

Tots els números són **per lletra o caràcter** comptant els espais, amb la veritat feta per en Pablo (corregeix el que el sistema
llegeix; el que no toca queda com a bo). «Net» vol dir que ningú no ha afinat res mirant-ne les imatges abans de mesurar.

| conjunt | què és | mesura | estat |
|---|---|---|---|
| 100 línies | entrevista a 1080p, a l'atzar, sense crèdits | **CER 0,0009**, 99 de 100 perfectes | net; lector d'abans de les darreres millores |
| 50 línies | entrevista, ids congelats abans de mirar res | **≈ 0,0019 en lletres** (2 errors de 1.071), 37 de 41 línies perfectes. Les quatre amb error: un ⵃ llegit en lloc de ⴷ, un ⵯ perdut i les dues línies de «2026» (el mateix error de xifres) | net en el moment de mesurar |
| 40 discrepàncies | «Illy»: línies on el lector antic i el nou diferien | 32 de 40 perfectes (CER 0,0234, 25 errors de 1.069) | no net: triades per ser difícils |
| 52 línies de veritat | «Illy», transcrites a mà | CER 0,0051 (7 errors de 1.370), 46 de 52 perfectes | **afinat aquí**: no és una mesura neta |
| 15 línies d'en Pablo | «Illy», revisió alineada | CER 0,0034 (1 error de 293) | no afinat |
| 105 lletres dubtoses | triades per baixa confiança | 98 ben llegides (99 després dels últims canvis) | difícils per construcció |

Cinc dels set errors de les 52 línies eren **ⴳ llegit ⵅ**; en Pablo va decidir que el lector tenia raó i que la transcripció a mà
s'equivocava («ⵡⴰⵅⵅⴰ», no «ⵡⴰⴳⴳⴰ»). Amb aquesta correcció el CER real d'aquell conjunt és ≈ 0,002.

**Després d'aquesta mesura** (PR amb xifres per forma, ⵯ fi i separació per plantilla): les 50 línies passen a 0 errors i les 40
discrepàncies a 23 errors (33 de 40 perfectes). **No és una mesura:** tres de les 50 línies s'han mirat per arreglar-les (el «2026»,
el ⵯ darrere «ⴰⴽⴽ» i un ⵃ llegit en lloc de ⴷ) i les 40 discrepàncies han servit per dissenyar dues regles. Per saber el nombre
real d'ara cal un conjunt nou.

Per comparació, el punt de partida (el CRNN de línia entrenat només amb 2.000 línies sintètiques) feia CER 0,050 sobre les 52
línies, sense llegir cap de les 12 comes.

## Què s'ha après de la segmentació

El lector és ara un **segmentador de glifs + un classificador de plantilles** i no cap model entrenat. Què va funcionar, per ordre
d'importància:

1. **Un píxel és de lletra si és blanc i és entre dues vores fosques.** És una prova a cada píxel, en quatre direccions, no un
   llindar global. El fons clar és blanc però només té vora per un costat o cap: no passa. Va acabar d'una vegada amb els requadres
   de 3–7 lletres fusionades sobre fons clar, els reflexos i les sabates.
2. **Components connexos i fusió només per formes conegudes**: ⵓ, ⴻ, «?», «:» i l'anell amb punt de ⵙ són peces apilades; la coma i el punt
   són peces petites sota la base; ⵯ són dues marques fines a dalt.
3. **Límit d'amplada** (≈ 1,2 × el cos = 34 px) i **tall per buits de columnes**. Una columna sense cap píxel de lletra entre
   dues lletres és la separació; el tall només s'accepta si el buit fa ≥ 3 px i, si la plantilla encaixa millor el component sencer,
   no es talla. Un buit d'1–2 px és soroll de JPEG dins d'un glif.
4. **La plantilla tria el tall** quan no hi ha buit (dues rodones tangents, ⴰ+ⵔ sobre fons clar): la projecció sola no distingeix el punt de
   contacte de dues rodones del mig d'una sola rodona.
5. **Filtre d'extensió**: el text és centrat; els components fora de l'extensió més centrada, a menys de 12 px de la vora de la franja o
   de l'alçada del cos són fons.
6. **Classificar glif a glif amb plantilles de la font** (IoU a l'escala de la línia, ±2 px) guanya el lector de línia: 0,0051 contra
   0,0445 amb el mateix retall. El CRNN no llegeix comes i, si se li neteja el fons, empitjora (no ha vist mai fons plans).
7. **Les xifres s'han de comparar per forma**, no a la y absoluta: a «Illy» baixen 2 px sota la base i a l'entrevista pugen 7 px sobre el cos.

**Provat i descartat:**
- Un desempat entre les dues millors plantilles mirant «on es diferencien» (ⵙ/ⵀ, ⵜ/ⵏ) va fer pujar el CER de 0,0234 a 0,0458: la zona exclusiva
  és dominada per la diferència de l'anella, no pel punt o la barra.
- Partir per buits d'1–2 px parteix lletres bones (una ⵥ en dues).
- Substituir el fons fora dels glifs per un color pla (per al CRNN).

## El que no se sap

- **720p real.** Només hi ha una simulació (les mateixes línies baixades a 2/3: CER 0,0073). Les confusions ⵎ/ⴹ a 20 px de cos són conegudes.
- **Sèries d'acció** (fons que es mou, canvis de llum ràpids): només s'han mirat «Illy» cap. 1 i l'entrevista «Tadfi n Tskla».
- **Xifres.** Només 2, 0, 6 i 8 es llegeixen amb glifs reals; **1, 3, 4, 5, 7 i 9 no s'han vist mai** i hi ha Arial com a recurs. Les plantilles de 2, 0, 6 i 8
  surten dels glifs de les mateixes línies que les proves.
- **ⵙ confosa amb ⵀ** (IoU 0,74 contra 0,73 a vàries línies): 0101, 0191, 0320 i 0322 de les 40 discrepàncies. L'anella real fa 28 px d'alt i la
  plantilla de ⵙ en fa 27.
- **Fons clar amb canvi de color dins la paraula** (0076, 0320, 0321): la creu perd el braç horitzontal al límit fosc/clar; una ⵓ amb les boles
  separades es descarta.
- **Tipografia d'altres canals o temporades**: la font s'ha identificat només en aquests vídeos.

Proposta per resoldre-ho: (1) per a ⵙ, mirar l'interior de l'anella (un punt contra una barra que toca dalt i baix) en lloc de l'IoU global, i afegir
variants d'escala d'1 px a les plantilles; (2) llindar local de fons per glif, calculat després del primer pas; (3) més veritat humana dels casos
difícils (fons clar, ⵓ, ⴳ/ⵅ, ⵙ/ⵀ).

## Com tornar a mesurar

1. **Només es mesura amb un conjunt nou.** Un conjunt revisat i després corregit ja no és un conjunt de prova.
2. Treure 50 fotogrames a l'atzar (llavor fixa) d'un vídeo que el lector no hagi vist, excloure crèdits (les línies que no encaixen amb les
   plantilles de la font) i **congelar els ids en un fitxer abans de mirar res**.
3. Generar el full de revisió alineada (la mateixa interfície que `illy_01/revisio_illy_alineat.html`: caixa per lletra, lletra a sota, teclat tifinag a la pantalla),
   que en Pablo corregeix. El que no toca és bo.
4. Calcular el CER lletra a lletra: el text del full amb les correccions aplicades per glif, contra la lectura. Entre xifres no hi ha espais.
5. **No afinar res mirant-ne les imatges.** Si cal, es fa un conjunt nou després.

Eines: `tools/snrt/fabrica/prova_lector_tifinag.py <carpeta_tipografia>` reprodueix els 0,0051 de les 52 línies (necessita les imatges, que no són al
repositori). Les mesures de les altres conjunts (`cer15.py`, `cer40.py`, `cernet.py`, `avalua_dubtes.py`) són al PC, a
`Veus-tachelhit\_escoltats\tamazight_tv\tipografia\segmentacio\`, junt amb `segmenta.py`/`plantilles.py` d'on surt el codi del repositori i els fulls.
