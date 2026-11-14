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
| Les paraules enganxades llargues són el problema | — | 1,7 % dels mots passen de 12 lletres | **morta — però la vara era dolenta**: mesurava mots LLARGS, i el que destrueix paraules del diccionari són mots CURTS enganxats (`ayingratsnt` = `ay ingr atsnt`, que es menja `amzaray` «diferència»). Dels 8 falsos que queden després de la taula, 4 són cadenes d'ASR irrecuperables i 1 és això. Torna com a H6 |
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

**I la mesura que compta més: amazic estàndard NARRAT, 226 versos de 8 contes** (The
Traveller 1–5 via les pistes `ak-*`, més `o21uxEQoczE`, `oFVo66DStDc`, `tR-hRjd9O-k`), amb la
lletra transcrita a mà en tifinag:

| model | CER | WER |
|---|---|---|
| **shi** (MMS + el nostre adaptador) | **0,210** | 0,718 |
| zgh | 0,435 | 0,884 |

Estable entre vídeos (shi 0,18–0,24; zgh 0,35–0,51). Parlat va millor que cantat (0,307 →
0,210), com s'esperava, i el nostre adaptador guanya el model d'estàndard per més del doble a
tots vuit. El WER alt amb CER baix diu el de sempre: el que falla són els espais, no les
lletres. **Aquest 0,210 és la línia de base contra la qual s'ha de mesurar el lector amb el
lèxic a dins (H3) quan es desplegui.** Fitxers: `canal/veritat_parlat.json`.

**El que aquesta veritat acota (auditor, 14-11).** Tot el que s'ha jutjat sobre els 40 trossos
de les classes és **consistència interna** —la casella és fidel a la glossa i a la cadena de
l'ASR—, no veritat: amb WER 0,72 una casella pot ser una traducció impecable d'un token que
l'ASR s'ha inventat. I **cap de les 31 classes no té subtítol humà**: els 1.468 trossos no es
podran validar mai directament. L'única prova contra l'àudio és passar la canonada de fets pels
226 versos narrats i mirar sobre quins tokens cauen les caselles (cert / substituït / inserit,
per alineament amb la veritat). *Estat:* en marxa (`fets_veritat.py`). Avís d'abast: narració
no és classe; el número no es trasllada sense dir-ho. També enterra del tot la vara «el
diccionari el reconeix» (70,1 % dels mots) contra un WER de 0,72: reconegut no vol dir
correcte — amb la matisació que el WER compta cada espai mal posat com un mot errat (`ar
saqquln` ↔ `arsaqqull`), i el CER de 0,21 diu que les lletres hi són molt més que els mots.

## Hipòtesis vives

