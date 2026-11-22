# Auditoria dels documents de recerca (21-11-2026)

Issue #722. S'han mirat els **40 documents de `docs/recerca/`** que no són el quadern: tot
`docs/recerca/*.md` a `origin/main` al commit `6ca46a2`. La vara de mesurar és
`docs/recerca/DESXIFRAT.md` **amb les seves correccions** (§28 corregida a la §37, §31 corregida
a la §38), `docs/recerca/METODE.md`, el codi del repositori i els serveis en viu.

La feina no era resumir els documents: era trobar **afirmacions que ja sabem falses i que allà
encara es donen per bones**. Cada troballa diu quin fitxer, quina línia, què hi diu, què és cert
i **com ho sé**. Quan no ho he pogut comprovar, ho diu.

**Resultat:** 7 falses, 8 velles que no enganyen, 12 números comprovats que casen, i **cap pregunta
oberta**. Les set falses porten un avís al seu lloc, sense esborrar l'error: **dotze avisos en nou
documents**, perquè tres de les troballes viuen en més d'un fitxer.

Les tres preguntes que vaig deixar obertes perquè no les podia comprovar des d'aquí s'han tancat
totes: dues amb mesures que no estaven al meu abast —i **la primera era una contaminació de debò**,
la taula estàndard ↔ dialecte amb un 36,4 % de línies del Rif (quadern §44), que val més que la
major part del que he trobat jo— i **la tercera va resultar falsa, amb la prova dins del repositori**
(troballa 7). Aquella la podia haver tancada jo: la vaig deixar oberta dues vegades per haver
suposat que calia llegir producció, quan n'hi havia prou amb `git show` del commit que la va
escriure. La lliçó és que «no ho he pogut comprovar» s'ha de guanyar buscant.

Una cosa que val la pena dir primer, perquè era la sospita principal: **cap dels 40 documents
repeteix les «quatre proves amb veritat humana» ni el −0,044 del model de llengua.** Les dues
afirmacions falses viuen només al quadern, i allà ja estan corregides. El que sí que s'ha trobat
és la **mateixa família d'error en un altre lloc** (troballa 1).

---

## Falses

### 1. El veredicte d'H3 està mesurat amb un model acústic que ja no serveix

| | |
|---|---|
| on | `tamazight-for-all.md:599-618`, `tamazight-for-all-h3-taula.md` (tot), `tamazight-for-all.md:860` |
| què diu | «**Veredicte: H3 és real i petita.** Set punts de WER i mig de CER», amb `CER −0,009 [−0,017, −0,001]` sobre els 226 versos de TFA, i la fila `corpus_bi α 0,15 β 1,0 (el desplegat)` → CER 0,198 / WER 0,640 |

**Què és cert.** Aquella mesura és correcta per al model que hi havia el 15-11 al vespre
(`adaptador_shi_ric.pt`, greedy a 0,207 de CER sobre TFA-226). **L'endemà al migdia el Space va
passar a servir H4b** (`adaptador_shi_zouhir_b`), que per si sol baixa TFA-226 de 0,187 a 0,169.
El quadern §38 torna a descodificar les proves amb el model que serveix ara, sobre els logits
guardats, i el guany del model de llengua a TFA-226 **desapareix**:

| prova | n | greedy | amb LM (α 0,15) | |
|---|---|---|---|---|
| tfa-226 | 226 | 0,1688 | 0,1674 | **−0,0014, no es pot dir** |
| cv-zgh-test | 256 | 0,1463 | 0,1264 | −0,0199 [−0,0274, −0,0125] millora |
| test-fora | 101 | 0,2740 | 0,2669 | −0,0071, no es pot dir |
| zouhir-tests | 121 | 0,2002 | 0,2074 | +0,0072, va a l'altre costat |