**H1 · L'error dominant és que la glossa entrega els noms i es menja el verb.** Mesura de
l'auditor: 171 de les 220 aparicions de la còpula (`iga`, `tga`, `illa`, `tlla`, `llan`…)
arribaven absents o com a nom («Juniper», «Obligation», «action de pleurer»); «voler» 0 de 11
bones; `maša` («però») 93 vegades «Seek, Search». *Predicció:* amb la taula
`FORMES_GRAMATICALS` (paradigmes del manual del Peace Corps Marroc 2007 + diccionari
d'Oulhaj), els «a mitges» baixen i els «bons» pugen en tornar a jutjar la mostra de 40.
*Resultat (14-11, mateixa mostra de 40, llavor 1114, tres passades):*

| | desat | taula nova (A) | taula nova, 2a crida (B) |
|---|---|---|---|
| bo | 9 | 10 | 9 |
| a mitges | 16 | 13 | 14 |
| **fals** | **15** | **8** | **8** |
| s'absté | 0 | 9 | 9 |

*Codi:* PR #604 fusionat a `main` el 14-11 (CI verda, proves del backend 4m44s).

**Veredicte: H1 es reformula.** El verb absent no era el que es menjava el significat: era el
que donava **permís per inventar-lo**. Donar-li el verb no afegeix comprensió (bo 9→10→9, i
entre dues passades amb entrada idèntica 8 de 40 canvien de veredicte: la casella «bo» es mou
±1 tota sola); **treu la llicència**: els falsos cauen de 15 a 8, i les dues passades donen
8 i 8 —zero soroll en aquesta casella. Sobre el que es deixa veure, falsos del 37,5 % al
25,8 %. Nou de 40 ara s'abstenen, cinc dels quals eren falsos. Una frase falsa és pitjor que
un buit, o sigui que això val; però no és comprensió.

Dos senyals d'aquesta mesura que manen el que ve: **(1)** amb entrada idèntica el model canvia
8 veredictes de 40 → cap millora de ±1 no vol dir res, i cal una mostra més gran o més
passades per dir res dels «bons». **(2)** al #19 la glossa va millorar («lligat») i el model va
escriure l'**oposat** («és diferent de»): una glossa correcta no impedeix una lectura
invertida. Dels 8 falsos que queden, les causes ja no són del glossador: al #9 `islman` =
«peix» està glossat bé dues vegades i el model escriu igualment una generalitat plausible;
quatre són cadenes de l'ASR irrecuperables; una és `amzaray` («diferència») enganxada per
l'ASR.

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

**H8 · A l'ASR, el que diuen dos lectors independents és bo; el que en diu un sol, no.**
*Mesurat contra veritat humana (29 versos, 14-11):* paraules que diuen **tots dos** models
(shi i zgh): **7 de 8 són a la veritat (88 %)**; paraules que només diu el nostre: **24 de 90
(27 %)**. La predicció es confirma amb força. Però l'acord només cobreix **7 de 161 paraules
de la veritat (4 %)**: amb el zgh de company, la precisió és alta i el rendiment és nul. *Segona prova (14-11): el mateix model sobre tres talls desplaçats (−0,3 s / 0 / +0,3 s),
mateixos 29 versos, veritat humana:*

| la paraula surt a | paraules | bones | precisió | cobreix la veritat |
|---|---|---|---|---|
| 3 lectures | 34 | 14 | **41 %** | 9 % |
| 2 lectures | 38 | 13 | 34 % | 8 % |
| 1 lectura | 93 | 7 | 8 % | 4 % |

**Veredicte:** l'acord és un senyal de debò (41 % contra 8 % a les que només surten una
vegada), però **el mateix model repeteix els seus errors a finestres diferents**: la precisió
de l'acord cau del 88 % (dos models) al 41 % (un model, tres talls), i la cobertura no passa
del 9 %. Els talls desplaçats NO són el segon lector que cal. I l'únic segon model que tenim
(zgh) cobreix el 4 %. **Conseqüència:** els +40 punts de sostre que l'auditor situa a l'ASR
no s'alliberen votant amb el que tenim; demanen un lector millor —descodificació amb el lèxic
a dins (H3) o adaptació amb l'àudio del canal (H4). La millora (1) de l'auditor queda
condicionada a tenir aquell lector.

**H3 · Descodificar amb el lèxic a dins** (cerca en feix + llista de formes). Ataca el mur
del graó 2, i després d'H8 és **la via principal**: votar amb el que tenim no allibera els +40
punts. *Estat (14-11):* codi fet, **no desplegat**. Ruta nova `/transcribe_mms_lm` al Space
(`huggingface-asr-space/mms_shi.py`, `app.py`, `requirements.txt` amb `pyctcdecode==0.5.0`):
el mateix MMS + adaptador, descodificat en feix (64) amb **182.054 unigrams** en l'alfabet del
model (`tools/exporta_unigrams.py`: lèxic + taules a mà, c→š x→ḫ ɣ→ġ ɛ→ε ṛ→r); KenLM
opcional si algú deixa `lm_shi.arpa` al costat. La ruta greedy no es toca. *Predicció:* CER
més baix que el greedy (0,307) sobre els 29 versos cantats i sobre els contes narrats, i menys
mots que no són paraules. *Risc:* el feix prefereix paraules corrents i es menja les rares
(`timyuri`, `tinfas`): mesurar també el recall de les paraules de la veritat que NO són al
lèxic. *Bloqueig:* el desplegament del Space el fa l'amo (compte de HF).