**Com ho sé.** El greedy de la §38 a tfa-226 és **0,1688**, que és el 0,169 d'H4b
(`zouhir-amazigh.md:174` i `tamazight-for-all.md:904`), no el 0,207 d'H3: la §38 està mesurada
amb l'adaptador d'ara. I el quadern conclou que **per la nostra pròpia regla no s'adopta**
(millora una prova, no dues).

**Per què enganya.** Qui llegeixi el document conclourà que posar el lèxic al feix és un guany
mesurat sobre la nostra prova de referència. Amb el model acústic que servim avui no és
detectable; només ajuda a Common Voice, que és parla llegida. El quadern §38 ho diu amb les
seves paraules: «em desdic del que vaig dir el 20 a la nit: vaig vendre això com l'únic guany
gros a l'abast. No ho és.»

**Nota a part:** `tamazight-for-all-h3-taula.md` és **dues taules sense cap línia de capçalera**
— ni data, ni quin model, ni quin test. Un fitxer així no es pot citar sense obrir-ne un altre.

### 2. La porta d'adopció del transcriptor es mesura contra un model que ja no serveix

| | |
|---|---|
| on | `tamazight-tv-fabrica-especificacio.md:176-181` (§6.5) i `tamazight-tv-pla.md:46` (fase 6) |
| què diu | «Mesura: test net CV zgh (256 talls; **referència 0,1537**)… Decisió: adoptar si CV zgh millora amb IC»; i «Porta: millorar el **0,1537 actual** sense empitjorar test-fora» |

**Què és cert.** 0,1537 és la xifra del **29-10** per a l'adaptador d'aleshores. Des del **16-11
al migdia** el Space serveix H4b, que sobre **el mateix test de 256 clips** fa **0,140**
(`zouhir-amazigh.md:173`: 0,146 → 0,140, −0,006 [−0,012, −0,001]); el quadern §38 en dona el
greedy a **0,1463** i la §28 a 0,1440/0,1433. Tots dos documents són del **17-11**, l'endemà del
desplegament.

**Com ho sé.** `zouhir-amazigh.md:173` i quadern §28/§38 per als números; `curl` a
`/health` del Space ASR (avui) retorna
`facebook/mms-1b-all+adaptador_shi_zouhir_b(... H4b 16-11-2026)`, o sigui que el que serveix és
H4b i no l'adaptador de 0,1537.