**H4 · Adaptar l'ASR amb l'àudio del canal sense text** (preentrenament autosupervisat sobre
les 440 peces del mateix parlant). *Estat:* catàleg del canal en marxa; demana GPU i decisió
de llicència.

**H6 · El coll d'ampolla després de la taula és la segmentació de l'ASR i el vocabulari del
camp.** Surt dels 8 falsos que queden: 4 cadenes irrecuperables, 1 paraula del diccionari
destruïda per enganxament de mots curts (`ayingratsnt` → `amzaray` perdut), 2 per geminació
o per nom absent del diccionari (`timyuri`, `tinfas`), i 1 (#9) on el model ignora una glossa
bona dues vegades. *Predicció:* comptant els trossos amb una paraula del diccionari
destruïda per enganxament (de qualsevol llargada, no només >12 lletres), la xifra serà molt
més alta que l'1,7 % de la vara vella. *Mesura prevista:* sobre tot el corpus, mots
desconeguts que es parteixen en 2–3 trossos de ≥3 lletres tots al diccionari (la lògica de
`parteix()`), amb mostra jutjada a mà. *Mesurat (auditor, 14-11), amb control de fals positiu (lletres remenades, llavor 1114):*

| vara | tokens | trossos | control remenat | lectura |
|---|---|---|---|---|
| estricta: paraula del diccionari ≥5 lletres + només peces de la classe tancada | 160 (2,1 %) | **146 de 1.088 (13,4 %)** | 1,2 % contra 4,8 % real (4:1) | **mínim segur** |
| ampla: qualsevol partició taula/diccionari amb paraula plena ≥4 | 674 (8,7 %) | 459 (42,2 %) | 7,6 % contra 15,0 % | infla gairebé el doble |

**Interval honest: del 13 % al ~25 % dels trossos** tenen una paraula del diccionari destruïda
per una partícula o un clític d'una o dues lletres pegat al costat: `mnnawn` = `mnnaw`+`n`
(13), `tawins` = `tawin`+`s` (6), `sawalf`, `tutlaytf`, `imdukald`, `taguriaġ`. Fan 6–8
lletres; de tota la llista estricta només una arriba a 12. **La vara de «>12 lletres» (1,7 %)
era correcta i parlava d'un altre fenomen.** Regla que en surt, i que val per a les tres vares
d'avui (diccionari-reconeix, partidor ample, partidor estricte): **cap mesura basada a
reconèixer mots no vol dir res sense el seu terra de lletres remenades al costat** — les tres
en tenien un (~40 % per a «el diccionari reconeix») i les tres l'havien amagat.

**On és el sostre (auditor, 14-11).** Dels 31 trossos no-bons de la mostra, què els limita de
debò: **~16 l'ASR** (cadena irrecuperable per cap diccionari), **~9 el lèxic i la
segmentació** (glosses perfectes ho arreglarien), **~6 el model** (tenia l'evidència i no la
va fer servir, o canvia de veredicte sol). Amb glosses perfectes i format de frase, el sostre
és **~18 de 40 (45 %)**. El glossador té ~9 trossos de marge (+22 punts); **l'ASR en té ~16
(+40 punts)**. Conseqüència: la feina de diccionari que queda val la meitat que al matí, i la
millora amb més sostre **ja no és de llengua sinó de senyal** —llegir el tall més d'una vegada
i quedar-se el que coincideix (→ H2, H8).

**H7 · El model prefereix una frase plausible a l'evidència.** #9: `islman` = «peix» glossat
bé dues vegades i escriu «les paraules amazigues són poques»; #19: glossa correcta («lligat»)
i escriu l'oposat. *Implicació:* cap millora de lèxic no ho arregla; cal canviar **què se li
demana** (no una frase: una relació, una llista de termes, un resum amb el que no sap marcat).
*La forma proposada (auditor):* #9 és possible perquè el model **pot ometre un token**; #19
perquè **pot escriure una relació**. Treure-li els dos permisos: **(1) `interlineal`** — una
llista tan llarga com els tokens de `hi_sent`, en el mateix ordre, amb la paraula catalana de
cada token o `?`; comprovable en codi (`len == tokens` o es rebutja), no pot ometre ni
inventar, i ensenya ON es trenca el tros. **(2) `marc`** — el tros descrit, no traduït: `tema`
(un grup nominal, mai una oració), `mena` (afirmació / pregunta / ordre / citació),
`polaritat` (afirmatiu / negatiu / restrictiu), `qui_hi_surt` (només persones que una forma
verbal o un pronom sostinguin). **(3) `cita`** — la paraula amaziga que el parlant anomena, copiada d'un token i sense
traduir (49 trossos; el #30 la destrueix sempre: «al sud diuen *imikk*» → «al sud en diuen una
mica»). I **`soste`**, que lliga cada paraula plena del tema i de la frase als tokens d'on
surt; el que no té token es poda abans de desar-se. *Decisió de l'amo (14-11): les dues
coses* — els fets com a producte principal i la frase a part, passant el mateix filtre.
*Estat:* implementat a `backend/fets.py` (comprovació en codi, 10 proves) i
`tools/escolta_llista.fets()`; **mesura pendent** sobre la mostra fixa de 40, jutjada a
cegues.

**H5 · El canal té subtítols humans en alguns vídeos.** *Catàleg complet (14-11): 440
vídeos, 45,0 h, 0 errors, cap llicència declarada.* **Confirmada i més gran del que semblava:
56 vídeos amb subtítols humans de debò** (67 comptant `live_chat`, que no és subtítol), 262
minuts: 42 amb àrab, 42 amb anglès, 1 francès. Per mena: 10 cançons, **~30 contes i sèries**
(The Rivals 1–7, The Traveller 1–7, The Last Warrior 1–4, Red Rock, Shepherd Boy, Werewolf,
Goat and Ogre, Hedgehog and Wolf, Wolf and Stork…), 2 introduccions a la llengua, 2 lliçons
d'alfabet, 4 documentals traduïts. **Cap de les 31 classes** (les que escoltem) no en té.
Pistes amb l'amazic escrit a mà, comprovades obrint-les: 3 `la` (tifinag), **5 `ak-*` que són
amazic en tifinag** (The Traveller 1–5), **2 `la-*` que són amazic en llatí** (The Traveller
1–2: «turft tumẓ aɣaṛas nns g wabuḍ n ill»), 1 `ti` (tifinag). `ar-454…` és àrab (darija) de
les lliçons d'alfabet. **Total: ~9 vídeos amb l'amazic transcrit a mà, uns 20 minuts — i els
de The Traveller són NARRATS, no cantats**: la primera veritat de referència en amazic
estàndard parlat, molt més a prop de la veu del professor que les cançons. *Catàleg desat a*
`Veus-tachelhit/_escoltats/veritat/cataleg_canal_complet.jsonl`. Detall de la primera passada
(184 vídeos): 11 vídeos amb àrab i anglès humans —10 cançons i 1 conte—, 27 minuts. I dos
d'ells (`X7_kAT8_J64`, `o21uxEQoczE`) duen una pista `la` que és **l'amazic transcrit en
tifinag a mà, amb temps**: «ⴰⵎⵖⴰⵔ ⵏⵏⵖ ⵉⵣⵡⴰⵔ» ↔ «Our leader moved forward». Això és àudio ↔
text amazic ↔ traducció, els tres humans i alineats: la primera **vara de veritat** que tenim
per a l'ASR en amazic estàndard, i parelles de traducció de debò. Cantat, no parlat: mesura la
llengua, no la veu del professor. Fitxers a `scratchpad/canal/subs_humans/`.

## Com es mesura a partir d'ara (auditor, 14-11)

La casella «bo» d'una passada sola de 40 trossos té una desviació de **±1,6 trossos = ±4
punts**, gairebé tota de temperatura del model (0,2). Amb n=40 i una passada només un canvi
de +15 punts era fiable: «bo 9→10» no volia dir res; «fals 15→8» (−22 punts) era
inconfusible. **Disseny:** **aparellat sempre** (mateixa llavor,
mateixos trossos: canviar-los afegeix ±6,7 punts de soroll de mostra a n=40); **jutjat a
cegues** amb les dues columnes barrejades i **20 trossos duplicats plantats** per mesurar
l'acord del jutge amb ell mateix —si baixa de ~90 %, cap número de la taula no val. El SHA
del codi va dins de cada JSON de sortida (fet al 14-11), perquè la línia de base dels 40 no
es va poder reconstruir. **La mostra fixa** (`mostra40.json`, llavor 1114), les tres
passades jutjades (`repassa40.json`, `repassa40b.json`, `control40.json`) i els guions de
mesura de l'auditor (`estricta.py`, `enganxades_curtes.py`, `quanta_mostra.py`, `audita*.py`)
són a `C:\Users\josep\Veus-tachelhit\_escoltats\veritat\auditoria-2026-11-14\`. Tota mesura
nova es fa sobre aquella mostra o sobre una de n=100 que la contingui.

**Correcció (auditor, 14-11, tarda): `temperature=0` NO fa la canonada reproduïble.** Dues
execucions a t=0, mateix prompt, mateixes glosses: `frase_t0` difereix en **21 de 40**
trossos. La recomanació «amb t=0, n=100 i k=1 n'hi ha prou» queda retirada: **n=100 i k=2 com
a mínim, tant a t=0 com a t=0,2**. I «zero de soroll a la casella dels falsos» era una
sobreafirmació treta de dues mostres: dues passades de la mateixa columna donen 13 i 10
falsos → **±3 per casella**. Els salts 15→8 (còpula) i 15→2 (format de fets) segueixen fora
d'aquest soroll. El jutge, en canvi, és estable: 20/20 als duplicats i 79/79 a les frases
repetides entre fulls.

## El format de fets, mesurat a cegues (14-11, mostra de 40, glosses VELLES)

| | bo | a mitges | fals | s'absté |
|---|---|---|---|---|
| frase vella (t=0,2) | 9 | 16 | **15** | 0 |
| frase nova (t=0) | 8 | 20 | 10 | 2 |
| **frase filtrada pels fets (v2)** | **4** | **9** | **2** | **25** |

**Perd 5 frases bones i se'n treu 13 de falses: de 15 falses a 2** (i les dues són els #9 i
#16 de sempre). Interlineal: 191 de 318 caselles plenes (60 %), **8 falses (4,5 %) i 6 de les
8 són paraules que la taula de la còpula ja arregla** (aquest run portava les glosses velles).
Marc: tot el que el model va omplir era cert (tema 13/13, mena 11/11, polaritat 8/8, qui
9/9) i n'omplia un terç. El #9 porta `islman → peix` a la interlineal, que la frase ometia a
totes dues temperatures: **el mecanisme funciona on havia de funcionar.**

El que la mesura va manar canviar abans d'escalar als 1.468 trossos (fet el 14-11, v3):
**(a)** el suport es comprova contra la interlineal, no contra un `soste` a part — de 7 podes,
6 treien coses certes que el model tenia a la seva pròpia interlineal, i `soste` només mirat
en rang deixava passar la frase falsa del #17 apuntant tot al token 0; **(b)** `mena`,
`polaritat` i `qui_hi_surt` **es calculen en codi** de les partícules i dels afixos, no es
demanen (el model n'omplia un terç i `ur` surt 104 vegades al corpus); **(c)** la `cita` només
d'entre candidats que el codi assenyala (token darrere d'un verb de dir), marcada «X» a la
interlineal i mai un token que designi gent — el #9 havia pres `imaziġn` («els amazics»,
subjecte de «diuen») per la paraula anomenada i la citació falsa li havia entrat a la frase
amb cometes; **(d)** una paraula que ÉS un token es sosté sola (el #30 perdia la frase per
«imikk sense token»); **(e)** la llargada no eximeix de token («gos», «pou» passaven).

*v3 (14-11, glosses d'avui):* 40 acceptats, tema 22, cita 2, interlineal 189/318 — i **frase
0 de 40, perquè el model no en va escriure cap**: amb «si dubtes, null» més «només amb paraules
de la interlineal» s'absté sempre, i el producte «la frase a part» que l'amo va demanar queda
buit. *v4:* redacció de la v2 per a la frase (escriu-la quan les caselles donin) amb el filtre
nou contra la interlineal. La comparació que decideix: v2 (filtre `soste`: 15 passen, 2
falses) contra v4 (filtre contra la interlineal). Si la v4 té menys falsos amb cobertura
semblant, el filtre nou guanya; si en té més, torna el «si dubtes, null». *v4 (capçalera):*
40 acceptats, tema 22, cita 2 (el #30 porta `imikk`), **frase 21 escrites / 6 podades / 15
passen**, interlineal 198/318 (62 %). Judici a cegues pendent. Observat: algunes frases
copien el «?» de la casella («no ? només ?») —el forat és visible en comptes d'inventat—, i
el #19 torna a relacionar amb «és»: la frase és l'únic camp on el model pot relacionar, i és
el preu de tenir-la.

*Judici de la v3 (auditor, a cegues, acord 20/20):* interlineal **189 caselles, 2 falses
(1,1 %)** i les 6 de la còpula fora (`ġar→només`, `dad→?`, `maša→però`, `inna→va dir`); cita
**2 de 2** (`imikk`, i `manik` = «els qui diuen *manik*», la citació dialectal del vídeo);
tema 21 de 22 cert però **9 dels 22 no són grups nominals**; `mena` 12/12, `polaritat` 9/9
(«restrictiu» ja s'usa); `qui_hi_surt` 16 amb **4 falsos**, tots del mateix bug (la `-ġ`
final llegida com a 1sg quan és de l'arrel, `iffġ`, o un possessiu, `nnġ`). I **8 caselles
eren el token copiat tal qual** (el #10, cinc de cinc) i comptaven com a plenes: el compte
honest era 181. Quatre pedaços fets a la **v5** (PR #606): suport per arrel, token copiat → «?»
i cometes només per a un candidat a cita, `-ġ` només amb verb conegut i prefix que mana,
tema sense «?» ni infinitiu. *Judici de la v4 (auditor, a cegues, mateix full):* **la comparació que decidia, v2 (filtre
`soste`) contra v4 (filtre contra la interlineal), 15 frases contra 15: 4/9/2 → 6/8/1.** El
filtre nou guanya per totes dues bandes i el «si dubtes, null» no torna. Les invencions de la
v2 han desaparegut una per una (#24 «la mare», #29 «són una llengua», #9 «imaziġn»). L'únic
fals (#26) i l'única predicació inventada (#19) tenien una còpula a la frase sense cap casella
de còpula; el #3, bo, la tenia (`tgi→no és`) → **regla de la còpula**, que deixa la columna a 0
falsos de 14. El «?» dins la frase: 5 de 15 el porten, 1 bo / 4 a mitges / 0 falses — **el
model posa el forat on abans posava la invenció**; no compta en contra i es marca [?]. De les
11 podes de la v4, 10 eren flexió («pregunta»/`pregunto`, «verbs»/`verb`): la comparació per
arrel les recupera. Tot això és a la **v6** (PR #606). *v6 (capçalera, codi 3479dd9):* frase **18 escrites, 2
podades, 16 passen** (5 amb [?]); tema 22; cita 2; interlineal 187/318 amb el compte honest;
`qui_hi_surt` omplert en 18; **6 podes en total (la v4 en tenia 11)**. Judici de la v6 pendent;
és el que decideix si s'escala als 1.468 trossos. Límit conegut que no s'arregla: un tema pot dur un
genitiu fals («traducció de fons», #37); prohibir-los mataria «la conjugació dels verbs».

## Les tres millores, per ordre de sostre (auditor, 14-11)

1. **Llegir cada tall dues o tres vegades i quedar-se el que coincideix.** On hi ha +40
   punts: ~16 dels 31 no-bons són ASR irrecuperable. Evidència: els mateixos 58 talls, el
   mateix model, el mateix fitxer, i el text canvia en 46 de 58 (79 %) amb taxa agregada
   idèntica. Mesura: reconeixement de les paraules acordades contra les discrepants; val si
   ~85 % contra ~45 %. Risc: triple de crides, i quedar-se només les paraules fàcils. → H8.
2. **Canviar què se li demana al model**: `interlineal` (una paraula o `?` per token, en
   ordre, comprovat en codi), `marc` (tema com a grup nominal, mena, polaritat, qui hi
   surt; cap camp admet relacions, per això cap no es pot invertir), `cita` (la paraula
   amaziga citada, sense traduir: 49 trossos, el producte més valuós d'aquests vídeos), i
   `sosté` lligant cada paraula plena al seu token. Avui: 394 frases, ~89 bones. Amb això:
   ~250 marcs certs, ~49 cites, **cap frase llegible de corregut**. La pèrdua és real i
   **s'ha de voler abans de fer-ho**: decisió de l'amo. → H7.
3. **El lèxic del camp i dos bugs**: ~40 entrades del metallenguatge (`iḍris`, `tilawin`,
   `tinfas`, `tafransist`, `tayunanit`…); l'encert superficial del diccionari talla les
   regles (`wawal` → «run down» i mai `w`+`awal`); el guard de `MIN_ARREL` feia impartibles
   `das`, `at`, `dak`, `dag` (fet al 14-11: la resta curta val si és a la taula a mà); i una
   porta de varietat: els 3 vídeos amb certesa ASR mediana < 0,87 rendeixen 6,9 % de català
   contra 38,3 % dels altres 20. Risc: un lèxic a mà que endevina, i un llindar tret de 23
   vídeos. Marge: ~9 trossos de 40.

**El que ja no val la pena:** res més al prompt del traductor amb el format de frase. El seu
sostre, amb el verb servit i glosses perfectes, és ~18 de 40.

## El que està malament de la feina feta (auditor, 14-11; es manté com a llista de deute)

- La canonada no era reproduïble (temperatura 0,2) i la línia de base no es podia
  reconstruir (sense SHA al JSON): tots dos arreglats el 14-11.
- La vara del diccionari té un terra de fals positiu del ~40 %: remenant les lletres encara
  «reconeix» el 39,5 %. «El 60 % de les paraules existeixen» no vol dir «són correctes».
- «shi 62,9 % · zgh 57,0 %» no reprodueix (avui 70,1 % · 59,4 %); la conclusió aguanta.
- `segur` no s'ha produït mai (0 de 394) i tres documents parlaven de l'escala com si en
  tingués dos nivells. 283 violacions de la regla dura del prompt (text amb «no s'entén»)
  tapades pel filtre `amb_ca`.
- La premissa fundacional és massa forta: en 6 dels 9 encerts originals el català era
  correcte **contra** la glossa. El títol àrab compra fluïdesa i paga amb veritat (#1).
- El tall pels silencis està mesurat per a la certesa de l'ASR, no per a la sintaxi: 226 de
  1.088 trossos fan <2 s; 74 toquen el màxim de 9 s.
- El judici de l'auditor no va ser cec i el seu acord amb ell mateix no està mesurat.
- `šku`, `ga`, `lan` són trossos de l'ASR, no paraules: feina d'un normalitzador, no de la
  taula. `wawal`, `tlawin`: bug de la passa 1 (pendent). `amawal` («vocabulari»): lèxic del
  camp (pendent).

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