**Per què enganya.** Llegida tal com està, és una **porta d'adopció** que es pot passar sent
pitjor que el que ja servim: un transcriptor nou a 0,15 «milloraria la referència». I hi ha un
segon problema que la fa inaplicable: **no diu amb quina escala de puntuació** és el 0,1537, i el
projecte sap que les escales difereixen — `tamazight-for-all.md:893` ho diu per a TFA: «l'escala
ric del nucli no és la de `h3_puntua` (0,187 aquí és el 0,207 d'allà)». 0,1537 i 0,146 poden ser
el mateix model en dues escales; sense dir-ho, no es pot aplicar.

**El que NO és, i és la diferència entre arreglar un document i parar una màquina: el 0,1537
només és a la documentació. La regla que corre és correcta.** `tools/lm/cercle_virtuos.py` **no
fa servir cap llindar absolut**: `regla_interna()` (`:123-137`) és purament comparativa contra
el model d'ara —s'adopta si **cap conjunt empitjora amb IC i almenys dos milloren amb IC**, i si
falta una prova no es jutja— i el capçal del fitxer (`:10-11`) diu en tantes paraules «REGLA
INTERNA (director)… **La regla de producció (§6.5) NO es toca**». Qui va escriure el codi ja sabia
que §6.5 era una altra cosa i no la va fer servir.

**Com ho sé.** `grep -rn '1537' --include=*.py .` sobre tot el repositori: **cap coincidència**.
El número no és enlloc del codi, només als dos documents (i en aquest informe).

**Per tant la gravetat és aquesta:** no hi ha risc viu d'adoptar un model pitjor. El que està
malament és la **regla de producció escrita** de §6.5, que és la que es llegiria el dia que
s'adoptés un transcriptor a producció fora del bucle. S'arregla el document; no s'ha d'aturar res.

### 3. El tifinag cremat no es llegeix amb CER 0,29

| | |
|---|---|
| on | `tamazight-tv.md:63` |
| què diu | «**El tifinag cremat** es llegeix amb CER 0,29 al millor cas (aslmdtv): la línia àrab és la que dona el significat segur» |

**Què és cert.** Sobre aquest mateix material —els subtítols cremats de Tamazight TV— la mesura
oficial dona **CER 0,0009** sobre 100 línies no vistes, i 0,0019 sobre 50 línies amb els ids
congelats abans de mirar res (`ocr-tifinag-snrt.md:21-22`, repetit a
`tamazight-tv-sistema.md:110`). I per a aslmdtv, que és el que la frase cita entre parèntesis,
`ocr-tifinag-impres.md:109` estima «**≥ 99,5 % dels glifs**». Ni una lectura ni l'altra dona
0,29. El 0,29 és la xifra d'un **lector de veu** sobre rètols d'un altre canal, no d'un OCR
(memòria «la pista amaziga va sota un codi de llengua fals»).

**Com ho sé.** Els dos documents que mesuren. I la cronologia ho explica: `tamazight-tv.md` es va
desar a les **09:34** del 17-11 (`8b7f0c0`) i `ocr-tifinag-snrt.md` a les **15:59** del mateix
dia (`bf10d21`) — la frase es va escriure sis hores abans que hi hagués la mesura, i ningú no la
va tornar a tocar. El 0,29 no surt de cap altre document dels 40 (`grep`).

**Per què enganya.** No és només un número 300 vegades massa gran: **és el que sosté una
conclusió**. «La línia àrab és la que dona el significat segur; el tifinag és esborrany» era raonable
amb un 29 % d'error i no ho és amb un 0,09 %.

### 4. L'alineació forçada ja existeix, i és el guany més gros que tenim

| | |
|---|---|
| on | `tamazight-tv-sistema.md:129` |
| què diu | «El pas que ho resol és l'**alineació forçada**… s'ha de fer a Kaggle (GPU) i es jutja amb ≥50 marques d'en Pablo. **Fins que existeixi**, el transcriptor només rep el que passa la porta» |

**Què és cert.** El diagnòstic es va executar el **18-11** (#601) i els seus números són al
quadern §41: **358 de 589 talls (62 %) amb l'inici desplaçat més de 0,5 s**, desplaçaments de
−36 s a +119 s, i **CER 0,7370 amb els límits del subtítol contra 0,6581 retallant on el model
sent la veu: −0,0789**. Per comparar: una ronda del cercle val −0,003 a −0,013 i el model de
llengua al feix −0,0199 i només a Common Voice. **Retallar bé val sis vegades més que la millor
ronda**, i no demana dades noves.

**Com ho sé.** Quadern §41, que a més diu que el resultat «feia tres dies que hi era» i que
ningú no l'havia llegit.

**Per què enganya.** Aquest document es presenta a la primera línia com «document de referència
(llegeix-lo primer)». Tal com està, amaga la palanca més gran que hem mesurat: qui el llegeixi
creurà que l'alineació forçada és feina futura que demana GPU i 50 marques d'en Pablo.

### 5. `adaptador_shi_ric.pt` no és «el que serveix al Space»

| | |
|---|---|
| on | `zouhir-amazigh.md:64` |
| què diu | «El mateix lector de sempre (`mms-1b-all` + `adaptador_shi_ric.pt`, **el que serveix al Space**)» |

**Què és cert.** El que serveix és `adaptador_shi_zouhir_b` (H4b) des del **16-11 al migdia**.
`adaptador_shi_ric.pt` es queda al repositori només per poder tornar enrere.

**Com ho sé.** Dues coses, i la segona és d'avui:
1. **El mateix document ho desmenteix 83 línies més avall**, a `zouhir-amazigh.md:147-152`:
   «Desplegat el 16-11 al migdia… l'adaptador H4b puja al Space com `adaptador_shi_zouhir_b.pt`».
2. `curl https://josepabloucr-huggingface-asr-space.hf.space/health` (21-11) retorna
   `"mms":{"model":"facebook/mms-1b-all+adaptador_shi_zouhir_b(... H4b 16-11-2026)","ready":true}`.

**Per què enganya.** És una contradicció dins d'un sol document, i la frase falsa és la que va
primer. Qui s'aturi a la secció «Resultats sobre tot el corpus» se'n durà el model equivocat.

### 6. El filtre de varietat no pot dir «rif», i per això el corpus tenia tarifit

| | |
|---|---|
| on | `tamazight-tv-fabrica-especificacio.md:126-143` (§6.1), `tamazight-tv-pla.md:36` (fase 4) i `:57`, `tamazight-tv-peons.md:40-43` (Bloc C), `tamazight-tv-sistema.md:56-62` (§5) |
| què diu | que hi ha una mesura de varietat per capítol amb resultat a `{taixelhit, atles-central, atles-mitja, **rif**, mixt, desconeguda}`; que «**Només les sèries de l'Alt Atles central entren al train** de la varietat»; i que la fàbrica té una etapa `05_varietat.py` |

En Pablo ha decidit que el tarifit és una altra llengua i que no entra enlloc. Aquests documents
fan creure que ja hi ha un filtre que ho garanteix. **No n'hi ha.**

**Què és cert, i com ho sé** — tres comprovacions al codi i una al quadern:

1. **`05_varietat.py` no existeix.** `ls tools/snrt/fabrica/` dona `02_llegeix.py`, `03_talla.py`,
   `04_tradueix.py`, `05_informe.py`. L'etapa de varietat no s'ha construït mai; el que hi ha és
   una funció `varietat()` dins de `05_informe.py:111`.
2. **Aquesta funció no té cap referència del Rif.** `tools/snrt/fabrica/05_informe.py:118-122`
   defineix exactament tres grups: `"Aït Mraw / Beni Mellal"`, `"Souss"`, `"Atles Mitjà"`.
   Compara les 200 formes més freqüents del capítol contra aquests tres. **Un capítol rifeny no
   té contra què sortir alt: la mesura no pot retornar «rif» per construcció**, tot i que §6.1
   punt 5 posa «rif» a la llista de resultats possibles.
3. **El punt 4 de §6.1 —«escoltar», el que el document diu que «és la mesura que val»— no es
   fa.** `tools/snrt/fabrica/LLEGEIX-ME.md:87-89`: «només els punts 1–3…; el punt 4 (escoltar 30
   rèpliques amb l'ASR) **no es fa**. `varietat_capitol` queda “desconeguda”». O sigui que l'única
   mesura que corre és la que el propi document qualifica d'«orientativa».
4. **I ha fallat, amb el número.** Quadern §42: «**El classificador pel lèxic deia “tachelhit” als
   27 capítols**, sense cap excepció», mentre que **8 dels 27 són del Rif** (4 de 21 al train,
   2 de 2 al dev, 2 de 4 al test). Les dues raons que dona: el lèxic diferencial té **117
   marques tachelhit contra 39 tarifit**, i el subtítol està **normalitzat per l'IRCAM**, que és
   on les marques dialectals s'esborren. El senyal que sí que funciona no passa per cap dels dos
   filtres: **els topònims a l'àrab** (Tafersit ×26, Rif ×30, Nador, Driouch).

**Per què enganya.** `tamazight-tv-sistema.md` és el document de referència i la seva §5 («les
portes: què decideix si una cosa entra o no») **no esmenta la llengua ni la varietat enlloc**: ni
com a porta, ni com a cosa pendent. `tamazight-tv-peons.md` Bloc C envia un peó a aplicar «§6.1
i §6.2 sencers», que inclouen un punt 4 que no existeix. I la fase 4 del pla afirma un filtre
d'entrada al train que mai no s'ha aplicat. El cost ja és conegut: el dev del traductor era
**100 % rifeny**, i «el tarifit no inflava el número, però el dev hauria triat el model
equivocat» (§42).

### 7. «Cap d'aquestes conclusions no s'ha aplicat a producció» era fals el dia que es va escriure

| | |
|---|---|
| on | `2026-10-31-la-llengua.md:6` |
| què diu | «Cap d'aquestes conclusions no s'ha aplicat a producció. Les lliçons continuen com estaven.» |

Aquesta la vaig deixar oberta dues vegades perquè pensava que calia llegir producció per
tancar-la. **No calia: la prova és al mateix commit que va crear el document.**

**Què és cert.** `5eed55d` («recerca: el que hem après de la llengua, i cinc títols falsos fora
del curs (#530) (#531)», 31-10 08:43) toca tres fitxers: el document, `backend/tests/test_grammar.py`
i **`backend/grammar.py` (+19/−9)**, que és el que serveix els títols de les unitats del curs. Hi
canvia cinc títols i l'encàrrec al redactor, i són **exactament** les conclusions del document:

| abans | després |
|---|---|
| `«Ser», «estar» i «tenir»: iga, illa, ɣur-i, dar-i` | `ija/iga, illa, ghori/ɣur-i` |
| `El perfectiu: accions acabades (passat)` | **`El perfectiu: accions fetes i estats`** |
| `La negació: ur …, ur … ša / bu` | `La negació: ur i les paraules que l'acompanyen` |
| `Les preguntes: is, ma, mani, manik, mšta, maymi` | `is, mayd, mani, manimsh, mšta, makh` |
| `El relatiu i el participi: lli, ay-, verb en -n` | `El relatiu i la forma en -n: nna, ayda, verb en -n` |

I al `hint` del perfectiu, «a finished action» passa a «a finished action, **or a state that already
holds, so often but not always a past**» — que és la §4 del document, «el perfectiu no és “passat”»,
aplicada. Al text del redactor, «forma de passat / acció acabada» → «forma d'acció feta o d'estat».

**Com ho sé.** `git show --stat 5eed55d` i `git show 5eed55d -- backend/grammar.py`. I **el document
es contradiu a si mateix**: la línia 183 diu «El que sí que canvia amb aquesta PR: **cinc títols de
`backend/grammar.py`** que prometien coses falses, la pista del perfectiu per al classificador i
l'encàrrec al model, que deia “passat”». La línia 6 i la 183 no poden ser les dues.

**Què sí que és cert, i val la pena deixar-ho escrit:** la **resta** no s'ha aplicat. Des del 31-10
no s'ha tocat cap fitxer de curs (`git log --since=2026-10-31 -- backend/data/metode`: buit) ni
`grammar.py` un altre cop, i `LESSON_VERSION` no es va tocar, així que **cap lliçó no es va
reescriure**. La frase hauria estat certa dient «les lliçons», que és el que el commit va deixar
igual; dient «cap conjunt de conclusions», no.

**Per què enganya.** És la segona línia del document, abans de qualsevol resultat, i és la que
decideix si un lector es pensa que allò encara és una proposta o que ja corre. Mitja dotzena de
títols del curs porten aquestes conclusions des del 31-10.

---

## Velles, però que no enganyen

Aquestes no diuen res fals de qui les va escriure: han quedat enrere. Les deixo sense avís al
document (afegir-n'hi vuit més faria el text il·legible) i les llisto aquí perquè es puguin
refer quan algú hi torni a treballar.

1. **`tamazight-tv-sistema.md:68` i `tifinag-estandard-i-dialecte.md:28,62`: «31 capítols de
   “Tadfi n Tskla”».** Els comptes s'han mogut: el quadern §39 parla de **215 capítols** al
   catàleg i 26 fets, el §40 de 30 collits per YouTube contra 215 a la fàbrica de l'ECS, el §42
   de **27 collits**, i el §33 de 20 episodis. Cap d'aquests documents és citable per al volum
   d'avui.

2. **`ocr-arab-text-cremat.md:34`: «La nostra línia (font IRCAM + sintètic + CRNN, CER 0,050 en
   reals) ja supera tot el que hi ha publicat».** El 0,050 és el **punt de partida**, no el que
   tenim: `ocr-tifinag-snrt.md:36` diu «el punt de partida (el CRNN de línia entrenat només amb
   2.000 línies sintètiques) feia CER 0,050 sobre les 52 línies». El lector d'ara, que és un
   classificador de plantilles i no un CRNN, fa 0,0009–0,0051. La conclusió («supera tot el
   publicat») s'aguanta encara millor; el número subestima la nostra feina 50 vegades.

3. **`ocr-tifinag-snrt.md:61-62` i `:72`: la confusió ⵙ/ⵀ com a cosa oberta.** La secció «provat i
   descartat» explica que un desempat «mirant on es diferencien» va **empitjorar** el CER de
   0,0234 a 0,0458, i «el que no se sap» hi deixa ⵙ/ⵀ. Es va resoldre amb un desempat
   **diferent**: no per forma sinó per **topologia** (trossos de tinta, forats i com estan
   posats). El quadern §3 i §9 el mesuren a **+5,29 punts de grau A** i `tskla` passa de 3/9 bé a
   9/9. Ja és al repositori: `tools/snrt/fabrica/tifinag_plantilles.py:122-193` (`topologia()`,
   `#699`), fusionat a `origin/main` amb `e16e7e8`. El document no és fals —era un altre
   desempat— però deixa un lector amb la impressió que les lletres-cercle no se saben separar.

4. **`models-de-text.md:320-321`: «cal que `HUGGINGFACE_TRANSLATION_SPACE_URL` a Render apunti a
   aquest Space (ara apunta al de Tamazight-NLP, que és el model base)».** Ja no cal: el codi
   mateix hi apunta per defecte. `backend/main.py:166`:
   `HF_TRANSLATION_SPACE_DEFAULT = "https://huggingface.co/spaces/josepabloucr/Finetuned-Quantized-NLLB"`.

5. **`tifinag-estandard-i-dialecte.md:108-109`: «Aquesta hipòtesi **no està provada**: és una
   proposta».** La H-E2 (que la diferència entre el que es diu i el que s'escriu té estructura) ja
   està mesurada: quadern §2, **181 correspondències** que surten en dos capítols o més, de 26
   capítols i 15.745 talls, i «**el 61 % difereixen en una sola lletra**, que és el que deia la
   hipòtesi H-E2 d'en Pablo». La condició (b) del document —que un parlant de referència confirmi
   20 correspondències— segueix pendent, així que el document és **prudent**, no fals.

6. **`tamazight-tv-peons.md:8-9`: el preàmbul envia tots els peons a
   `...worktrees\mirar`, branca `feat/ecs` = `origin/main`.** Aquell worktree és ara a
   `feat/snrt-visor-privat` (`git worktree list`) i `feat/ecs` no existeix. Un peó que segueixi el
   preàmbul al peu de la lletra treballarà on no toca.

7. **`tamazight-for-all.md:263`: «*Estat (14-11):* codi fet, **no desplegat**».** Està datat i el
   mateix document ho corregeix a `:745` («Desplegat el 15-11»). Hi afegeixo el que el quadern §32
   hi posa al damunt: `arpa_lm.py`, **la peça que fa entrar el lèxic al feix**, vivia només al
   dataset de Kaggle, de manera que l'experiment H3 **no es podia repetir des del repositori**
   fins al 21-11. Qui hagués volgut reproduir la taula d'H3 abans d'ahir hauria mesurat un feix
   que ignorava el lèxic del tot.

8. **`ocr-tifinag-impres.md` i `informe-2026-11-16.md:36`: la varietat d'aslmdtv.** El document de
   l'OCR ho diu bé (`:116`: «El conte està escrit més aviat en **tamazight de l'Atles central**
   que en tachelhit… Val la pena saber-ho abans d'incorporar-ne el lèxic a l'app»), però l'informe
   que el resumeix en diu només «aslmdtv llegit del tot (1.034 files de tifinag imprès, 95,5 % a
   ull)», sense la varietat. Amb la regla nova sobre la llengua del material, el resum perd
   justament el que calia saber.

---

## Números comprovats que casen

Un informe que només acusa no és un informe. Això és el que he anat a comprovar i **casa**:

| què | on ho diu | contra què l'he comprovat |
|---|---|---|
| Cap de les «quatre proves amb veritat humana» presentades com a independents | — | `grep -niE 'quatre proves\|4 proves'` als 40: **cap coincidència** |
| El −0,044 del model de llengua donat com a guany real | — | `grep -E '0[,.]044'` als 40: tres coincidències, i **cap** és això (un IC a `models-de-text.md:381`, un CER d'OCR a `ocr-tifinag-snrt.md:57` i una columna de frontera a `-h10-taula.md:15`) |
| H4b: TFA-226 0,187 → 0,169; Zouhir fora 0,268 → 0,200 | `tamazight-for-all.md:904-905`, `zouhir-amazigh.md:174` | `informe-2026-11-16.md:8-10`, memòria «H4: la primera millora amb veritat humana» |
| El Space ASR serveix H4b i té la ruta del lèxic al feix viva | `tamazight-for-all.md:745-748`, `zouhir-amazigh.md:147-152` | `/health` en viu (21-11): `adaptador_shi_zouhir_b`, rutes `/transcribe /align /transcribe_mms /transcribe_mms_lm`, `unigrams: 182081`, `kenlm: true` |
| «182.081 formes» al lèxic del feix | `tamazight-for-all.md:748` | `/health` en viu: `"unigrams":182081`, exacte |
| Traductor v3 al Space, chrF 0,62 sobre les 60 | `tamazight-tv-sistema.md:113` | `models-de-text.md:361-362` (0,623 en viu), memòria «el traductor d'amazic» (0,623); el Space respon HTTP 200 avui |
| La taula crua d'H3 (greedy 0,207/0,712 → `corpus_bi` 0,198/0,640) | `tamazight-for-all-h3-taula.md`, `tamazight-for-all.md:602-607`, `:856-862` | quadern §29, que cita exactament aquests números com els bons («−0,009 de CER, no −0,044») |
| CoTaSS: CER 0,80 en conversa espontània | `veritat-humana-cerca.md:48` | `informe-2026-11-16.md:13` |
| 531 canals mirats, cap pista humana amaziga nova | `veritat-humana-cerca.md:5-11` | `informe-2026-11-16.md:46`, memòria «YouTube no té més veritat humana amaziga» |
| L'escala del traductor: 0,424 → 0,521 → 0,571 → 0,602 | `informe-2026-11-16.md:18-23` | `models-de-text.md` (H-MT1 i Gemini), fila per fila |
| OCR àrab de la SNRT: CER 0,0074 i 0,0059 | `tamazight-tv-sistema.md:111` | memòria «lector d'àrab SNRT: l'ajust fi amb línies reals» (0,007) |
| 269 vídeos minats en dàrija; 58 amb subtítols humans | `tamazight-for-all-llibre-de-registre.md:7`, `-cataleg-unic.md:8` | `tamazight-for-all-darija-vs-lexic.md:3` (269) i `-cataleg-unic.md:8` (58): els tres documents casen entre ells |

I una nota de qualitat, no de veritat: `2026-10-31-la-llengua.md` és el document **millor fet** dels
40. Marca cada afirmació com a **atestat / inferit / sense verificar**, posa els límits abans dels
resultats («ningú no ha escoltat cap àudio»), i té una taula pròpia de «coses que vam creure i que
les auditories van tombar». Que la troballa 7 sigui seva no ho desmenteix: l'error és a la línia 6,
i la prova per enxampar-lo és **a la línia 183 del mateix document**, que diu què va canviar a
`grammar.py`. Un document que es contradiu així es pot auditar; un que no diu res, no.

---

## El que vaig deixar obert, i com s'ha tancat

Les tres les vaig deixar com a preguntes perquè em semblava que no les podia comprovar des d'aquí.
**Totes tres estan tancades.** Les dues primeres les ha tancades qui porta el quadern, amb mesures
que no estaven al meu abast, i **la primera era una contaminació de debò**: val més que la major
part del que he trobat jo. La tercera **va resultar falsa i la podia haver tancada jo** — vegeu-ho
al final.

1. **Si la taula estàndard ↔ dialecte està contaminada de tarifit: SÍ.** El fitxer no era a
   `Veus-tachelhit\` sinó a `E:\tamazight\_magatzem\`, i per això no el vaig trobar. Mesurat: les
   **74.761 parelles vénen de 25 capítols i 11 són del Rif — el 36,4 %**. De les 181
   correspondències, **26 vénen només del Rif** i 6 més en són majoria; 109 són netes. I no és
   soroll qualsevol: `awal→awar`, `wawal→wawar`, `izlan→izran` són la **l→r rifenya**, que és
   justament la marca que fem servir per detectar el tarifit, i `mad→min` és l'interrogatiu
   rifeny — o sigui que la taula ensenyava com a «estandardització» el senyal que serveix per
   separar les dues llengües. Taula neta a `estandard_dialecte_net.jsonl`, 149 correspondències.
   Escrit al quadern com a **§44**, amb l'avís a la §2.
2. **La incoherència de la §42: eren dos conjunts mal explicats, no tres comptes del mateix.** Són
   **8** capítols del Rif a la collita nova, no sis; els **sis** de puntuació lèxica més baixa són
   tots del Rif (i els cinc de sota també), que és el que la frase volia dir. I els **11** tarifit
   de producció són **uns altres capítols** —els vells de Tadfi, amb slugs de 40 lletres—, amb
   **solapament zero** amb els 8. Corregit al quadern.
3. **`2026-10-31-la-llengua.md:6`: «Cap d'aquestes conclusions no s'ha aplicat a producció»: és
   FALSA**, i ha passat a ser la **troballa 7** de la primera llista. No calia llegir producció: el
   commit que va crear el document, `5eed55d`, també canvia `backend/grammar.py` amb cinc títols
   d'unitat i l'encàrrec al redactor, que són les conclusions de la §4 i la §9. La vaig deixar
   oberta **dues vegades** per haver suposat que la comprovació era fora del meu abast, quan n'hi
   havia prou amb un `git show`. Les dues suposicions del mateix tipus —aquesta i la del fitxer que
   era a `E:\tamazight\_magatzem\` i no a `Veus-tachelhit\`— són l'error d'ofici d'aquesta
   auditoria: **«no ho he pogut comprovar» s'ha de guanyar buscant, no suposant.** Dir-ho com a
   pregunta oberta va servir perquè algú ho tancés, i és millor que inventar-s'ho; però dues de les
   tres es podien tancar des d'aquí.

---

## Com s'han marcat els errors

Als nou documents que contenen les set troballes falses hi ha ara, al lloc exacte de l'error i
**sense esborrar-lo**, un avís de la forma que fa servir el quadern:

```
> **Això es va corregir a <on>:** <què és cert>. El que hi ha aquí sota és el que es va creure.
```

L'error es queda escrit, perquè el valor és veure què es va creure i per què era fals.
