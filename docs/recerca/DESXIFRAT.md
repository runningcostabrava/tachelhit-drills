# El que hem desxifrat

*Quadern de la recerca sobre l'amazic: el so, el tifinag cremat, l'àrab i la traducció. Obert
la nit del 19 de novembre de 2026 i viu des d'aleshores. Cada cosa amb la prova al costat, i
les que han sortit falses també, perquè no es tornin a provar.*

**Com es llegeix.** Només s'hi afegeix: una secció no es reescriu mai, perquè el valor és veure
què es va creure i per què era fals. Quan una secció posterior en desmenteix una d'anterior, la
primera porta un avís que hi apunta. Mira l'índex abans de citar cap número.

## Índex

- **§1** Els subtítols de la SNRT no són una transcripció, i no es poden arreglar
- **§2** La taula estàndard ↔ dialecte existeix i és regular — *corregit a la §44*
- **§3** L'IoU global no pot llegir les lletres-cercle, i es pot arreglar
- **§4** Tres coses que vaig afirmar i eren falses
- **§5** Els graus, i què vol dir cadascun
- **§6** El que queda per saber
- **§7** Una segona manera de tenir dos testimonis (19-11, nit)
- **§8** La franja no és al mateix lloc a cada capítol (19-11, matinada)
- **§9** El desempat topològic val: +5,3 punts (19-11, matinada)
- **§10** La taxa d'acord per línia barreja tres coses (20-11, matinada)
- **§11** El que faria ara, per ordre
- **§12** La nit del 19 al 20 de novembre: l'ull ja no és el problema
- **§13** Resolt: els deu convidats que no entenem són del Rif
- **§14** Correcció important: l'orella els sent, el que no casa és el subtítol
- **§15** L'orella rifenya: la resposta és que el límit és el subtítol
- **§16** Què fer amb això
- **§17** Auditoria dels números de la nit
- **§18** De quina varietat és el Baba Ali (predicció escrita abans del resultat)
- **§19** La ronda: el cercle es tanca per primera vegada
- **§26** El diccionari, comptat bé (20-11, tarda)
- **§27** La regla del cercle, jutjada per capítols (20-11, tarda)
- **§28** El llindar: 0,20 i 0,35 són iguals, i per això s'ha de triar 0,20 (20-11, tarda) — *corregit a la §37*
- **§29** Els espais: quant costen, i què els cura (20-11, nit)
- **§30** Buscar ample quan hi ha qui ho verifica (20-11, nit)
- **§31** Números corregits aquesta nit — *corregit a la §38*
- **§32** La peça que feia entrar el lèxic al feix no era al repositori (21-11, matinada)
- **§33** No tots els «Tadfi n Tskla» porten tifinag (21-11, matinada)
- **§34** Quin model de llengua, decidit sense GPU (21-11, matinada)
- **§35** El glossari al visor, i el mateix error repetit (21-11, matinada)
- **§36** Qui tradueix millor, i qui no arriba (21-11)
- **§37** Les quatre proves són tres, i una no és humana (21-11)
- **§38** El model de llengua al feix, mesurat de debò (21-11)
- **§39** El gir cap a l'àrab (21-11, d'en Pablo)
- **§40** L'ECS tenia una fàbrica millor, i jo duplicava (21-11)
- **§41** L'alineació forçada: −0,0789, i feia tres dies que hi era (21-11)
- **§42** El corpus tenia tarifit, i el dev n'era el 100 % (21-11)
- **§43** El primer guany de debò amb el material del SNRT: 0,2634 → 0,3470 (21-11)
- **§44** La taula norma↔parla tenia 26 entrades que són tarifit (21-11)
- **§45** Retallar amb l'alineació forçada: −0,21 de CER, el guany més gran fins ara (22-11) — *el número no val: §48 i §49*
- **§49** El CER d'inferència premia escurçar el so, no encertar la frontera (23-11)
- **§46** L'energia no pot substituir l'alineació, i el perquè confirma la §45 (22-11) — *mesura invàlida, §48*
- **§47** Tres dreceres per no esperar les 26 h d'alineació, i cap no val (22-11) — *mesura invàlida, §48*
- **§48** L'alineació no alineava la frase: alineava els espais entre paraules (23-11)
- **§50** Del so, el que no és la frase és el 17-20 %, no el 51 % (23-11)
- **§51** La via 3 amb tot el material: el TutlAit és àrab de debò, i l'entrenament passa de 7,4 a 21,4 h (23-11)

---

## 1. Els subtítols de la SNRT no són una transcripció, i no es poden arreglar

El cercle virtuós entrenava amb talls de la SNRT donant el subtítol per bo. No funcionava, i
durant setmanes es va buscar la causa a l'OCR, a l'alineació i al criteri d'entrenament.

**La causa és una altra i no té reparació possible:** el subtítol i la veu diuen coses
diferents *a propòsit*. La cadena escriu en la norma de l'IRCAM i l'actor parla dialecte.

La prova, del capítol «agnkrfivlpeu…», rèplica 0:

```
pantalla: ⴰⵣⵓⵍ ⵉⵎⴰⵏⵏⴰⵢ ⴷ ⵜⵎⴰⵏⵏⴰⵢⵉⵏ ⵏ ⵜⴱⴰⴷⵓⵜ ⵜⴰⵎⴰⵣⵉⵖⵜ
veu     : azul imfarjn timfarjin nnġ iεizzn idnġ ifffanġ
```

Les dues diuen «Hola, espectadors i espectadores». La pantalla escriu **imannay/tmannayin**
(el terme de l'IRCAM); el presentador diu **imfarjn/timfarjin** (el de tothom). Cap de les dues
màquines s'equivoca.

**Conseqüència:** cap millora de l'OCR pujarà l'acord per damunt d'un sostre, i aquest sostre no
és un defecte. El que és un defecte és **haver-ho pres per error** durant setmanes.

---

## 2. La taula estàndard ↔ dialecte existeix i és regular

> **Això es va corregir a la §44:** de les 181 correspondències, **26 venen només de capítols del Rif** i 6 més en són majoria — són tarifit, no dialecte del tachelhit. El 36,4 % de les parelles que van fer la taula vénen d'11 capítols rifenys. La taula neta en té 149. El que hi ha aquí sota es va mesurar abans de saber-ho.

181 correspondències que surten en dos capítols o més, de 26 capítols i 15.745 talls.
**El 61 % difereixen en una sola lletra**, que és el que deia la hipòtesi H-E2 d'en Pablo.

Els patrons que s'hi veuen:

| patró | exemple | vegades |
|---|---|---|
| cau la consonant final | `imaziġn` → `imaziġ`, `iqqand` → `iqqan` | 7, 8 |
| la geminada s'escriu i no se sent | `tanmmirt` → `tanmirt`, `ayyuz` → `ayuz` | 7, 5 |
| **k → š** (palatalització del taixelhit) | `nnk` → `nnš` | 11 |
| ɣ / x | `nnġ` → `nnḫ` | 16 |

Viuen a `estandard_dialecte.jsonl`.

---

## 3. L'IoU global no pot llegir les lletres-cercle, i es pot arreglar

Sis lletres del tifinag són una anella amb una marca diferent a dins. Se solapen entre **0,74 i
0,88**, i l'anella és la major part dels píxels: el que les distingeix són quatre píxels.

A `tskla` —la paraula del títol del programa— el lector tria ⵀ sobre ⵙ per **0,03** i encerta
nou de cada deu vegades. 32 errors d'aquests en vuit capítols.

**La topologia sí que les separa**, i surt de les plantilles mateixes:

| trossos de tinta | forats | signes |
|---|---|---|
| **2** | **1** | **ⵙ** (única) |
| 1 | 2 | ⴱ ⵀ ⵛ |
| 1 | 1 | ⴰ ⴳ ⴽ ⵇ ⵔ ⵕ ⵚ |

Un cercle amb un punt al mig no es pot confondre amb res si es compta en comptes de mirar-se la
forma. D'aquí surt el desempat de `desempat_topologic.py`.

---

## 4. Tres coses que vaig afirmar i eren falses

Les deixo escrites perquè el camí que no va enlloc no s'hagi de tornar a fer.

- **«El text desat és vell; rellegir pujarà l'acord.»** Al Goughelt era cert (10,7 % → 17,1 %).
  Als 26 capítols, **no**: 7 → 6. L'OCR ja llegia bé i la causa era la del punt 1.
- **«El grau B està contaminat d'errors de lectura.»** Al revés: és el material dialectal, i és
  el més valuós que tenim.
- **«La confusió ⵎ→ⴹ espatlla *tamaziġt*.»** Ho vaig deduir d'un fitxer desat per un lector vell.
  Ja estava arreglat: 26 bé i 0 malament en rellegir.

El patró comú de les tres: **diagnosticar des d'un artefacte en comptes de tornar a executar**.

---

## 5. Els graus, i què vol dir cadascun

| grau | l'orella | l'ull | què és | per a què |
|---|---|---|---|---|
| A | segura | hi coincideix | la norma i la parla diuen el mateix | entrenar |
| B | segura | diu una altra cosa | **correspondència estàndard ↔ dialecte** | la taula |
| C | dubta | — | la forma es repeteix i la rescata | esperar |
| D | dubta | — | res | esperar un model millor |

Dels 26 capítols: **A 13.422 paraules (17,7 %), B 27.305 (36,0 %)**. El B és el doble que el A, i
fins avui es llençava.

---

## 6. El que queda per saber

- **ⴱ contra ⵀ** segueixen essent iguals per topologia (1 tros, 2 forats, forats de mida
  gairebé igual). Cal una altra pista: on és la barra, quina inclinació té.
- **ⵔ / ⵕ / ⵚ** (1 tros, 1 forat) es distingeixen pel forat: 285 / 263 / 259 píxels. És poc
  marge i cal mesurar-ho sobre signes de debò, no sobre plantilles.
- **El sostre de l'acord**: no se sap quin és. Amb el fenomen del punt 1, un capítol perfecte no
  arribaria al 100 %, i convindria saber a quant arriba per deixar de perseguir-lo.
- **Els 17 episodis de Baba Ali** que la forja té i la biblioteca no.

---

## 7. Una segona manera de tenir dos testimonis (19-11, nit)

El Baba Ali només porta **àrab cremat**: cap tifinag. O sigui que allà no hi ha ull en amazic i
el creuament del punt 5 no s'hi pot fer.

Però hi ha significat (l'àrab, traduït) i hi ha so. Si es tradueix al català **el que el nostre
model sent en amazic** i coincideix amb el català que ve de l'àrab, també són dos testimonis
independents — no de l'escriptura, sinó **del sentit**:

```
so  --(el nostre ASR)-->  amazic  --(el nostre traductor)-->  català   ⟍
                                                                        ⟩  coincideixen?
àrab cremat  --(lector d'àrab)-->  àrab  --(traductor)-->  català      ⟋
```

Les dues cadenes no comparteixen cap baula. Si diuen el mateix, el més probable és que totes
dues hagin encertat.

Val per a tot el material amb so i significat però sense text amazic de referència: els 3.621
del Baba Ali de la biblioteca i els **17 episodis de la forja que no hem tocat mai** (l'1, el 14
i del 16 al 30, ja baixats).

Límit, dit abans de fer-ho: el traductor amazic→català va a chrF 0,62, o sigui que una
discrepància pot ser seva i no de l'ASR. Serveix per **triar candidats bons**, no per declarar
errors.


---

## 8. La franja no és al mateix lloc a cada capítol (19-11, matinada)

Vaig rellegir capítols retallant sempre la franja a **y 870** de 1080p, que és la geometria
estàndard. Resultat: el capítol «bueyrhjvjyaleo…», que amb el text de la fàbrica és **el millor
de tots** (261 de grau A, 37,3 %), rellegit per mi donava **A = 0** i ni una sola `tskla`.

La causa: **20 dels 25 capítols tenen la franja fora de l'estàndard**, amb set posicions
diferents (y 562 a 592 en 720p). La fàbrica ho mesura a cada capítol i ho desa a
`geometria.json`, dins del mateix paquet que jo baixava — i no l'extreia.

Retallava nou píxels massa avall i escapçava els signes per dalt.

**Queden invalidades dues coses que havia donat per mesurades:**

- «Rellegir els 26 no millora l'acord» (7 → 6 al capítol provat).
- «El desempat topològic no mou res» (A = 0 amb i sense).

Totes dues es van fer sobre franges mal retallades. S'han de tornar a fer, i s'estan fent.

**La lliçó, que és la tercera vegada aquesta nit:** quan un resultat és absurd —el millor
capítol donant zero— el primer sospitós no és el món, sóc jo. Vaig estar a punt de concloure
que el desempat no servia.

També: la durada del vídeo de la forja (3.225,7 s) coincideix EXACTAMENT amb la que va mesurar
la fàbrica, o sigui que el vídeo sí que és el mateix i els temps casen. Aquella por era
infundada i val la pena deixar-ho dit.


---

## 9. El desempat topològic val: +5,3 punts (19-11, matinada)

Amb la geometria bona del capítol (y 861, no 870), al «bueyrhjvjyaleo…», 700 rèpliques:

| | grau A | `tskla` |
|---|---|---|
| sense desempat | 239 · 34,1 % | 3 bé / 6 amb ⵀ |
| **amb desempat** | **276 · 39,4 %** | **9 bé / 0 amb ⵀ** |

**+5,29 punts.** I no és només `tskla`: guanya 37 línies i la paraula n'explica 6; la resta són
altres confusions de la família dels cercles (ⵙ ⵀ ⴱ ⵛ).

De passada, el 34,1 % de la relectura queda a prop del 37,3 % que donava el text de la fàbrica:
el lector d'ara i el que va fer servir ella llegeixen pràcticament igual, i la diferència de
qualitat entre capítols NO era text vell. Era una altra cosa (punt 1: la parla contra la norma).

Pendent abans de proposar-ho al repositori: confirmar-ho en dos capítols més. Un sol capítol pot
ser casualitat.


---

---

## 10. La taxa d'acord per línia barreja tres coses (20-11, matinada)

Els 25 capítols no fan un degradat: fan **tres grups**.

| grup | acord per línia | acord per paraula | què passa |
|---|---|---|---|
| bons (11) | 8-39 % | 21-40 % | tot funciona |
| mitjans (8) | 0,3-1,6 % | **8-12 %** | l'ull llegeix bé i la parla diu una altra cosa |
| trencats (6) | 0-0,3 % | 1,7-3,1 % | l'OCR ha perdut text |

**El jutge que els separa és l'àrab**, que és una tercera lectura independent i mesurada
(CER 0,0059). Es compara quanta lletra amaziga hi ha per caràcter àrab contra el que és normal
als capítols bons (1,072), i quantes rèpliques tenen àrab i gairebé cap tifinag:

- `caxyzjdttlgi`: 60 % del text esperat i **19 % de rèpliques mudes** → l'OCR no hi arriba.
  Mirant la franja es veu per què: el subtítol va sobre un fons fosc, vermell i ple de branques.
- `nknrztnktbva`: 91 % del text, **0 % de mudes**, i acord 0,8 % → l'OCR va bé i el que canvia
  és què es diu.

**I la conclusió que importa:** els vuit del grup mitjà donen entre **200 i 320 paraules de
grau A cadascun**. Jutjats per línia semblaven inservibles; per paraula no ho són. Mirar línies
senceres llençava unes 2.000 paraules ben sentides.

La confiança que la fàbrica desa (`tifinag_conf_mitjana`) **no serveix** per detectar-ho:
correlació +0,33 amb l'acord, i `agnkrfivlpeuwzme` té 0,964 amb un 0,9 % d'acord. L'únic que va
detectar bé és el `caxyzjdttlgi` (0,479). El que sí que avisa és el nombre de glifs llegits
(17.000-20.000 als bons, 8.776-13.000 als trencats) i, sobretot, les rèpliques mudes.

---

## 11. El que faria ara, per ordre

1. **Proposar el desempat topològic al repositori.** Mesurat: +5,3 punts on hi ha confusions de
   cercles, 0,00 on no n'hi ha, cap regressió en tres capítols.
2. **Arreglar els sis capítols trencats**, que és un problema de binarització sobre fons
   carregat, no de plantilles. El `LLINDAR_LOCAL` que ja hi ha al lector és la via.
3. **Deixar de jutjar per línia.** El magatzem per paraula ja hi és; el que falta és que el
   cercle hi begui en comptes de beure de línies senceres.
4. **L'àrab com a jutge, de manera sistemàtica.** Avui l'he fet servir a mà per separar dues
   avaries. Hauria de ser una comprovació de cada capítol, abans de donar-lo per bo.

## 12. La nit del 19 al 20 de novembre: l'ull ja no és el problema

Dues coses s'han tancat aquesta nit i una s'ha obert.

### 12.1 Els capítols donats per morts només estaven mal llegits

La fàbrica va llegir els subtítols del vídeo de **720p**; ara en tenim de **1080p**, i cada
capítol té la seva franja a `geometries.json`. Rellegits amb el lector d'ara (que ja porta el
desempat topològic de la PR #700):

| capítol | fàbrica (720p) | relectura (1080p) |
|---|---|---|
| asywmmpqztvnotxd | 0,0 % | **25,8 %** |
| wvvizytgxfihllta | 0,0 % | **29,8 %** |
| hbkjilqmyknmftva | 0,0 % | **18,8 %** |
| caxyzjdttlgivxih | 0,0 % | **16,7 %** |
| bueyrhjvjyaleocf | 38,8 % | **41,7 %** |

On la fàbrica guanya, guanya per dècimes (38,7 contra 38,2) — soroll. La tria es fa capítol a
capítol amb l'orella d'àrbitre i surt a `text_triat.jsonl` (15.365 rèpliques).

**Desdita:** vaig dir que la fàbrica guanyava als capítols bons perquè llegeix diversos
fotogrames i en treu consens. Aquell número (37,3 contra 34,1) era d'abans d'arreglar la
geometria i de fusionar el desempat. Amb les dues coses, la relectura guanya també allà.

### 12.2 Per què deu episodis donen ~1 % d'acord: no és l'ull

Els 22 capítols són **el mateix programa** (*Tadfi n Tskla*, una entrevista literària, un
convidat per episodi) i l'acord va de 41,7 % a 0,4 %, sense res al mig. Descartat, un per un:

| hipòtesi | com s'ha mirat | resultat |
|---|---|---|
| l'ull llegeix malament | les tres lectures de la mateixa rèplica de costat | no: l'àrab confirma el tifinag paraula per paraula |
| índex desplaçat | acord amb l'orella desplaçada de −3 a +3 línies | no: d=0 guanya als 22 |
| desfasament en temps | per cada rèplica, quina línia de TOT l'episodi casa més | no: a l'episodi bo 30 de 34 encerts són la línia justa; als dolents 1 de 75, a +548 línies |
| el convidat parla àrab | acord amb l'esquelet de consonants de l'àrab | no: 0,0–0,9 % pertot |
| frases massa llargues | acord per trams de llargada i per capítol | no: correlació −0,09 |
| el tall d'àudio és dolent | RMS, silenci, i correlació amb el meu vídeo al mateix instant | no: veu de debò (RMS 0,059) i al moment bo (+0,59) |

Per eliminació: **el model no entén aquells parlants.** No és una avaria, és un límit, i va
**per convidat**, no per capítol — cosa que té sentit, perquè són escriptors de llocs diferents
i nosaltres només hi posem l'orella del tachelhit (`shi`).

**Desdita:** vaig dir que l'explicació era la llargada de la frase, després d'imprimir les
rèpliques 20-28 de dos episodis. Al bo hi queia una escena de servir el te, tota de frases
curtes. Vaig triar els exemples que em donaven la raó; el número diu −0,09.

**Desdita:** vaig llegir `qdaš mas muṣṭafa` com *shukran lak sayyid Muṣṭafā* i vaig donar per
fet que el convidat parlava àrab. Mesurat amb tot l'episodi, l'acord amb l'àrab és 0,0 %.

### 12.3 Què s'ha obert: provar altres orelles

L'MMS porta adaptadors per varietat. Si la causa és la varietat, passar el mateix so per
`tzm` (Atles central), `zgh` (estàndard marroquí), `rif`, `kab` i `ary` (àrab marroquí, de
control) ha de donar, per cada convidat, quin adaptador l'entén. Això no és només arreglar un
número: és **saber de quina varietat parla cada escriptor del programa**, que és coneixement
que volem tenir.

Preparat a `prova_adaptadors/` (55 talls per episodi, 10 dolents i 2 de control) amb el nucli
`sent_adaptadors.py`. La comparació es fa a casa, perquè les sortides de `ary` van en alfabet
àrab i s'han de comparar amb el subtítol àrab, no amb el tifinag.

### 12.4 El que val d'aquesta nit, en una frase

Set hipòtesis meves, sis de mortes i cap de les mortes era absurda: totes eren raonables i
totes estaven equivocades. L'única manera de saber-ho ha estat **mesurar-les d'una en una amb
un testimoni que no hi tingués interès**. El mètode no és tenir bones idees; és tenir un
àrbitre.

### 12.5 El corpus refet, i un número meu que estava inflat

Amb el text triat i l'aparellament per ordre:

| | abans | ara |
|---|---|---|
| rèpliques de grau A amb significat | 1.560 | **2.190** |
| hores de so amb significat | 1,78 h | **2,14 h** |
| paraules de grau A | 13.422 | **6.779** |

Les rèpliques creixen perquè quatre capítols morts han ressuscitat. Les **paraules cauen a la
meitat** perquè el 13.422 el vaig comptar amb l'aparellament per veïnatge, que és cec a l'ordre
i aparella coses que no van juntes. Comptat sobre el mateix text, el veïnatge en dona 17.298 i
l'alineació per ordre 6.779: **el número que vaig reportar estava inflat pel doble**.

I una tercera errada meva, d'avui: `alinea()` torna parelles d'**índexs** `(i, j)` i jo les
desempaquetava com si fossin `(paraula, distància)`. Això comparava un índex amb 0,35, o sigui
que només donava grau A quan la paraula de l'ull era la primera de la línia; en sortien 2.330.
Es va veure perquè la caiguda era massa grossa i la vaig mirar en comptes de publicar-la.

Mostra del que hi ha ara, a l'atzar (`sentit ↔ norma`, distància, confiança):

    imaziġn  ⵉⵎⴰⵣⵉⵖⵏ    0,00  0,90      azul     ⴰⵣⵓⵍ      0,00  0,98
    tġuriwin ⵜⵖⵓⵔⵉⵡⵉⵏ   0,00  0,95      tbrat    ⵜⴰⴱⵔⴰⵜ    0,00  0,91
    uġnij    ⵓⵖⵏⵏⵉⵊ     0,25  0,87      ttansa   ⵜⴰⵏⵙⴰ     0,25  0,91

### 12.6 La varietat: el model només té tres orelles amazigues

L'MMS-1b-all porta 1.198 llengües, i d'amazigues només tres: **`shi`** (tachelhit, el que fem
servir), **`kab`** (cabilenc) i **`taq`** (tamasheq, el tuareg). No hi ha `tzm` (Atles central),
ni `zgh` (estàndard marroquí), ni `rif` (tarifit). Això vol dir que **la hipòtesi de la varietat
no es pot provar del tot amb aquest model**, i val més dir-ho que donar la prova per feta.

Amb 55 talls per episodi, `kab` contra `shi`:

| | shi | kab |
|---|---|---|
| SALEH AIT SALEH (control) | 40,0 % | 41,8 % |
| SAID OU BOULMAN (control) | 35,2 % | 44,4 % |
| els deu episodis dolents | 0–2 % | 0–2 % |

Dues coses. La primera: **el cabilenc no rescata els deu episodis dolents**, igual que el
tachelhit. La segona és més interessant i no es pot afirmar amb aquesta mostra: als controls el
cabilenc sembla anar millor, però són 47 encerts contra 41 sobre 109 talls, que cap dins del
soroll. Si fos cert seria una millora gratuïta de tot el projecte (el `kab` de l'MMS té molta
més matèria d'entrenament que el `shi`), i per això es mesura amb 3.600 talls dels dotze
episodis que l'orella sí que entén.

### 12.7 Dues hipòtesis més mortes, i la mateixa causa

- **«L'orella es menja els finals de les paraules.»** Ho semblava a les 43 parelles ancorades
  (`iskkiln`→`iskil`, `tullist`→`tulli`, `asmuttg`→`asmut`). Mesurat sobre 16.997 parelles:
  l'orella és **més llarga** el 40 % de les vegades i més curta el 21 %, i els errors es
  reparteixen igual entre el principi (20,1 %) i el final (19,1 %).
- **«Del grau B en surt una taula norma ↔ parla.»** Filtrada per repetició en boques diferents,
  en queden 8 parelles i **totes vuit són el mateix artefacte**: la frase *tutlayt tamaziġt*
  aparellada amb un lloc de desplaçament. Ancorant-la pels dos costats (la paraula d'abans i la
  de després han de casar) queden 43 observacions i cap no es repeteix. Això posa en dubte les
  181 parelles de `estandard_dialecte.jsonl`, que van sortir de l'aparellament cec a l'ordre.

Les 43 ancorades, però, no són per llençar: quatre o cinc són or de debò, i la millor és
**ⵜⵓⵍⵍⵉⵙⵉⵏ *tullisin* ↔ *tqssisin*** — la norma fa servir la paraula amaziga per «contes» i el
convidat l'arabisme (*qiṣṣa*). També `ⵖⴰⵙⵙⴰⴷ ġassad ↔ ġaṣṣad`, `ⵢⴼⴼⵓⵢⵙ yffuys ↔ iffus` i
`ⵜⵣⴹⴰⵕⵜ tzḍart ↔ tẓẓart`.

La causa de les dues errades és la mateixa i és meva: **llegir una regularitat en un grapat
d'exemples triats per mi**. Set hipòtesis aquesta nit, cinc de mortes per aquest mateix vici.

### 12.8 Les quatre orelles de l'MMS, mesurades

639 talls (55 per episodi, deu dolents i dos controls), el mateix so per totes quatre:

| orella | acord global |
|---|---|
| `kab` cabilenc | **8,0 %** (51 de 634) |
| `shi` tachelhit (la que fem servir) | 6,8 % (43 de 636) |
| `taq` tamasheq (tuareg) | 1,7 % (11 de 636) |
| `ara` àrab | **0,2 %** (1 de 625) |

Tres coses:

1. **L'àrab queda descartat amb un transcriptor d'àrab de debò**: 1 encert de 625. La hipòtesi
   era meva i la vaig provar primer amb un esquelet de consonants fet a mà; ara està provada
   amb l'eina bona i el resultat és el mateix.
2. **Cap de les quatre toca els deu episodis dolents**: totes entre 0 i 2 %.
3. Als dos controls el cabilenc va igual o millor que el tachelhit (41,8/44,4 contra 40,0/35,2),
   però amb 55 talls per episodi això no decideix res: 47 encerts contra 41 sobre 109.

Conclusió honesta: aquells deu convidats són inaccessibles a **totes** les orelles amazigues que
l'MMS porta, i no parlen àrab. La causa més probable segueix sent la varietat (Atles central o
Rif, que l'MMS no té), i **amb aquest model això no es pot provar**. És el límit d'aquesta via.

### 12.9 La ronda d'entrenament, i què n'espero abans de mesurar-la

El nucli del cercle (`tools/lm/kaggle/transcriptor_snrt.py`, commit `c2044c4`) es fa servir tal
com és; l'únic que canvia és **d'on surt el train**: ja no el tria el filtre de CER sobre text
ric, sinó el grau A d'esquelet de consonants.

    train 1.678 talls · dev 171 · test 1.163 (quatre capítols SENCERS retinguts, sense filtre)
    retinguts: Zahour i Akounad (l'orella els entén) · Khbiza i Abarnous (no)
    recepta B (SNRT + les dades d'H4b, perquè el model no oblidi el que ja sabia)

**El que espero, dit abans:** que els dos retinguts bons millorin i que els dos dolents **no es
moguin**. El train surt de rèpliques que el model ja encerta a mitges, i els deu convidats que
no entén hi aporten entre 2 i 10 rèpliques cada un. Si els dolents també milloren, el límit és
el domini i no el parlant, i llavors el pla canvia.

La regla d'acceptació no la toco: `M_{r+1}` només si dues proves milloren amb interval de
confiança i cap no empitjora.

### 12.10 Dues lectures independents de la mateixa imatge, i cinc capítols mal apuntats

Comparant el text que la fàbrica va desar amb la relectura d'ara, desplaçant les línies de −6 a
+6, surt una cosa que no buscava:

- A **20 dels 25** capítols les dues lectures coincideixen al **93–99 %** i a d=0. Són dos codis
  diferents, dues resolucions diferents i dos moments diferents llegint la mateixa imatge: que
  diguin el mateix valida **el lector**, no només la relectura.
- A **cinc** no coincideixen a **cap** desplaçament: ZAID OUCHNA, ASMAE MOUDOUBAH, BRAHIM EL
  ASRI, RACHID FARIS i ALI EL ABDELLAOUI. El text desat d'aquells capítols no té relació amb la
  imatge, i són justament els que la relectura ha rescatat.

No és un desplaçament constant, i això diu el mecanisme: la fàbrica agrupa fotogrames idèntics
en **trams** i desa una lectura per tram. Si els trams surten malament, les lectures cauen en
rèpliques equivocades amb un desajust que varia de tram en tram — i cap prova de desplaçament
constant no ho pot veure.

Comprovat amb el tercer testimoni, que no va participar en la tria. El capítol de HASNAE FATNI,
línia a línia:

    abans (720p)  ,
    ara  (1080p)  ⴽⵓ ⴰⵙⴽⴽⵉⵍ ⴰⵎⴰⵣⵉⵖ ⴷ ⵜⵓⵊⵊⵓⵜ ⵏ ⵡⴰⴽⴰⵍ
    àrab          كل حرف أمازيغي هو عبق لهذه الأرض
    català        Cada lletra amaziga és una fragància d'aquesta terra.

Paraula per paraula. I el que hi havia abans era `,`, `ⵎ 1`, `?ⵯ` i `ⴳ`.

### 12.11 L'índex per paraula, que és el que havies demanat

`index_paraules.tsv`: una fila per forma sentida, amb els quatre fets que la sostenen i cap
número inventat per mi — vegades, vegades amb acord de l'ull, boques (episodis diferents, o
sigui convidats diferents) i confiança mitjana. Ordenat per **vegades amb acord**, que és el fet
més fort que tenim: dos testimonis que no saben res l'un de l'altre dient la mateixa cosa,
diverses vegades i en boques diferents.

    formes diferents sentides        39.274
    acordades alguna vegada           3.967
    acordades 2+ vegades                741
    acordades 2+ vegades, 2+ boques     680   <- el nucli
    acordades 10+ vegades                78

El cap de la llista no l'hi ha posat ningú:

| sentit | escrit | vegades | amb acord | boques |
|---|---|---|---|---|
| tmaziġt | ⵜⵎⴰⵣⵉⵖⵜ | 371 | 165 | 25 |
| tskla «literatura» | ⵜⵙⴽⵍⴰ | 110 | 64 | 25 |
| tirra «escriptura» | ⵜⵉⵔⵔⴰ | 103 | 53 | 14 |
| tutlayt «llengua» | ⵜⵓⵜⵍⴰⵢⵜ | 119 | 46 | 18 |
| ungal «novel·la» | ⵓⵏⴳⴰⵍ | 69 | 22 | 13 |
| wawal «paraula» | ⵡⴰⵡⴰⵍ | 55 | 22 | 17 |

El programa es diu *Tadfi n Tskla*, «la fragància de la literatura»: l'índex n'ha tret el
vocabulari central sense que ningú li digués de què parlen.

I una parella que val la pena: **nnḫ** (56 vegades) i **nnġ** (128) van totes dues a ⵏⵏⵖ,
«nostre» — la mateixa paraula sentida de dues maneres, amb 184 ocurrències al darrere. Això sí
que és una correspondència, i ha sortit de l'índex, no de la taula de grau B.

### 12.12 La variació, treta de l'ACORD i no del desacord

La taula de grau B no va donar res perquè busca la variació al lloc més dèbil: allà on l'ull i
l'orella **discrepen**. Hi ha una manera millor, i ha sortit mirant l'índex: **dues formes
sentides diferents que casen totes dues amb la mateixa paraula escrita**, cada una acordada
diverses vegades. Això no és desacord, són dos acords, i la diferència entre ells és la
variació.

97 paraules escrites tenen dues formes sentides o més, cada una acordada 2+ vegades i diferents
en consonants (`variants.tsv`). I l'escapçament es separa de la variació mecànicament: un
escapçament és un **tros** de la forma plena, i el filtre es fa contra la paraula **escrita**,
no entre les dues formes — `ns` i `nn` són tots dos trossos de `nns`, i comparats entre ells
semblarien un canvi n~s (`variacio.tsv`).

Els canvis de consonant que en surten, pel pes de la parella més feble:

| canvi | pes | |
|---|---|---|
| **ġ ~ ḫ** | 25 | el més gros, i el més sospitós (vegeu sota) |
| **k ~ š** | 11 | la palatalització del tachelhit |
| **l ~ r** | 10 | |
| **s ~ z** | 8 | *tmdyazt / tmdyast* |
| **ḍ ~ ṭ** | 7 | *taḍfi / taṭfi* |
| **m ~ n** | 5 | *tġnsa / tġmsa* |
| **g ~ y** | 2 | *urgaz / uryaz*, l'alternança coneguda d'«home» |

**El que no sé separar encara, i cal dir-ho:** aquestes parelles són on l'orella sent dues coses
per la mateixa paraula escrita, i això barreja la variació del parlant amb les confusions
sistemàtiques de l'orella. El ġ~ḫ, que és el més gros, fa tota la pinta de ser nostre — la
nostra transliteració porta ɣ→ġ i x→ḫ, i són dues fricatives veïnes.

I té prova: **una segona orella**. Si el `kab` també sent ḫ on la pantalla escriu ⵖ, és parla;
si hi sent ġ, era una confusió de l'adaptador `shi`. Les dades per decidir-ho són les de la
mostra gran de 3.515 talls que corre ara.

### 12.13 La millor hipòtesi de la nit: els deu convidats no parlen tachelhit

Ha sortit per una porta de darrere. A l'índex, la paraula escrita ⵏⵏⴽ («teu») es sent `nnš` 20
vegades i `nnk` 11, i mirant on cauen aquelles š resulta que **es concentren**: dotze episodis en
tenen zero i uns pocs en tenen entre 10 i 25 %. I a la taula de variació hi havia `wawal/wawar`
i `umaḍal/umaḍar`, o sigui **l → r**.

`nnš` i l → r són dues marques conegudes del **rifeny**. Mesurades per episodi, i només sobre
paraules que casen:

| convidat | acord | k→š | l→r |
|---|---|---|---|
| HAYAT BOUTERFAS | 0,8 % | 25 % | 11 % |
| RACHID FARIS | 0,4 % | 20 % | 15 % |
| SAID AL MOUSSAWI | 1,7 % | 18 % | 33 % |
| ANDICHI CHAHID | 1,9 % | 11 % | 16 % |
| … | | | |
| ASMAE MOUDOUBAH | 29,8 % | 0 % | 0 % |
| LAHCEN ZAHOUR | 23,5 % | 0 % | 0 % |

    correlació k→š amb l→r:      +0,58
    correlació k→š amb l'acord:  -0,46

Dues marques fonètiques independents assenyalen **els mateixos** convidats, i són els que la
nostra orella no entén. Això ho explicaria tot d'una sola vegada, i explicaria també per què cap
adaptador de l'MMS no els rescata: **l'MMS no té `rif`**.

**El confós, dit:** les dues marques es mesuren només sobre paraules que casen, i en un episodi
amb 0,5 % d'acord n'hi ha molt poques (el mínim exigit és 5 i 10). La correlació es sosté en
mostres petites.

**Com es prova:** una orella que sàpiga rifeny. L'MMS no en té, de manera que la via és
entrenar-ne una o trobar un model de tarifit i passar-li aquells deu episodis. Si els entén, la
hipòtesi queda provada i a més sabrem de quina varietat és cada convidat — que és coneixement
que volem tenir per ell mateix, no només per arreglar un número.

Comprovació externa intentada i sense resultat: els noms dels convidats en alfabet llatí no
surten a cap font fiable, i no val la pena insistir buscant persones concretes.

### 12.14 La prova de la hipòtesi del rifeny: una orella que en sap

L'MMS no porta `rif`, però algú n'ha fet un afinament del **mateix model base que fem servir**:
`iukocha/mms-tachebdant-from-tarifit` (base `facebook/mms-1b-all`, llicència CC-BY-NC-4.0 —
recerca sí, desplegar no, que és el marc d'aquest treball).

Passa pels **mateixos 639 talls** que ja han passat per `shi`, `kab`, `taq` i `ara`: mateix so,
mateixa regla, una orella més.

**La predicció, escrita abans de mesurar-la:** si aquells deu convidats parlen una varietat del
Rif, aquesta orella n'ha de treure **més** acord que el `shi` (que hi fa 0–2 %) i als dos
controls de tachelhit n'ha de treure **menys** (el `shi` hi fa 35–40 %). Si no passa cap de les
dues coses, la hipòtesi cau i cal dir-ho.

Nota de camí: en local no es pot córrer. El `venv` del backend porta numpy 1.26 perquè és el que
desplega a Render, i transformers 5.23 en demana 2.x (`np.long`). No es toca aquell `venv` per
una prova; va a Kaggle.

### 12.15 Una trampa de la meva pròpia comptabilitat

La ronda corre des de les 03:13:09 amb recepta B i 4 èpoques, i amb les dades **netes** (la
pujada neta va acabar a les 03:08). Però hi havia un parany que m'hauria fet rebutjar el resultat
bo: **cada intent de llançament escriu la marca local**, i aquesta nit n'hi va haver que van
fallar per falta de GPU *després* del que va entrar. El fitxer de marca es va quedar amb la
03:16:50 i el quadern corre amb la 03:13:09, de manera que la comprovació «aquesta sortida és
d'aquesta execució?» hauria dit que no.

Arreglat on toca: la marca de debò és la del **codi que ha corregut** (es llegeix amb
`kernels_pull` i es treu el `RUN_ID`), no la del meu fitxer. La lliçó del 18-11 era «no donar per
bona una sortida vella»; aquesta nit s'hi afegeix la del revés — **no donar per vella una
sortida bona**, que fa perdre la feina igualment.

### 12.16 El cabilenc contra el tachelhit, decidit — i una desdita meva del ġ~ḫ

**3.515 talls dels dotze episodis que l'orella entén, el mateix so per les dues orelles:**

| orella | acord |
|---|---|
| **`shi` tachelhit** | **21,8 %** (764 de 3.512) |
| `kab` cabilenc | 20,2 % (704 de 3.489) |

El tachelhit guanya, per 1,6 punts, i guanya a 9 dels 12 episodis. El que semblava al mostreig
de 55 talls per episodi (kab 41,8/44,4 contra shi 40,0/35,2) era soroll, com ja es deia allà.
**No hi ha millora gratuïta: ens quedem amb `shi`.**

**Desdita:** vaig dir que el ġ~ḫ «fa tota la pinta de ser nostre» perquè el `kab` no el feia cap
vegada en 37 paraules. Amb 377:

| orella | paraules amb ⵖ a la pantalla | hi diu ḫ |
|---|---|---|
| `shi` | 274 | 6,6 % |
| `kab` | 377 | **7,7 %** |

Dues orelles independents hi senten ḫ amb la mateixa freqüència, i totes dues sobre la mateixa
paraula: *tamaziġt* → *tamaziḫt*. **El ġ~ḫ és a la parla, no és nostre.**

I el k~š **no es pot decidir amb aquesta mostra**, per una raó que té sentit: aquests 3.515 talls
són dels episodis **bons**, i allà la š no hi és (1 de 186 amb `shi`, 0 de 241 amb `kab`). La š es
concentrava als dolents, i d'aquells només en tinc 55 talls per episodi. La hipòtesi del rifeny
segueix penjant de l'l→r i de 19 ocurrències de š: la prova que la decideix és l'orella rifenya.

Això afina la regla 9.2 del mètode: **una segona orella només serveix si la mostra arriba al
fenomen**. Zero de 37 no vol dir zero.

### 12.17 El català del corpus, mesurat pel que es pot mesurar

El corpus de grau A és el que es veuria (so, tifinag, àrab, català), i el català va sortir de
l'àrab amb la cascada de quota gratuïta. Comptant només els trencaments **objectius** —sense
català, lletres àrabs o tifinag a dins, caràcters trencats, paraules repetides, llargada
desproporcionada:

    sense cap trencament objectiu    2.179 de 2.190   99,5 %

I de les 11 marcades, la majoria són falsos positius del meu propi filtre: «I amb nosaltres hi
ha un artista» per *wa-maʿanā fannān* està bé, i «tots escriuen, tots seleccionen i tots
examinen» repeteix «tots» perquè l'àrab repeteix *jamīʿan*.

Però n'hi ha una que sí que és dolenta: «És un conte que algú del Marroc va explicar en amazic»
per un àrab que diu que l'escriptura és una estructura de poesia, conte i teatre. Dues coses,
doncs: **el volum no és el problema**, i **si diuen el que diu l'àrab no està mesurat** — això
demana algú que llegeixi àrab i no està fet.

## 13. Resolt: els deu convidats que no entenem són del Rif

Hi havia un testimoni que no havia fet servir i que no toca res del nostre: **el presentador diu
d'on és cada convidat**, i això ho tenim en català, vingut de l'àrab. L'àrab no ha passat ni pel
nostre OCR de tifinag ni per la nostra orella.

Comptant les mencions de lloc de cada episodi (Sus i Anti-Atles, Atles central, Rif i est):

| convidat | acord | zona que domina |
|---|---|---|
| SALEH AIT SALEH | 38,7 % | Sus 10 — *«has vingut d'Agadir o de Taroudant?»* |
| MOHAMED AKOUNAD | 33,5 % | Sus 17 — *«ets el pioner de la literatura del Sus»* |
| MOHAMED OUAGRAR | 22,5 % | Sus 28 |
| LAHCEN ZAHOUR | 23,5 % | Sus 10 |
| **ZAID OUCHNA** | **16,7 %** | **Atles central 16** |
| **MOHAMED MOUHIB** | **15,1 %** | **Atles central 52** |
| ANDICHI CHAHID | 1,9 % | **Rif 24** |
| SAID AL MOUSSAWI | 1,7 % | **Rif 23** |
| HAYAT BOUTERFAS | 0,8 % | **Rif 26** |
| SAID ABARNOUS | 0,5 % | **Rif 41** |
| IBTISSAM KHBIZA | 0,4 % | **Rif 6** |

    correlació (part de mencions del Rif) amb l'acord:   -0,79
    acord mitjà on domina el Rif (11 episodis):            1,7 %
    acord mitjà on no domina (12 episodis):               22,7 %

**Tretze vegades més.** I els dos casos del mig —Ouchna i Mouhib, 15–17 %— són de l'**Atles
central**, que és exactament on ha de quedar una varietat intermèdia entre el tachelhit i el
rifeny. La gradació és la que la geografia demana.

Això explica d'una sola vegada tot el que la nit havia anat descartant: per què l'ull llegeix bé
i l'orella no casa, per què el so és bo i al moment correcte, per què cap adaptador amazic de
l'MMS no els toca (no hi ha `rif`), i per què k→š i l→r —les dues marques del tarifit— es
concentren justament en aquells episodis.

**El confós, dit:** les mencions es compten a tot l'episodi, i un convidat del Sus que parli de
música del Rif en produeix (Said Ou Boulman: *«escolto tota mena de música, la del Rif i la del
Sus»*). Per això es mira la zona que domina, i la separació aguanta igual: 41 mencions del Rif
contra 4 del Sus a l'episodi d'Abarnous.

### 13.1 Què canvia

1. **Els deu episodis del Rif no són material espatllat: són un sub-corpus de tarifit.** 5.800
   rèpliques amb so, àrab i català, i amb el subtítol en tifinag estàndard. No s'han de llençar
   ni s'han de barrejar: s'han de marcar.
2. **El corpus de tachelhit és més net del que crèiem**: dels 25 episodis, dotze són del Sus,
   dos de l'Atles central i deu del Rif. L'acord del 22,7 % als dotze bons és el número de debò
   del nostre lector i la nostra orella sobre tachelhit; el 13 % global barrejava tres llengües.
3. **La prova de l'orella rifenya** ja no és una temptativa: és la manera d'obrir aquelles deu
   hores. Si funciona, el projecte guanya una varietat sencera.
4. **El principi de varietat del projecte hi queda complit**: una frase ha de dir d'on és, i ara
   sabem d'on és cada una d'aquestes 15.365.

### 13.2 Marcat, i amb la regla corregida

La primera regla —«la zona que surt més»— era massa crua i em va posar **Said Ou Boulman**, que
és l'episodi amb **més acord de tots** (41,7 %), com a tarifit: havia parlat de música del Rif i
tenia 5 mencions del Rif contra 4 del Sus. Era el confós que jo mateix havia advertit dues
línies abans.

La regla d'ara demana **majoria clara (≥60 %) i que l'acord no la contradigui**; quan es
contradiuen, diu «en dubte» en comptes de triar. Cada episodi porta desat com s'ha decidit
(`varietats.tsv`, `varietats.json`).

| varietat | episodis | línies | acord mitjà |
|---|---|---|---|
| **tachelhit** | 11 | 6.704 | **27,2 %** |
| amazic de l'Atles central | 3 | 2.010 | **19,3 %** |
| **tarifit** | 11 | 6.651 | **1,6 %** |

La gradació és la que la geografia demana: el Sus a dalt, l'Atles central al mig, el Rif a terra.

**I el número que importa: l'acord de la nostra orella amb el nostre ull sobre tachelhit és
27,2 %, no el 13 % que deia aquesta tarda.** Aquell 13 % barrejava tres llengües i es castigava
amb episodis que no eren del seu idioma. Mesurat sobre el que és, el lector i el transcriptor van
el doble de bé del que crèiem.

### 13.3 Què hi ha, de debò, dins d'aquestes 17,68 hores

| varietat | rèpliques | hores | amb català | amb la nostra transcripció |
|---|---|---|---|---|
| tachelhit | 6.704 | 7,95 h | totes | 6.495 |
| **tarifit** | 6.651 | **7,67 h** | totes | 6.270 |
| **amazic de l'Atles central** | 2.010 | **2,07 h** | totes | 1.869 |
| | **15.365** | **17,68 h** | | 14.634 |

Dues coses que fins ara estaven amagades dins d'un 13 % global que no volia dir res:

1. **7,67 hores de tarifit** amb so, subtítol en tifinag estàndard, àrab i català. El tarifit té
   molt menys material disponible que el tachelhit, i aquí n'hi ha vuit hores alineades.
2. **2,07 hores d'amazic de l'Atles central** —Hasnae Fatni, Zaid Ouchna i Mohamed Mouhib—, que
   és **la varietat que aquest projecte documenta** (Aït Mraw, la zona d'Azilal–Kalaat M'Gouna,
   el principi de varietat de `CLAUDE.md`). Amb 19,3 % d'acord: material utilitzable, i de la
   llengua que de debò fa falta.

Això no és un arranjament d'un número: és que el corpus era tres corpus i no ho sabíem.

### 13.4 Les dues marques, soles, separen les tres varietats

| varietat | k→š | l→r | acord | episodis |
|---|---|---|---|---|
| tachelhit | 1,8 % | 1,0 % | 26,4 % | 11 |
| amazic de l'Atles central | **5,7 %** | 1,3 % | 19,2 % | 3 |
| tarifit | **12,1 %** | **12,9 %** | 1,7 % | 11 |

L'**l→r** és el que marca el rifeny (13 % contra 1 %), i la **k→š va en gradació d'oest a est**
(1,8 → 5,7 → 12,1), que és el que diu la dialectologia amaziga: la palatalització creix cap a
l'est i l'l→r és específic del Rif. Les dues mesures surten del nostre so i del nostre subtítol,
sense cap veritat humana.

**La predicció que això permet, i que es pot comprovar:** en un episodi nou, mesurar les dues
marques i dir la varietat —cap de les dues, tachelhit; només k→š, Atles central; totes dues,
tarifit— i **després** mirar què diu el presentador. Si encerta, tenim un classificador de
varietat que només necessita escoltar.

**El confós:** l'Atles central són tres episodis, i les marques es mesuren a través de l'orella
de tachelhit, que hi pot posar biaix. La fila del mig és feble; les de dalt i de baix, no.

### 13.5 El lèxic diferencial: la confirmació que no esperava tan neta

Amb cada episodi marcat, es pot comptar cada forma sentida per mil paraules a cada varietat i
veure quines es reparteixen desigualment. Demanant 12+ ocurrències i 3+ episodis de la seva banda
(per no recollir el vocabulari d'un convidat sol) surten **156 formes**. I el que surt és el
parell de llibre de text:

| concepte | tachelhit | tarifit |
|---|---|---|
| «molt» | **bahra** (138 vegades, 9 episodis) | **aṭṭas** (23, 10 episodis) |
| «paraula» | **wawal** | **wawar** |
| «poesia, poemes» | **tmdyazt** (30) | **izran** (21), **asfru** (21) |
| «jo» | **nkki** (48) | — |
| «com» | — | **mamš** (31, 10 episodis) |
| «tot» | — | **marra** (16) |
| «quan» | **lliġ** (69) | — |
| «ara» | **ġilad** (53) | — |
| «altre» | **yaḍnin** (62) | — |

*bahra* contra *aṭṭas* per dir «molt» és la diferència de manual entre el tachelhit i el rifeny, i
aquí surt sola: **138 a una banda i 0 a l'altra**, i 23 a l'altra i 0 a la primera. I
*wawal*/*wawar* és la mateixa l→r de la taula de variació, ara en forma de paraula sencera.

**Per què això val com a confirmació:** si la marca de varietats fos equivocada, aquesta partició
no existiria —sortirien les mateixes paraules a les dues bandes—, i si fos un artefacte del
model, no coincidiria amb el que la dialectologia amaziga diu de fa dècades. El biaix que sí que
hi ha, dit: les formes surten del nostre transcriptor, que és de tachelhit, i les del tarifit les
sent pitjor; però el biaix no inventa *quines* paraules es reparteixen desigualment.

Desat a `lexic_diferencial.tsv`.

### 13.6 El lèxic classifica, i es valida deixant-ne un fora

Mirar com de bé el lèxic separa els episodis que l'han fet seria trampa. La prova honesta és
refer-lo **sense** l'episodi que es vol classificar, cada vegada. Resultat:

    de fora de mostra, a les dues bandes: 20 de 22 ben classificats

I els dos que falten (ANDICHI CHAHID, OMAR BOUMZZOUGH, tots dos marcats tarifit) no surten
classificats al revés: surten **«al mig»**. Cap error de direcció.

Els tres de l'Atles central **no han participat mai** en el lèxic, de manera que són una prova de
fora de mostra de franc:

| | tachelhit/1000 | tarifit/1000 |
|---|---|---|
| els 11 tachelhit | 89–192 (mediana 153) | 16–38 |
| **els 3 de l'Atles central** | **61–106** | **28–37** |
| els 11 rifenys | 8–60 | 42–75 |

**Entremig, i tirant cap al tachelhit** — que és el que el tamazight de l'Atles central fa. I en
Mouhib, amb la puntuació lèxica més baixa dels no-rifenys (61), és també el que menys acord tenia
dels no-rifenys (15,1 %): dues mesures independents el posen al mateix lloc del continu.

Tres mètodes que no comparteixen cap dada —les paraules del presentador, dues marques fonètiques
i el lèxic— diuen el mateix, i el tercer es valida sol.

### 13.7 El que l'orella rifenya pot i no pot provar

`iukocha/mms-tachebdant-from-tarifit` té **WER 0,7191** declarat a la seva targeta, després de
**200 passes** d'entrenament. És una orella fluixa, i això decanta la prova cap a un sol costat:

- **si tot i ser tan fluixa supera el nostre `shi` als episodis rifenys**, la hipòtesi queda molt
  reforçada: voldria dir que allà la llengua li és pròpia i al nostre no;
- **si no el supera, no es pot concloure gran cosa.** Un model dolent que falla no diu res de la
  llengua, només d'ell mateix.

O sigui que aquesta prova pot **confirmar** però gairebé no pot **desmentir**. Val més dir-ho
abans de veure el número que explicar-lo després.

El control que distingeix «el model no serveix» de «aquells convidats no són rifenys»: si dona
~0 % a **tot arreu**, també als dos episodis de tachelhit, és que està trencat i la prova no
compta. I es mira si el que escriu són paraules rifenyes plausibles o soroll.

També cal dir una esmena tècnica feta abans de córrer, no després: aquell model escriu en
**ortografia llatina del tarifit** (`ə ā č ŋ ç ɛ ɣ`), i el nostre esquelet no coneixia la `ə`,
que és una **vocal**. Sense arreglar-ho l'hauria comptada com a consonant i el rifeny hauria
sortit pitjor del que és per un error meu. La `č` —la palatalitzada que correspon a la `k`
estàndard— es mesura de les dues maneres, estricta i indulgent, perquè triar-ne una seria decidir
la prova per endavant.

### 13.8 L'índex, partit per varietat (que és el que calia des del principi)

Barrejar tres llengües en un índex és el mateix error que barrejar-les en un promig d'acord.
Partit (`index_paraules_tachelhit.tsv`, `_tarifit.tsv`, `_atles.tsv`):

| varietat | formes | acordades | nucli (2+ vegades, 2+ boques) |
|---|---|---|---|
| tachelhit | 18.872 | 2.726 | **490** |
| tarifit | 17.573 | 804 | **91** |
| Atles central | 5.303 | 769 | **80** |

El nucli rifeny és **91 contra 490**, i no perquè hi hagi menys matèria (7,67 h contra 7,95 h):
perquè **l'orella no el sent**. Això posa número a què es guanyaria amb una orella del Rif —de
l'ordre de cinc vegades més vocabulari validat de les mateixes vuit hores.

I el cap de cada llista confirma la partició pel seu compte: al tachelhit hi ha *bahra*(51),
*tirra*(49), *tskla*(44); a l'Atles central *nnḫ*(10) i *uẓawan*(7); al tarifit, poc i amb
formes diferents. L'índex de l'Atles central rendeix igual que el tachelhit per línia (769 de
2.010 contra 2.726 de 6.704), o sigui que **aquelles dues hores són tan bones com les altres
vuit**.

### 13.9 La ronda, ara que sabem de quina llengua és cada tall

| | tachelhit | Atles central | tarifit |
|---|---|---|---|
| **train** | 1.268 (75,6 %) | 329 (19,6 %) | **81 (4,8 %)** |
| **dev** | 134 | 25 | 12 |
| **test** (quatre retinguts sencers) | 573 | — | 554 |

La predicció deixa de ser una intuïció i passa a ser aritmètica: el train porta **81 talls de
tarifit**, uns sis minuts de so. Que els dos capítols rifenys retinguts millorin amb això no seria
raonable. **I si milloressin voldria dir una cosa gran:** que el guany és de domini —el programa,
el micròfon, el registre, la manera de parlar davant d'una càmera— i no de llengua.

El test va equilibrat gairebé exacte (573 talls de tachelhit contra 554 de tarifit) i això no ho
vaig dissenyar sabent les varietats: va sortir de triar «dos que l'orella entén i dos que no».
Quatre hores després s'ha vist que aquella tria era la tria de la llengua.

I els 329 talls de l'**Atles central** al train són més dels que esperava, i són de la varietat
que aquest projecte documenta.

### 13.10 La variació dins de cada varietat, i dues esmenes al que vaig dir

Separada per varietat, la taula de variació deixa de barrejar llengües:

**tachelhit (19 parelles)**

| escrit | formes sentides | canvi |
|---|---|---|
| ⵏⵏⵖ | nnḫ(11) / nnġ(8) | ḫ~ġ |
| **ⵏⵏⴽ** | **nnk(9) / nnš(7)** | **k~š** |
| ⵜⵎⴷⵢⴰⵣⵜ | tmdyazt(14) / tmdyast(3) | z~s |
| ⵜⴰⴹⴼⵉ | taḍfi(11) / taṭfi(3) | ḍ~ṭ |

**Atles central**: 1 parella (nnḫ/nnġ). **tarifit**: 3, i poques perquè allà l'orella no hi
arriba.

**Esmena 1.** Vaig dir que la k→š era del rifeny i que el tachelhit no en feia. No és així: a la
paraula ⵏⵏⴽ el Sus diu *nnk* 9 vegades i *nnš* **7**. El que canvia entre varietats és el **grau**
(1,8 % / 5,7 % / 12,1 %), no la presència. El discriminador fort és l'**l→r** (1 % contra 13 %);
la k→š és una gradació, i la frase «cap de les dues → tachelhit» de §13.4 s'ha de llegir així.

**Esmena 2.** El mètode pot confondre **dues paraules diferents** amb una variant: ⵜⵎⴰⵣⵉⵖⵜ es sent
*tmazirt* 3 vegades, i *tamazirt* («el país») i *tamaziġt* («la llengua») no són la mateixa
paraula amb una consonant canviada — són dues paraules que es diferencien en una consonant. El
filtre d'«un sol canvi» no ho pot veure, i per aquí entra brossa que sembla fonètica i és lèxica.

### 13.11 El corpus de grau A, partit i utilitzable

`corpus_grau_a_tachelhit.jsonl`, `_atles.jsonl`, `_tarifit.jsonl`:

| varietat | rèpliques | durada | episodis |
|---|---|---|---|
| tachelhit | 1.738 | **1,77 h** | 11 |
| **amazic de l'Atles central** | 354 | **18 min** | 3 |
| tarifit | 98 | 4 min | 11 |

Les 354 de l'Atles central són la **varietat que aquest projecte documenta**, amb so, tifinag i
català alineats:

    ⴳ ⵓⵏⵎⵓⴳⴳⴰⵔ ⵡⵉⵙⵙ ⵙⵉⵏ   ·   g unmuggar wissin   ·   «A la segona temporada»

I els 4 minuts de tarifit, contra les 7,67 hores que n'hi ha, tornen a dir el mateix per tercera
vegada: **el material hi és, l'orella no.** Això és el que la prova de l'orella rifenya ha
d'obrir.

## 14. Correcció important: l'orella els sent, el que no casa és el subtítol

Mirant una línia de l'episodi de Khbiza (0,4 % d'acord) ha sortit una explicació que havia
descartat massa de pressa:

    tifinag  ⵎⴽⵍⵍⵉ ⵜ ⴷⵍ ⵖⵔ ⵏⵎⴰⵍⵍⵓ, ⵉⵛⵇⴰ ⴰⴷ ⵏⴰⵍ ⴽⵔⴰ ⵏ ⵜⵔⵉⵍⵉⵜ ⴳⵉⵙ
    català   Tal com vaig entrar al sindicat, és difícil trobar-hi una dona
    shi      nnaqaba … tadišt n tarifšt
    rifeny   nnaqaba … tadhišt n tarifəšt

Les **dues** orelles senten *nnaqaba* (النقابة, el sindicat) i *tadišt* (dona), i això és el que
diu el català. El tifinag diu el mateix amb **paraules diferents**: *išqa* on l'orella sent
*təqsəḥ*, i *trilit* on sent *tadhišt*.

El tercer testimoni que ho separa són **els arabismes**: una paraula àrab que el convidat diu
surt també al subtítol àrab, amb les seves consonants.

| varietat | casa amb l'àrab | casa amb el tifinag | raó |
|---|---|---|---|
| tachelhit | 2,4 % | **38,3 %** | 0,06 |
| Atles central | 4,6 % | 31,6 % | 0,15 |
| **tarifit** | **3,8 %** | **12,8 %** | **0,30** |

Als episodis rifenys l'orella encerta arabismes **igual o millor** que als tachelhit —`lftra`
(الفترة), `ljmεiya` (الجمعية), `lḥark` (الحركة), `lεml` (العمل), tots confirmats per l'àrab— i en
canvi casa amb el tifinag tres vegades menys.

**Desdita:** «el model no entén aquells parlants» era massa fort. L'orella els sent, almenys en
part; el que no casa és el **subtítol**, perquè està escrit en la norma de l'IRCAM i per al
rifeny la norma canvia el vocabulari sencer, no només la fonètica.

**El confós, dit:** el parlant rifeny fa servir més arabismes que el del Sus, i això sol ja
inflaria la columna de l'àrab sense que l'orella hi senti millor. L'arabisme prova que l'orella
produeix alguna cosa reconeixible, no que entengui les paraules amazigues.

**I la predicció que ho decideix, escrita abans de córrer:** si l'orella rifenya casa amb el
tifinag **millor** que la nostra als episodis del Rif, el límit era l'orella. Si hi casa **igual
de malament**, el límit és la norma i cap orella no ho arreglarà — i llavors aquelles 7,67 hores
no són parelles de transcripció sinó de **traducció** (parla rifenya → tifinag estàndard), que és
una altra cosa i també serveix.

### 14.1 El diccionari norma ↔ rifeny encara no es pot treure, i se sap per què

Si el subtítol dels episodis rifenys és una traducció, allà on l'ull i l'orella diuen paraules
**completament diferents** hi ha la parella de traducció (`ⵜⵔⵉⵍⵉⵜ` escrit, *tadhišt* dit). Buscades
com el que són —distància **gran**, no petita— i amb les dues condicions de sempre (ancoratge pels
dos costats i repetició en dues boques):

    parelles llunyanes mirades       6.467
    ancorades pels dos costats           6
    que es repeteixen en 2+ boques       0

**No es pot treure, i la raó és aritmètica i no mala sort:** ancorar demana que els dos veïns
casin, i als episodis rifenys el tifinag casa el 12,8 % de les vegades. La probabilitat de tenir
dos encerts seguits és d'un 1,6 %, i encara menys perquè els encerts s'agrupen.

Això fa la prova de l'orella rifenya **doblement important**: no és només per confirmar la
varietat. És la clau que faria possible el diccionari — si puja el ritme d'encerts locals, les
àncores apareixen i les parelles de traducció cauen soles.

### 14.2 El sostre de l'acord no el posa la nostra orella: el posa el subtitulador

Les parelles ancorades dels episodis **tachelhit** són poques (27 de 10.809 candidates, cap
repetida en dues boques) però totes diuen el mateix:

| escrit a la norma | dit pel convidat | què és |
|---|---|---|
| ⵓⵎⴰⵡⴰⵍ *amawal* | **lmuεjam** | المعجم, «lèxic» |
| ⴰⵎⵣⵔⵓⵢ *amzruy* | **ttariġ** | التاريخ, «història» |
| ⵜⵓⴼⵔⴰⵢⵉⵏ *tufrayin* | **lmašaεir** | المشاعر, «sentiments» |
| ⵜⴰⵣⴷⴰⵢⵜ *tazdayt* | **lεalaqad** | العلاقة, «relació» |
| ⵜⵎⵙⵙⵓⵔⵉⵏ | **lasuṣit** | *l'association* |
| ⵉⵙⵎⵓⵜⴳⵏ | **tkwinat** | تكوينات, «formacions» |

**El subtítol escriu el neologisme de l'IRCAM i el convidat diu el manlleu àrab o francès.** No és
una variant fonètica ni un error: és el subtitulador normalitzant, i passa també al tachelhit.

El filtre de repetició no les salva perquè cada neologisme surt poques vegades, però **la classe
es repeteix** i té 27 casos documentats. I la conseqüència va més enllà del rifeny: **el sostre
de l'acord no el posa la nostra orella, el posa el subtitulador.** Per això el tachelhit s'atura
al 38 % i no hi pujarà, per bo que es torni el model, perquè en aquelles línies el que s'escriu
no és el que es diu.

Això lliga amb el que ja sabíem des del 19-11 (§1 del `METODE.md`: el subtítol no és una
transcripció) i hi posa el mecanisme concret i mesurat: **normalització lèxica**, no només
ortogràfica.

### 14.3 El corpus de grau A està una mica esbiaixat contra els manlleus

Si el grau A es dona quan l'ull i l'orella casen, i no casen justament quan el convidat diu un
manlleu que el subtítol normalitza, el corpus de grau A ha de contenir **menys manlleus** del que
la gent diu. Mesurat als episodis tachelhit, sobre paraules segures de 4+ consonants:

| grau de la rèplica | paraules | són manlleu àrab |
|---|---|---|
| A | 3.450 | **2,1 %** |
| B | 4.487 | 2,2 % |
| C | 3.538 | **3,0 %** |

Raó A/C: **0,71**. El corpus de grau A representa els manlleus un **29 % menys** del que es parla.
No és un desqualificador —i és molt menys del que temia—, però un aprenent que només sentís
aquest corpus sentiria un amazic una mica més pur del real.

La compensació ja hi és i és la regla d'en Pablo del 19-11: **els que no són d'alta concordança
també es cataloguen**. Els graus B i C conserven els manlleus i són al magatzem; el biaix està
documentat i es pot corregir mostrejant-hi quan calgui.

## 15. L'orella rifenya: la resposta és que el límit és el subtítol

Sobre els deu episodis rifenys, 497 talls (sortida parcial de la passada local, ja concloent):

| orella | acord amb el tifinag |
|---|---|
| `shi` (tachelhit, la nostra) | **0,4 %** |
| rifeny (`iukocha/mms-tachebdant-from-tarifit`) | **0,4 %** |
| rifeny, lectura indulgent de la `č` | 0,4 % |

**Idèntic.** Una orella entrenada en rifeny escoltant parla rifenya no casa gens millor amb el
subtítol que la nostra de tachelhit. I això era el discriminant escrit per endavant a §14:

> si l'orella rifenya casa amb el tifinag **millor** que la nostra, el límit era l'orella; si hi
> casa **igual de malament**, el límit és la norma i cap orella no ho arreglarà.

**Igual de malament.** El límit és el subtítol. Aquelles 7,67 hores no s'obriran amb un model
millor, perquè el que hi ha escrit a la pantalla no és el que es diu: és la traducció a la norma
de l'IRCAM.

**La reserva, que ja era escrita abans:** aquell model és fluix (WER 0,72 declarat) i un resultat
nul d'un model fluix val poc tot sol. El que li dona pes és que va en la mateixa direcció que
dues mesures independents fetes abans — els arabismes (l'orella sent el contingut: 3,8 % als
rifenys contra 2,4 % als tachelhit) i els neologismes (*amawal* escrit, *lmuεjam* dit).

I el model **no** està trencat: escriu tarifeny de debò —*xmin* (quan), *dh* (a), *nni* (aquell),
*lwəqt* (el temps), *tarifəšt* (el rifeny)— i en una línia on la nostra orella també encerta,
totes dues senten *nnaqaba* (النقابة) i *tadhišt* (dona), que és el que diu el català.

### 15.1 Què vol dir per al que ve

1. **El rifeny no és un corpus de transcripció: és de traducció.** Parla rifenya amb el seu
   significat escrit en la norma. Serveix per entrenar un traductor parla→norma, no un
   transcriptor.
2. **El sostre del tachelhit (38 %) tampoc no és nostre**: és la mateixa normalització, més
   suau. Pujar-lo demanaria subtítols que transcriguin, i això no depèn de nosaltres.
3. **El que sí que depèn de nosaltres** és el que ja tenim: 2,14 hores de grau A on les dues
   lectures coincideixen, que són les línies on el subtitulador no va normalitzar res.

### 15.2 Les dues orelles contra el subtítol: 0,4 % contra 67,6 %

El número «el rifeny casa igual de malament que el tachelhit» tenia dues lectures que aquell
número sol no separa: (a) el subtítol està traduït i cap orella no hi pot casar, o (b) el model
rifeny és massa fluix i no casaria amb res. Es separen comparant **les orelles entre elles**.

Sobre els 527 talls dels episodis rifenys:

| | acord |
|---|---|
| el nostre `shi` contra el **subtítol** | **0,4 %** |
| el rifeny contra el **subtítol** | **0,4 %** |
| **`shi` contra el rifeny** | **67,6 %** |

Les dues orelles senten el mateix dues vegades de cada tres i cap no s'assembla al subtítol.
Això mata la lectura (b) —el soroll no coincideix amb ningú al 67 %— i mata també «el model no
entén aquells parlants». **El que queda fora és el subtítol.**

Al control de tachelhit: `shi`~ull 50 %, rifeny~ull 40 %, `shi`~rifeny 90 % (encara amb pocs
talls). Allà el subtítol **sí** que s'assembla al que es diu.

**La reserva, i no és menor:** els dos models **no són independents**. El rifeny és un afinament
del mateix `facebook/mms-1b-all` que fem servir, de manera que comparteixen la representació
acústica i part d'aquell 67,6 % és parentiu, no coincidència de testimonis. Que la diferència
sigui 0,4 contra 67,6 fa difícil que el parentiu ho expliqui tot, però **aquesta prova sola és
més feble del que sembla**.

El que la sosté és que va en la mateixa direcció que una mesura que **sí** que és independent:
les paraules sentides casen amb els **arabismes del subtítol àrab** (3,8 % als rifenys, més que
el 2,4 % dels tachelhit), i això el parentiu entre dos models no ho pot fabricar.

## 16. Què fer amb això

El fet nou de la nit, en una frase: **el subtítol de la SNRT és una traducció normalitzada, no
una transcripció**, i això es pot mesurar — 38 % d'acord al tachelhit, 31 % a l'Atles central,
0,4 % al tarifit, i les dues orelles coincidint entre elles al 67,6 % allà on cap no coincideix
amb la pantalla.

Això canvia què val cada cosa:

### 16.1 El que ja serveix tal com és

- **2,14 hores de grau A** (2.190 rèpliques amb significat): són justament les línies on el
  subtitulador **no** va normalitzar res, i per això les dues lectures hi coincideixen. És el
  train de la ronda que corre.
- **La marca de varietat dels 25 episodis**, amb tres senyals independents i validada deixant-ne
  un fora (20 de 22). Compleix el principi de varietat del projecte: ara cada frase sap d'on és.
- **L'índex per paraula partit per varietat**: 490 formes al nucli del tachelhit, 80 a l'Atles
  central, 91 al tarifit.
- **Les 17,68 hores senceres com a parelles de traducció** parla → norma, que és una altra feina
  i també útil (subtitulació, traductor), però que no s'ha de confondre amb transcripció.

### 16.2 El que es pot obrir, i com

**El tarifit (7,67 h) necessita una transcripció, i ara se sap que no la donarà cap model sol.**
Però les dues orelles hi coincideixen al 67,6 %, i això és un **pseudo-transcrit de consens**:
allà on dues orelles de bases diferents diuen el mateix, el més probable és que sigui el que s'ha
dit. Amb el significat que ja tenim de l'àrab i del català, això dona un corpus rifeny de
**grau C** (no verificat, però catalogat), que és exactament el que el mètode mana fer amb el que
no és d'alta concordança.

El pas que el verificaria no és tècnic: és **una persona del Rif llegint cent línies**. Amb cent
línies corregides es pot mesurar quant val el consens, i llavors les vuit hores passen a grau A o
es queden a C amb un número al costat.

### 16.3 El que no val la pena intentar

- **Millorar l'orella per pujar l'acord als episodis rifenys.** Mesurat: no és l'orella. Una
  orella rifenya hi fa exactament el mateix 0,4 %.
- **Esperar que el tachelhit passi del 38 %.** El sostre el posa la normalització lèxica del
  subtitulador (*amawal* escrit, *lmuεjam* dit), i això no és un defecte del nostre sistema.

### 16.4 La pregunta oberta que més val

Dels 25 episodis n'hi ha 3 de l'**Atles central** (2,07 h, acord 19,3 %), que és la varietat que
aquest projecte documenta. Són pocs, i la biblioteca de la SNRT en té 954 capítols de sèrie. **La
pregunta que val la pena és quants dels altres són de l'Atles central**, i ara es pot respondre
sense veure'ls: el classificador per lèxic encerta 20 de 22 de fora de mostra i només necessita
el so i el subtítol.

### 15.3 El control que ho tanca: 26,6 % en una llengua que no és la seva, 0,4 % en la seva

Passada sencera (Kaggle, 639 talls en 172 s, marca comprovada):

| | el nostre `shi` | el rifeny |
|---|---|---|
| als 2 episodis **tachelhit** (109 talls) | 37,6 % | **26,6 %** |
| als 10 episodis **rifenys** (527 talls) | 0,4 % | **0,4 %** |

El model rifeny arriba al **26,6 %** d'acord amb un subtítol en tifinag estàndard **escoltant
parla del Sus, que no és la seva varietat**. O sigui que no està trencat: sap casar amb un
subtítol quan el subtítol diu el que es parla. I escoltant **la seva pròpia varietat** cau al
0,4 %.

Això mata l'última objecció que quedava —«un model fluix falla contra qualsevol cosa»—: el mateix
model, el mateix dia, els mateixos talls de quatre segons, fa 26,6 % en una llengua que no és la
seva i 0,4 % en la seva.

**La predicció escrita a §13.7 i §14 es compleix a mitges, i la meitat que falla és la meva
hipòtesi:**

    al tarifit:   shi 0,4 % · rifeny 0,4 %   ->  NO compleix («el rifeny ha de ser millor»)
    al tachelhit: shi 37,6 % · rifeny 26,6 % ->  compleix («ha de ser pitjor»)

La hipòtesi que el límit era l'orella queda **refutada per la prova que jo mateix havia dissenyat
per confirmar-la**. El límit és el subtítol: als episodis rifenys està escrit en una varietat que
no és la que es parla, i per això no hi ha model que hi pugui casar.

I la rèplica GPU–CPU: la passada de Kaggle i la local sobre els mateixos talls donen el mateix
0,4 % als rifenys, que és la comprovació que el camí de casa no tenia cap error.

### 15.4 Una tercera orella, de base diferent, i una rèplica exacta

**El testimoni independent.** L'objecció del parentiu (el model rifeny és un afinament del mateix
MMS que fem servir) es tanca amb `maghreb-ai-research/whisper-small-tarifit`: arquitectura
diferent (codificador-descodificador, no CTC), base diferent, entrenament diferent, ortografia
diferent (àrab de xat, amb 9=q i 7=ḥ). I sent les **mateixes paraules**:

    MMS rifeny   nnaqaba s-gudhəfitəqsəḥbəša  tadhišt n tarifəšt
    Whisper      naqaba   sogdfit y9s7b7      tabicht   tarifest
    subtítol     ⵎⴽⵍⵍⵉ ⵜ ⴷⵍ ⵖⵔ ⵏⵎⴰⵍⵍⵓ, ⵉⵛⵇⴰ ⴰⴷ ⵏⴰⵍ ⴽⵔⴰ ⵏ ⵜⵔⵉⵍⵉⵜ ⴳⵉⵙ
    català       …és difícil trobar-hi una dona

Tres orelles que no comparteixen base senten *naqaba*, *tarifest*, *tabicht*; el subtítol diu una
altra cosa. El parentiu ja no explica res.

Nota de camí: aquell diposit porta el `generation_config.json` amb la llengua a `None`, i el
model es posava a endevinar-la —sortia kannada i devanagari. El `config.json` **sí** que la porta
(`forced_decoder_ids` amb el token 50265, el del **francès**: l'afinament va fer servir la casella
del francès per al rifeny). Forçant-la, escriu rifeny.

**La rèplica.** El model rifeny es va passar dues vegades pels mateixos 639 talls per motius
diferents (a casa perquè la cua de GPU no es movia, i a Kaggle quan es va alliberar). Les dues
sortides són **idèntiques al 100 %**: mateix text exacte als 639 talls, en CPU i en GPU. Cap dels
dos camins no té cap error, i això ha sortit de franc per haver fet la mateixa cosa dues vegades.

### 16.5 El corpus rifeny per consens, amb número

Sobre la mostra de 527 talls dels episodis rifenys, les dues orelles (el nostre `shi` i el model
rifeny) coincideixen en **356 (67,6 %)**, i totes 356 tenen significat del català.

Projectat a les 6.651 rèpliques rifenyes (7,67 h):

    ~4.492 rèpliques amb transcripció de consens i significat  ·  unes 5,2 hores

Seria corpus de **grau C**: no verificat, però catalogat i amb un número al costat, que és el que
el mètode mana fer amb el que no és d'alta concordança. I el que el pujaria a grau A **no és
tècnic**: cent línies llegides per algú del Rif donarien la mesura de quant val el consens, i
llavors aquelles cinc hores tindrien un valor conegut en comptes d'una esperança.

Per fer-lo de debò calen les tres orelles sobre els 3.517 talls de `prova_dolents` (300 per
episodi), que ja són pujats a Kaggle amb el nucli escrit i esperant una sessió de GPU.

### 15.5 El Whisper, quantificat: 35,8 % amb la nostra orella i 0,0 % amb el subtítol

64 talls repartits entre tots els episodis (un de cada deu de la mostra):

| | Whisper ~ subtítol | `shi` ~ subtítol | **Whisper ~ `shi`** | Whisper ~ MMS rifeny |
|---|---|---|---|---|
| episodis rifenys (53 talls) | **0,0 %** | **0,0 %** | **35,8 %** | 20,8 % |
| control tachelhit (11 talls) | 9,1 % | 36,4 % | 27,3 % | 36,4 % |

Als episodis rifenys el Whisper i la nostra orella coincideixen entre elles el **35,8 %** i amb el
subtítol el **0,0 %**. I el Whisper no comparteix res amb l'MMS: ni arquitectura
(codificador-descodificador contra CTC), ni base, ni entrenament, ni ortografia. **L'objecció del
parentiu queda tancada.**

**Les reserves, totes dites:** són 53 talls (±7 punts); la normalització de l'àrab de xat
(9→q, 7→ḥ, ch→š…) és meva i aproximada, i deprimeix totes les xifres del Whisper —per això fa
només 9,1 % contra el subtítol al control on el `shi` fa 36,4 %—; i d'aquell model no se'n publica
cap WER. Però la comparació que importa és **interna i sobre els mateixos talls**: dues orelles
que no comparteixen res s'assemblen entre elles i no a la pantalla.

### 15.6 La cadena de proves, sencera

| prova | resultat | què descarta |
|---|---|---|
| l'àrab del subtítol (arabismes) | 3,8 % als rifenys contra 2,4 % als tachelhit | que l'orella no senti |
| el model rifeny al tachelhit | **26,6 %** | que el model rifeny sigui soroll |
| el model rifeny al tarifit | **0,4 %**, igual que el nostre | que el límit sigui l'orella |
| `shi` contra el rifeny | 67,6 % | — (parentiu de bases) |
| **Whisper contra `shi`** | **35,8 %**, amb 0,0 % contra el subtítol | el parentiu |
| CPU contra GPU, mateix model | **100 % idèntic** | que el nostre camí tingui un error |

Cinc mesures independents i una rèplica exacta. **El subtítol dels episodis rifenys no diu el que
es parla**, i això no és una avaria de res: és com es fan els subtítols.

## 17. Auditoria dels números de la nit

Tornats a comptar directament dels fitxers, sense fer servir els guions que els van produir:

| el que he dit | el que surt |
|---|---|
| rèpliques al corpus: 15.365 | 15.365 ✓ |
| capítols: 25 | 25 ✓ |
| hores: 17,68 | 17,68 ✓ |
| tachelhit 11 · Atles 3 · tarifit 11 | igual ✓ |
| acord tachelhit: 27,2 % | **27,1 %** |
| acord Atles central: 19,3 % | 19,3 % ✓ |
| acord tarifit: 1,6 % | 1,6 % ✓ |
| grau A amb significat: 2.190 (2,14 h) | 2.190, 2,14 h ✓ |
| paraules de grau A: 6.779 | 6.779 ✓ |
| ocurrències: 75.747 | 75.747 ✓ |
| lèxic diferencial: 156 formes | 156 ✓ |
| variants: 97 | 97 ✓ |

Una sola diferència, de **0,1 punt**: vaig dir 27,2 % i el recompte directe dona 27,1 %, perquè
l'un divideix per les línies amb text i l'altre per les rèpliques graduades. No canvia cap
conclusió, però val més dir-ho que arrodonir cap on convé.

### 15.7 L'últim confós: l'ull llegeix igual de bé les tres varietats

La quantitat de text de cada rèplica la marca l'àrab, que és una lectura independent i mesurada
(CER 0,0059). Si als episodis rifenys l'ull perdés text, l'acord baixaria sense que el subtítol
hi tingués res a veure.

| varietat | lletres amazigues per caràcter àrab | rèpliques mudes |
|---|---|---|
| tachelhit | 1,038 | 1,4 % |
| Atles central | 1,015 | 2,5 % |
| **tarifit** | **0,910** | **1,1 %** |

Un **12 %** menys de text per caràcter àrab, i **menys** rèpliques mudes que als tachelhit. Un
12 % no pot explicar que l'acord caigui del 37,6 % al 0,4 %, i aquell 12 % fins i tot encaixa amb
l'explicació de la traducció: una traducció pot ser més curta que l'original.

Amb això queden tancats tots els confosos que se m'han acudit en tota la nit.

## 18. De quina varietat és el Baba Ali (predicció escrita abans del resultat)

El classificador per lèxic **només necessita el que sent l'orella**, no el tifinag — i al Baba Ali
el tifinag gairebé no es llegeix (39 a 113 línies amb text per episodi). O sigui que es pot
classificar una sèrie sencera sense subtítol amazic llegible, i això val perquè **el Baba Ali són
30 episodis**: unes 7.500 rèpliques.

Fet aquesta nit: 240 talls de quatre episodis (60 per episodi, només rèpliques amb significat i
d'1 a 12 s), tallats dels vídeos d'aquí amb les marques de temps del visor, i passats per **la
nostra orella amb l'adaptador afinat** — la mateixa condició que els 25 capítols de Tadfi, perquè
comparar sortides de dos models diferents faria que la diferència fos del model i no de la
varietat.

**El que espero:** és una comèdia de situació, no una entrevista literària, i la llengua hi serà
més col·loquial i amb més manlleus. Dels tres resultats possibles:

- **tachelhit** → el projecte guanya 30 episodis de la varietat que ja domina;
- **Atles central** → guanya el que més li falta;
- **«al mig»** → el classificador necessita més matèria de la que té, i caldrà dir-ho.

Per comparar, els marges de fora de mostra dels episodis de Tadfi:

    tachelhit       89-192/1000 de formes del tachelhit · 16-38 del tarifit
    Atles central   61-106/1000                         · 28-37
    tarifit          8-60/1000                          · 42-75

### 18.1 Aturat per falta de memòria, amb una lectura provisional

El sistema va aturar la passada local quan en portava **50 talls de 240**: carregar l'MMS-1b-all
a la CPU són uns 4-8 GB de RAM i la màquina es va quedar curta (després hi havia 6,4 GB lliures
de 17,9, o sigui que va ser un pic). No es torna a engegar sense demanar-ho.

Lectura provisional amb el que va quedar fet, i **no n'hi ha prou per concloure**:

    baba_ali_02   114 paraules   sh 61,4/1000   rf 0,0/1000

Aquell 61,4 cau a la **frontera** entre el tachelhit (89-192) i l'Atles central (61-106), i el
0,0 de formes rifenyes és per sota de totes dues franges —amb 114 paraules i 39 formes rifenyes
al lèxic amb prou feines hi ha ocasió de topar-n'hi cap. Un sol episodi i un sisè de la mostra no
decideixen res.

El que sí que es pot dir és qualitatiu i va on s'esperava: molts manlleus (*ṣṣuġf*, *lḫaṭrin*,
*yalah*), com toca a una comèdia, i hi surt *lliġ*, que és del costat tachelhit del lèxic. **No
sembla rifeny**, i la resta queda pendent dels 190 talls que falten.

Per reprendre-ho: `talla_baba_ali.py` ja té els 240 talls tallats i `orella_nostra.py` els passa
amb l'adaptador afinat. A la GPU de Kaggle seria un minut; en local, uns quinze i amb la memòria
justa.

## 19. La ronda: el cercle es tanca per primera vegada

    recepta B · 4 èpoques · ritme 1e-4 · seed 42 · parteix de l'adaptador que serveix avui
    train 3.090 talls (3,14 h): 1.669 del grau A + 1.421 de Zouhir · dev 169 · fuita treta 16

**El número que justifica tota la feina del corpus:** el filtre de qualitat del nucli (CER ≤ 0,4
contra l'adaptador actual) deixa passar **1.341 de 1.669 talls (80 %)** i la CER mediana del train
és **0,286**. El 17 de novembre, amb el text sense triar, aquell mateix filtre passava el **0,9 %**
(4 de 466) i la mediana era **0,83**. La diferència no és un model millor: és comparar **esquelets
de consonants** en comptes de text amb vocals contra un subtítol que no les escriu.

### Les cinc proves, amb interval de confiança (remostreig de 1.000 vegades)

| prova | Δ CER | interval 95 % | |
|---|---|---|---|
| snrt-retingut | −0,0133 | [−0,0196, −0,0073] | **millora** |
| zouhir-tests | −0,0128 | [−0,0177, −0,0080] | **millora** |
| test-fora (parla nostra mai sentida) | −0,0121 | [−0,0240, −0,0025] | **millora** |
| cv-zgh-test (256 clips nets) | −0,0023 | [−0,0069, +0,0023] | no es pot dir |
| tfa-226 | +0,0026 | [−0,0025, +0,0079] | **no empitjora** |

La regla, llegida al codi (`cercle_virtuos.py:122`) i no de memòria:

    adopta = not absents and not empitjora and len(millora) >= 2
    empitjora = límit BAIX de l'interval > 0  ·  millora = límit ALT < 0

Cap prova no empitjora (el límit baix més alt és −0,0025), tres milloren, les cinc hi són:
**`adopta = True`**. És la primera ronda del cercle que passa la seva pròpia regla.

**Llegit a punts hauria dit el contrari.** La meva primera lectura va dir «quatre milloren i una
empitjora, la regla no es compleix», perquè vaig comparar punts. La regla demana interval
justament per això: el +0,0026 del tfa-226 no és un empitjorament, és soroll.

### Els quatre capítols retinguts, un per un — i la predicció

| capítol retingut | talls | abans | després | canvi |
|---|---|---|---|---|
| **Akounad** (tachelhit) | 284 | 0,5768 | 0,5392 | **−0,0376** |
| **Zahour** (tachelhit) | 289 | 0,6955 | 0,6592 | **−0,0363** |
| Abarnous (tarifit) | 275 | 0,8271 | 0,8272 | +0,0001 |
| Khbiza (tarifit) | 279 | 0,9072 | 0,9389 | **+0,0317** |

La predicció escrita a §12.9 era: **milloren els dos de tachelhit i no es mouen els dos de
tarifit**. Els dos de tachelhit milloren 3,6 i 3,8 punts de CER en capítols **sencers i mai
vistos**; l'Abarnous no es mou (+0,0001); i el Khbiza **empitjora 3,2 punts** — més del que havia
dit, i és informació de més: entrenar amb dades de tachelhit fa el model una mica **pitjor** amb
un parlant rifeny. Que és el que ha de passar si són llengües diferents, i és una confirmació de
§13 que ve d'un lloc completament distint.

### Tres coses que s'han de dir

1. **Els intervals són meus**, no de l'orquestrador del cercle: remostreig sobre les mateixes
   frases abans i després, 1.000 vegades. La regla és la del codi. L'únic número a la frontera és
   el cv-zgh (límit alt +0,0023); si l'interval del cercle el posés per sota de zero, només
   pujaria el compte de millores de 3 a 4, i la condició de rebuig no depèn d'ell.
2. **Adoptar M₁ és una decisió teva**, no meva. El model és de recerca i no es desplega enlloc
   (`docs/PERMISOS.md`); el que diu la regla és que *qualifica*.
3. **La ronda que ha corregut és la de les 04:36, no la de les 03:13.** Vaig deixar viu un guió de
   cua que tornava a llançar-la quan s'alliberés GPU, i a les 04:35:59 ho va fer: va substituir la
   que ja portava una hora i vint. El resultat és vàlid (mateixes dades, passada completa de 68
   minuts), però la primera hora i vint es va perdre per un descuit meu.

## 20 · El matí del 20: provar-ho tot fora del SNRT

Tot el que vaig trobar la nit del 19 al 20 surt del mateix lloc —material de la SNRT, llegit pel
nostre ull i sentit per la nostra orella— i això vol dir que podia estar mesurant una manya del
sistema i no una propietat de la llengua. En Pablo ho va dir amb una frase: «mira de validar el
que has après amb altres parts del nostre catàleg». Tres proves, totes amb material d'una altra
procedència, i una que em desdiu.

### 20.1 · El sostre el posa el subtitulador: confirmat quatre vegades

El mateix codi, la mateixa orella, la mateixa mesura. L'únic que canvia és **qui escriu la
referència**:

| referència | què és | acord d'esquelet | CER esq. mediana |
|---|---|---|---|
| zouhir-tests | rètols transcrits a mà | **71,9 %** | 0,000 |
| cv-zgh-test | frases escrites i després llegides | 67,9 % | 0,000 |
| tfa-226 | transcripció humana | 61,4 % | 0,000 |
| test-fora | parla nostra, mai sentida | 52,4 % | 0,200 |
| snrt-retingut | **subtítol en norma de l'IRCAM** | **23,1 %** | 0,667 |

La predicció escrita abans de mesurar-ho deia «molt per sobre del 38 %, cosa de 70 % amunt». Es
compleix. El número que més diu no és el percentatge sinó la **mediana zero**: contra veritat
humana, la paraula del mig casa exacta.

El que això no treu: aquestes proves també tenen so més net. Per això hi ha la fila de
`test-fora` —parla nostra, gravada al camp, mai sentida pel model— que treu 52,4 %, més del
doble que el SNRT.

### 20.2 · Què compra el grau A: la meva predicció, refutada

El llindar de 0,35 decideix tot el corpus de la ronda, i al SNRT no es pot comprovar: no hi ha
veritat humana i l'únic jutge és el mateix parell que vull jutjar. A les proves amb veritat
humana sí (3.872 parelles de paraula):

| llindar | passen | precisió (esquelet) | precisió (text ric) | record |
|---|---|---|---|---|
| 0,35 (el de la ronda) | 76,7 % | **74,4 %** | 66,7 % | 99,7 % |
| 0,25 | 68,9 % | 82,9 % | 74,4 % | 99,7 % |
| **0,15** | 57,5 % | **99,2 %** | 89,0 % | **99,7 %** |
| 0,00 | 57,1 % | 100,0 % | 89,7 % | 99,7 % |

Havia escrit «espero una precisió d'esquelet molt alta (>90 %) a 0,35». **És 74,4 %**: una de
cada quatre paraules que el filtre accepta no és la paraula.

I el que surt a canvi val més que el que esperava: **el record no es mou**. Estrenyent de 0,35 a
0,15 es conserven el 99,7 % de les paraules exactament correctes i desapareixen el 97,6 % de les
dolentes (760 → unes 18). El salt és entre 0,25 i 0,15, perquè amb paraules de 3 a 6 consonants
un llindar de 0,15 ja vol dir «esquelet idèntic»: la decisió de debò no és un número, és
**idèntic o no**.

El que s'hi cola a 0,35 no són paraules diferents: `uggar`~`ugar` (tensa), `yudf`~`yuḍf`
(emfàtica), `uzrak`~`uzrag` (sonora), `jar`~`injar` (un clític enganxat). Per a l'índex de
fiabilitat això és material; per a una etiqueta d'entrenament és una consonant equivocada.

**Per a la ronda 2:** el train s'ha de triar amb esquelet idèntic. Es perd un 20 % de talls i no
es perd ni una paraula bona.

### 20.3 · El lèxic de varietats, provat fora i contra l'atzar

El lèxic diferencial surt del SNRT, es jutja amb episodis del SNRT i el sent la mateixa orella.
Per sortir del cercle: el manifest de la biblioteca (6.628 gravacions) porta text escrit per
**persones** i una etiqueta de varietat que no ha sortit mai de cap mesura meva.

Primer intent: zero formes trobades al grup `shi`, de 9.278 paraules. **Un zero absolut vol dir
que miro el camp equivocat**: aquelles files són en tifinag i el lèxic és en llatí de l'orella.
Refet per esquelet de consonants, que normalitza els dos alfabets:

| grup | paraules | del lèxic | sh/1000 | rf/1000 |
|---|---|---|---|---|
| `shi` (tifinag) | 9.278 | 2.480 | 213,0 | 54,3 |
| `tdl` (Beni Mellal + CD del Mètode) | 7.407 | 594 | 59,8 | 20,4 |
| `zgh` | 456 | 82 | 133,8 | 46,1 |

Cap grup no tira cap al rifeny, que és el que havia predit (a la biblioteca no n'hi ha). Però
això sol no prova res: podria ser que les formes «tachelhit» fossin només les paraules amazigues
més freqüents, i llavors qualsevol corpus del món sortiria igual. **Prova nul·la**: repartir els
22 episodis en dos grups a l'atzar, de les mateixes mides, fer el lèxic igual i mirar la raó.

    de debò:   184 i 69 formes · 2.635 i 721 apariacions · raó 3,65
    a l'atzar: mediana 1,05 · del 5 % al 95 % entre 0,44 i 2,45 · màxim 3,21 (200 repartiments)
    cap dels 200 no hi arriba — p = 0,005

El lèxic separa de debò. I com que a la biblioteca no hi ha ni una paraula de rifeny, la prova
només pot ensenyar un costat — cosa que és, ella mateixa, la raó per la qual aquelles 7,67 hores
del SNRT valen el que valen: **és l'únic tarifit que tenim.**

### 20.4 · I el que es dedueix d'una mesura no val per a l'altra

De 20.2 en vaig treure una recomanació: «el train de la ronda 2 s'ha de triar amb esquelet
idèntic; es perd un 20 % de talls i no es perd ni una paraula bona». **Estava malament, i
l'error és d'altura**: aquella mesura és per PARAULA i el train es tria per FRASE.

Mesurat per frase, sobre les mateixes 699 frases amb veritat humana:

| CER d'esquelet | frases | CER ric mitjà | CER ric mediana |
|---|---|---|---|
| idèntic (0,00) | 18,7 % | 0,063 | 0,048 |
| 0,00–0,10 | 21,5 % | 0,108 | 0,100 |
| 0,10–0,20 | 32,9 % | 0,166 | 0,156 |
| 0,20–0,35 | 19,0 % | 0,260 | 0,250 |
| 0,35–0,60 | 5,4 % | 0,477 | 0,417 |
| > 0,60 | 2,4 % | 1,007 | 0,900 |

i el que entraria al train segons el llindar:

| llindar | frases | CER ric mitjà de l'etiqueta |
|---|---|---|
| 0,35 (el de la ronda) | 92,3 % | 0,151 |
| 0,20 | 76,1 % | 0,127 |
| 0,10 | 43,6 % | 0,093 |
| idèntic | 18,7 % | 0,063 |

La predicció escrita abans deia que a 0,35 entrarien frases amb CER ric per sobre de 0,3. **No
hi entren**: la mitjana del que passa a 0,35 és 0,151, i el tram dolent (0,477) queda just a
fora. És la segona predicció que em falla aquest matí, i les dues en la mateixa direcció: **jo
espero que els llindars fluixos siguin pitjors del que són.**

El filtre, per frase, ordena molt bé: el CER ric puja de 0,063 a 1,007 de manera monòtona amb el
d'esquelet. Això és el que justifica el filtre, i no el percentatge de talls que passa.

**La recomanació bona per a la ronda 2** no és «esquelet idèntic» sinó un canvi mesurable:
provar 0,20, que conserva el 76 % de les frases i treu un 16 % de l'error de l'etiqueta
(0,151 → 0,127). I és això: una hipòtesi per provar amb una ronda, no una conclusió.

**La lliçó d'ofici** (METODE §16): una mesura feta a una altura no decideix a una altra. El
mateix llindar, el mateix corpus i el mateix dia donen «estrènyer és de franc» per paraula i
«estrènyer costa una quarta part del corpus» per frase.

### 20.5 · Les tres orelles sí que van córrer, i la tercera no era la que jo creia

Aquesta nit vaig dir que la feina de les tres orelles sobre els episodis rifenys «mai no va
trobar GPU». **Sí que va córrer**: a les 05:28, llançada pel mateix guió de cua que vaig
descuidar. Les tres orelles van sentir els 3.517 talls senceres.

Com s'assemblen entre elles, sobre el mateix so:

| parella | coincideixen (esquelet ≤ 0,35) |
|---|---|
| shi ~ kab | **71,4 %** |
| shi ~ rif | 68,4 % |
| kab ~ rif | **68,2 %** |

La predicció escrita deia: «`kab` i `rif` han de coincidir més entre ells, perquè el cabil i el
rifeny són llengües del nord i el tachelhit és del sud». **És just al revés.** La parella que més
coincideix és `shi`~`kab`, que és la que **comparteix el model base** (MMS-1b-all amb dos
adaptadors), i la parella que menys coincideix és la de les dues llengües més pròximes.

Això no és una curiositat: canvia què val el consens. Dues de les tres orelles no són dues
opinions, són **la mateixa màquina dues vegades**. Un consens shi+kab no és corroboració.

Amb la independència comptada bé:

| | talls | |
|---|---|---|
| les tres coincideixen (amb el `rif`, base independent) | 1.862 | 52,9 % |
| dues, i una és el `rif` | 962 | 27,4 % |
| dues, però `shi`+`kab` (mateixa base) | 198 | 5,6 % |
| cap parella no casa | 489 | 13,9 % |

**`corpus_consens_rifeny.jsonl`: 2.824 rèpliques amb suport independent i significat en català,
3,56 hores.** Les 198 de base compartida hi són marcades `independent: false`.

I una correcció del número que vaig donar anit: havia dit «unes 4.492 rèpliques (5,2 h)»
extrapolant d'un acord de dues orelles. Amb les tres i exigint independència són **2.824 (3,56
h)**. El número de la nit estava inflat un 59 %.

Cada orella per separat casa amb el subtítol entre el 4,7 % i el 6,3 %. Tres models diferents,
dues arquitectures i tres ortografies diuen el mateix que deia anit: **allò escrit no és allò
dit.**

Segueix sent **grau C**. Tres màquines que s'assemblen no són una persona que ho confirmi, i el
que convertiria aquest corpus en grau A no és tècnic: són cent línies llegides per algú del Rif.

### 20.6 · Les marques fonètiques són a la parla: replicat amb una orella sense parentiu

Anit les dues marques (k→š i l→r) les va mesurar la nostra orella comparant amb el subtítol. Si
l'adaptador `shi`, davant d'un so que no coneix, tendís a escriure `r`, la marca seria nostra.

Mesura nova, sense subtítol i sense alineament —les dues fonts de soroll—: **dins de cada
orella**, quina proporció de `r` hi ha sobre `l`+`r`, i de `š` sobre `k`+`š`, a cada episodi.
Comparar una orella amb ella mateixa entre episodis val encara que les dues escriguin diferent.

| | la nostra (`shi`) | la rifenya (altra base, altra ortografia) |
|---|---|---|
| tachelhit | r 51,6 % · š 19,1 % (11 ep.) | r **52,7 %** · š 23,8 % (2 ep.) |
| Atles central | r 50,0 % · š 29,9 % (3 ep.) | — |
| tarifit | r **67,6 %** · š 53,1 % (11 ep.) | r **66,6 %** · š 61,8 % (10 ep.) |

Dos models que no comparteixen ni base ni ortografia donen el mateix número. I **episodi a
episodi no hi ha cap solapament**: tots els tachelhit entre 49,1 i 55,0 % de `r`, tots els
rifenys entre 61,6 i 78,0 %. Separació perfecta sobre 22 episodis, i l'Atles central al mig per
tercera vegada.

Aquesta mesura és millor que la d'anit i l'hauria d'haver fet primer: no necessita que l'ull i
l'orella casin, que era justament el que no passa als episodis rifenys.

**Una cosa per mirar, no una conclusió:** dos episodis classificats com a tachelhit treuen una
`š` molt alta —`yjmvageehekczjwy` 51,6 % i `bueyrhjvjyaleocf` 44,9 %, contra 12-20 % de la
resta— amb una `r` normal (55,0 i 51,0). `š` alta amb `r` normal és el perfil de l'Atles
central, no del Rif. Les dues orelles coincideixen en l'anomalia de `bueyrhjvjyaleocf` (44,9 i
43,8), o sigui que no és soroll d'un model. **Val la pena tornar a mirar la varietat d'aquests
dos.**

### 20.7 · I la proporció que passa no es transporta

De §20.4 en va sortir: «provar 0,20, que conserva el 76 % de les frases». Aquell 76 % és de les
proves amb veritat humana. Al corpus del SNRT, que és el que es filtra de debò:

| llindar | talls amb significat | hores |
|---|---|---|
| 0,60 | 5.875 | 6,52 |
| **0,35** (la ronda) | **2.190** | **2,14** |
| 0,25 | 1.322 | 1,23 |
| **0,20** | **924** | **0,84** |
| 0,15 | 565 | 0,49 |
| idèntic | 109 | 0,07 |

**A 0,20 el SNRT conserva el 42 %, no el 76 %.** La distribució del SNRT està desplaçada cap a
la dreta precisament perquè el subtítol és una traducció: el mateix llindar talla molt més aquí.

El que SÍ que es transporta és la relació —més CER d'esquelet, més CER ric— i el que NO és la
proporció que passa. Una calibració diu **on tallar segons la qualitat que vols**; quant de
corpus et quedarà només ho diu el corpus que filtres.

Amb això, la ronda 2 ja no és una recomanació sinó una pregunta amb dos braços comparables:

    0,35 → 2.190 talls SNRT (el que ja s'ha corregut: Δ CER −0,0133 al retingut)
    0,20 →   924 talls SNRT, etiquetes millors

i es contesta corrent la MATEIXA recepta des de M₀ amb el corpus de 0,20. No cal adoptar M₁ per
fer-ho, i és l'única manera de saber si val la pena.

### 20.8 · Els dos episodis que no estan ben posats, i per què són precisament aquells

Els dos episodis amb `š` anòmala tenen nom, i no és casualitat quins són: **són els dos únics que
la regla de varietat va decidir pel criteri més feble**, «l'acord alt, perquè el presentador no
és concloent».

| episodi | com es va decidir | acord | `š` | `r` | lèxic sh/rf |
|---|---|---|---|---|---|
| SAID OU BOULMAN | l'acord alt | 41,7 % | 44,9 % | 51,0 % | **89,2** / 36,8 |
| MOHAMED EL GHAZOULI | l'acord alt | 34,7 % | 51,6 % | 55,0 % | 132,2 / 29,7 |
| tachelhit (els altres 9) | el presentador | — | 12–20 % | 49,1–55,0 % | 129–192 / 16–38 |
| Atles central (3) | el presentador | — | ~30–40 % | 50,0 % | 61–106 / 28–37 |
| tarifit (11) | el presentador | — | 47–57 % | 61,6–78,0 % | 7,7–60 / 42–75 |

`š` alta amb `r` normal és el perfil de **l'est sense ser del Rif**, que és on la §13 posa
l'Atles central. I el lèxic d'en Said Ou Boulman (89,2 sh/1000) cau **dins del marge de l'Atles
central** (61–106), no del tachelhit (129–192). Les seves mencions del presentador tampoc no
l'ajuden: rif 5, sus 4, atles 2.

**No els reclassifico amb això.** El que es pot dir amb honestedat és que de les 7,95 hores que
vaig comptar com a tachelhit, **dues episodis (SAID OU BOULMAN i MOHAMED EL GHAZOULI) no estan
fermament col·locats**, i que el primer té tres senyals que l'acosten a l'Atles central. Si ho
fos, les hores d'Atles central —la varietat que aquest projecte documenta— passarien de 2,07 a
unes 2,8.

Com es decidiria de debò: el mateix que per al rifeny, **algú que parli la llengua escoltant deu
minuts de cada episodi**. La màquina ja ha dit tot el que pot dir.

## 21 · Adoptar M₁ inflaria el filtre? (la prova, escrita abans del resultat)

En Pablo, quan li vaig demanar que decidís si adoptàvem M₁: «com sé jo quina resposta t'he de
donar, M té un biaix o no el té? com ho sabem». Té raó: no és una decisió, és una mesura que jo
no havia fet.

**El que ja sabíem.** La regla del cercle està feta contra aquest biaix: M₁ no es jutja amb el
subtítol del SNRT sinó amb proves on la veritat no en ve —rètols transcrits a mà, la nostra parla
gravada al camp, frases llegides— i hi millora amb interval (−0,0128 i −0,0121). Si M₁ només
hagués après a escriure com el subtitulador, aquelles no s'haurien mogut.

**El que no sabíem, dit amb precisió.** No «M₁ té biaix», sinó: **si la ronda 2 tria el corpus
amb l'oïda de M₁, el filtre s'infla?** M₁ ha vist 1.849 talls amb el text del subtítol com a
etiqueta; en aquells dirà el que posa la pantalla perquè l'hi han ensenyat.

**El disseny que no s'aguantava**, i val la pena que quedi escrit: volia aparellar cada tall vist
amb un de no vist del mateix capítol i amb el mateix CER de partida. **No es pot**: el train es va
endur *tots* els talls de grau A de cada capítol, o sigui que dins d'un capítol «vist» vol dir
«CER baix» i «no vist» vol dir «CER alt» per construcció. De 1.849 vistos només en sortien 337
parelles, totes al límit, i amb mitjanes que ja no coincidien (0,339 contra 0,380).

**El control bo ja existia i no costava cap GPU:** els quatre capítols retinguts. Els seus talls
de grau A són exactament «talls que casaven sota M₀ i que el model no ha vist mai», i M₀ i M₁ ja
hi han passat tots dos. L'únic que faltava era passar M₀ i M₁ pels 1.849 vistos.

    inflació = (quant baixa el CER als vistos) − (quant baixa als retinguts de grau A)

**El que la mesura no pot separar**, i que consta al resultat: els retinguts són capítols sencers
diferents, i a la diferència hi ha, a més de la memorització, el que separa uns capítols dels
altres. Per això la comparació principal és només amb els capítols **tachelhit** de les dues
bandes.

**La predicció, escrita al nucli abans de llançar-lo:** hi haurà inflació i serà gran, perquè
quatre èpoques amb lot petit són moltes passades per tall.

**I què farà cada resultat:**

| si surt | vol dir | la ronda 2 |
|---|---|---|
| interval que passa per zero | no hi ha inflació mesurable | pot sentir tot el SNRT |
| diferència clarament positiva | n'hi ha, i se sap quanta | ha de triar el corpus només del que M₁ no ha vist, i el preu són 1.849 talls |

(`prepara_inflacio.py`, `inflacio/sent_inflacio.py`, `puja_inflacio.py`, `mira_la_inflacio.py`.)

### 21.1 · El resultat, i un error meu pel camí

M₀ i M₁ sobre els 1.849 talls vistos (351 i 360 segons de GPU). Contra el control —els talls de
grau A dels capítols tachelhit retinguts—, i amb **les dues bandes passades pel mateix `rica()`**
del nucli, que és una cosa que vaig haver d'arreglar: el nucli de la ronda normalitza el text i
el meu el desava cru, i els nivells de CER no eren comparables encara que les baixades sí.

| grup | talls | CER M₀ | CER M₁ | baixa |
|---|---|---|---|---|
| vistos | 1.210 | 0,2019 | 0,1754 | −0,0265 |
| no vistos | 151 | 0,2219 | 0,2061 | −0,0158 |

**Inflació = +0,0103, interval 95 % [−0,0028, +0,0243]: passa per zero.**

I la predicció que vaig escriure al nucli («hi haurà inflació i serà gran») **falla**, que és la
cinquena del matí i sempre en la mateixa direcció.

**L'error meu, que val més que el resultat.** El primer càlcul aparellat donava **+0,0989**, deu
vegades més, i era fals. Ordenava els talls vistos per `(CER abans, CER després)` i l'aparellament
agafava sempre el primer dels que empataven en CER de partida — que és el que més havia millorat.
Em triava els millors jo mateix. Ho vaig veure perquè **la taula per trams no quadrava amb el
total**: dins de cada tram la diferència era de 0,01-0,04, i el total en deia 0,10. Un total que
no es pot reconstruir dels seus trams és un error, no una troballa.

**La firma de la memorització sí que hi és**, encara que l'interval no la confirmi:

| CER sota M₀ | vistos | no vistos |
|---|---|---|
| 0,00–0,05 | +0,0128 (n=85) | (n=8) |
| 0,10–0,15 | −0,0091 (n=158) | −0,0231 (n=16) |
| 0,15–0,20 | −0,0222 (n=174) | −0,0071 (n=24) |
| 0,20–0,25 | −0,0324 (n=203) | −0,0288 (n=24) |
| 0,25–0,30 | −0,0343 (n=249) | −0,0225 (n=30) |
| **0,30–0,36** | **−0,0543 (n=228)** | **−0,0150 (n=43)** |

Als vistos la millora creix monòtonament amb la distància de partida; als no vistos no té
tendència. Això és el que fa l'entrenament: acosta el model a l'etiqueta, i més com més lluny
n'estava. El control són 151 talls i per això l'interval no decideix.

### 21.2 · I per què la decisió no depèn d'aquest número

Els 14.426 talls catalogats, pel CER que tenien sota M₀:

| tram | vistos | no vistos |
|---|---|---|
| ≤ 0,35 (ja passava) | 1.832 | **335** |
| 0,35–0,45 (just a fora) | 17 | **1.137** |
| 0,45–0,60 | 0 | 2.350 |
| > 0,60 | 0 | 8.755 |

El corpus que la ronda 2 vol **no són els talls que ja tenim**: són els que M₁ promourà per
primera vegada. N'hi ha 1.137 just a fora del llindar, i M₁ millora precisament on la distància
és gran (−0,054 al tram de 0,30–0,36). Amb 335 que ja passen i una part d'aquells 1.137, hi ha
corpus nou **sense reutilitzar ni un tall vist**.

**Recomanació:** adoptar M₁ i triar el corpus de la ronda 2 només d'allò que M₁ no ha vist.
No perquè la inflació estigui provada —no ho està—, sinó perquè **evitar-la no costa res**: el
material que es deixa fora és el que ja s'ha fet servir, i el que es busca és el nou. Quan una
precaució és gratuïta, no cal esperar que la mesura la justifiqui.

## 22 · El llindar 0,20, provat: la meva recomanació era dolenta

§20.4 deia: «la recomanació bona per a la ronda 2 és provar 0,20, que conserva el 76 % de les
frases i treu un 16 % de l'error de l'etiqueta». §20.7 ja va corregir el 76 % (al SNRT és el
42 %). I la ronda ho ha contestat del tot.

Mateix M₀, mateixa recepta, mateixa llavor, mateixes proves. L'única diferència: 707 talls del
SNRT en comptes de 1.678.

| prova | 0,35 | 0,20 |
|---|---|---|
| snrt-retingut | **−0,0133** ✅ | +0,0014 |
| zouhir-tests | −0,0128 ✅ | **−0,0142** ✅ |
| test-fora | −0,0121 ✅ | −0,0064 |
| cv-zgh-test | −0,0023 | −0,0029 |
| tfa-226 | +0,0026 | +0,0014 |

**El braç estret no passa la regla del cercle**: una sola prova millora amb interval, i la regla
en demana dues. I cara a cara sobre les mateixes frases:

| prova | frases | CER 0,35 | CER 0,20 | B − A |
|---|---|---|---|---|
| **snrt-retingut** | 535 | 0,7278 | 0,7428 | **+0,0150 [+0,0100, +0,0199]** |
| test-fora | 101 | 0,2619 | 0,2676 | no decidible |
| tfa-226 | 226 | 0,1714 | 0,1701 | no decidible |
| zouhir-tests | 121 | 0,1874 | 0,1860 | no decidible |
| cv-zgh-test | 256 | 0,1440 | 0,1433 | no decidible |

El de 0,35 guanya on es juga —el SNRT retingut— i enlloc no perd. **Etiquetes més netes no
compensen menys material**, a aquesta escala.

I val la pena veure fins on arriba la cadena d'error: la calibració contra veritat humana era
bona (el CER ric de l'etiqueta baixa de 0,151 a 0,127, §20.4), la lectura de la proporció era
dolenta i es va corregir (§20.7), i **tot i tenir la calibració bona, la conclusió sobre el model
era falsa**. Una etiqueta millor no fa un model millor si pel camí es perd la meitat del corpus.

El llindar es queda a 0,35, ara per mesura i no per inèrcia.

## 23 · El cercle ha esgotat aquest corpus (i on és el coll d'ampolla de debò)

Decidit que la ronda 2 havia de triar el corpus només d'allò que M₁ no ha vist, el primer que
calia era comptar si n'hi ha. **No n'hi ha**: fora dels capítols retinguts no queda **cap** tall
no vist per sota del llindar — el train de la ronda 1 se'ls va endur tots. Tot el corpus nou ha
de sortir de **promoció**.

M₀ i M₁ sobre 3.164 candidats (no vistos, fora dels retinguts, CER ≤ 0,60):

| CER sota M₀ | talls | baixada amb M₁ | creuen 0,35 | |
|---|---|---|---|---|
| 0,35–0,40 | 313 | +0,0040 | 86 | 27,5 % |
| 0,40–0,45 | 472 | −0,0122 | 69 | 14,6 % |
| 0,45–0,50 | 405 | −0,0270 | 44 | 10,9 % |
| 0,50–0,55 | 752 | −0,0250 | 36 | 4,8 % |
| 0,55–0,61 | 706 | −0,0376 | 18 | 2,5 % |

**253 talls promoguts, 0,29 hores**, tots amb significat en català (tachelhit 0,19 h, Atles
central 0,07 h, tarifit 0,03 h). Més 141 que ja passaven i que la meva mesura anterior tenia mal
classificats, per una diferència de normalització entre `acord_triat.jsonl` i el nucli: **unes
394 rèpliques en total, ~0,45 h**.

Prediccio escrita: «unes desenes». Són 253 — **la setena vegada que em quedo curt en la mateixa
direcció**.

**I per què això tanca la ronda 2.** El train de la ronda 1 eren 1.678 talls del SNRT. El braç de
0,20, amb 707, ja va fallar la regla (§22). Amb 394 fallaria més clarament encara. I reutilitzar
els 1.849 que M₁ ja ha vist **no li ensenya res de nou**: és la mateixa dada.

Per tant: **no s'engega la ronda 2.** No per prudència, sinó perquè sabem el que donaria. Córrer
una hora de GPU per confirmar un fracàs que ja és mesurat seria gastar per no saber res.

### 23.1 · El coll d'ampolla no és l'algorisme

| | |
|---|---|
| vídeos del canal a la llista | **3.781** |
| capítols amb talls al dipòsit | **29** |
| episodis de *Tadfi n Tskla* al canal | 53 (en tenim 25) |
| episodis de *Baba Ali* al canal | 133 |

Hem llegit el **0,8 %** de la font. Tot el que he mesurat aquest matí —el sostre del subtitulador,
el llindar, la inflació, la promoció— són límits d'un corpus de 29 capítols, i cap no es mou
afinant res: es mouen **llegint més**.

Els 31 episodis de Tadfi que falten són 28 hores de la **mateixa sèrie**, amb el mateix format de
subtítol i la mateixa cadena ja feta (`tools/snrt/fabrica/nit.py`, reprenible). Això doblaria el
corpus. El guany següent del cercle no surt d'una ronda: surt de la fàbrica.

## 24 · La fitxa de fiabilitat, i la pila que no esperava

En Pablo: «per crear el diccionari hem de tenir índexs de fiabilitat». La temptació era un número
del 0 al 100. Seria mentida: una forma dita 50 vegades per **una** boca i una dita 50 vegades per
**vint** no són igual de fiables, i la mitjana no ho sap.

Sis senyals per forma, cadascun amb el seu sentit: **vegades**, **boques** (el que separa una
paraula de la llengua d'una mania d'un parlant o del model), **acord ull↔orella** (l'únic
testimoni independent), **confiança**, **diccionari humà** i **amb significat**.

| veredicte | formes | |
|---|---|---|
| de llibre (un diccionari la té) | 3.632 | 9,2 % |
| sòlida (≥5 boques, acord ≥0,25) | 154 | |
| **la norma no l'escriu** | **83** | |
| per mirar (mala espina de debò) | 6 | |
| poca cosa | 35.399 | 90,1 % |

**I aquí l'error meu, que val més que la taula.** El primer repartiment posava tot el que es diu
molt i no casa amb el subtítol a «per mirar: candidata a error sistemàtic del model» — 61 formes.
Mirant-les, era fals i del revés:

| forma | boques | confiança | acord | què és |
|---|---|---|---|---|
| `riġ` ⵔⵉⵖ | 17 | 0,85 | 0,11 | «vull» |
| `waḫḫa` ⵡⴰⵅⵅⴰ | 19 | 0,94 | 0,05 | «d'acord / encara que» |
| `walakin` | 18 | 0,85 | 0,00 | «però» (àrab) |
| `nkkwni` ⵏⴽⵯⵏⵉ | 9 | 0,88 | 0,10 | «nosaltres» |
| `aṭṭas` ⴰⵟⵟⴰⵚ | 10 | 0,88 | 0,13 | «molt» |

**Dinou parlants diferents no repeteixen l'al·lucinació d'un model.** Són manlleus de l'àrab i
partícules dialectals que la gent diu i que la norma de l'IRCAM no escriu: el sostre de la
normalització (§20.1) vist **paraula per paraula**.

El que separa les dues coses no és l'acord sinó **les boques i la confiança**: molta gent dient-la
amb seguretat i el subtítol que no l'escriu = llengua viva; poca gent, poca confiança i cap
suport = cosa nostra. Amb la regla corregida, la pila sospitosa passa de **61 a 6**.

**Per què importa:** ara tenim una manera **automàtica** de trobar les paraules que la gent diu i
el llibre no escriu. Són les que qui aprèn sentirà sempre i no trobarà enlloc, i són invisibles
per a qualsevol mètode que es fiï del subtítol.

(`fitxa_de_fiabilitat.py` → `fitxa_fiabilitat.tsv`; `lexic_confirmat.py` per al creuament amb els
diccionaris.)

## 25 · La taula de variants: per al diccionari sí, per a mesurar no

Feta **per evidència** i no per semblança de lletres: dues formes són variants si s'alineen
repetidament amb el mateix signe escrit. (L'intent per distància d'edició va dir que `nns` era
variant d'`insi`, «eriçó»: en paraules de tres consonants, un canvi aparella qualsevol cosa.)

48 grups, 122 formes. I el que surt és **el mapa dialectal a escala de paraula**:

| escrit | formes, amb qui les diu |
|---|---|
| ⵏⵏⴽ «teu» | `nnš` (8 boques, les tres varietats) · `nnk` (7, Atles+tachelhit) · `nk` (5, només tachelhit) |
| ⵡⴰⵡⴰⵍ «paraula» | `wawal` (10, Atles+tachelhit) · **`wawar` (2, només tarifit)** |
| ⵜⵓⴷⵔⵜ «vida» | `tudrt` (Atles+tachelhit) · **`tudart`, `tudat` (només tarifit)** |
| ⵏⵏⵖ | `nnġ` (13) · `nnḫ` (8) |

La l→r del rifeny i la k→š de §13 deixen de ser una estadística i passen a ser **entrades amb
qui diu cada forma**.

### 25.1 · I la prova que vaig fer per si servia per mesurar: no

La hipòtesi era que part del nostre CER és el model **encertant en un altre dialecte** i el
comptem com a error. Mesurat acceptant les variants conegudes com a encert:

| prova | CER | amb variants | canvi |
|---|---|---|---|
| zouhir-tests | 0,1874 | 0,1868 | −0,0006 |
| tfa-226 | 0,1714 | 0,1714 | +0,0000 |
| test-fora | 0,2619 | 0,2615 | −0,0004 |
| cv-zgh-test | 0,1440 | 0,1435 | −0,0005 |
| **snrt-retingut** (taula feta sense aquests capítols) | **0,7258** | **0,7256** | **−0,0002** |

**Zero.** És la vuitena predicció meva que cau avui, i la raó la teníem escrita des d'anit: a
0,726 el model i el subtítol no discrepen en **com s'escriu** una paraula, discrepen en **quina
paraula és** — *amawal* contra *lmuεjam*. La variació de grafia i pronúncia és real i val la pena
documentar-la, però **no és el que ens separa del subtítol**.

La taula serveix per al diccionari i per al visor. Per a mesurar, no.


## 26. El diccionari, comptat bé (20-11, tarda)

El 20-11 al matí vaig dir que **3.632 formes** estaven confirmades per un diccionari humà. **El
85 % no hi eren.** El casament es feia per esquelet (només les consonants, perquè la norma escriu
vocals que la parla no diu) amb un mínim de **dues**, i amb dues consonants una clau com `ns`
casa amb desenes de formes que no hi tenen res a veure.

El llindar no s'ha triat: s'ha mesurat (`quina_llargada_val.py`). Per a cada llargada es compta
quantes formes nostres casen amb el diccionari de debò i quantes amb **un diccionari fals** de la
mateixa mida, fet amb les mateixes lletres i les mateixes llargades:

| consonants | casen | per atzar | de debò |
|---|---|---|---|
| 2 | 1.833 | **1.479** | 354 (19 %) |
| 3 | 1.271 | **1.070** | 201 (16 %) |
| 4 | 412 | 146 | 266 (65 %) |
| 5 | 111 | **6** | 105 (**95 %**) |
| 6 | 5 | 0 | 5 (100 %) |

Per això **cinc consonants confirmen** i **quatre només insinuen**. El recompte honest:

| veredicte | formes |
|---|---|
| de llibre (forma exacta o esquelet ≥5) | **264** |
| potser al diccionari (esquelet de 4) | 389 |
| sòlida | 210 |
| la norma no l'escriu | 152 |
| per mirar | 9 |

## 27. La regla del cercle, jutjada per capítols (20-11, tarda)

`bootstrap()` remostrejava **talls**, i amb aquells intervals la regla decideix si una ronda
s'adopta. Els talls d'un capítol no són independents, i n'hi ha pocs darrere de moltes frases:
`snrt-retingut` són **1.127 frases de quatre capítols**.

| prova | capítols | per tall | per capítol |
|---|---|---|---|
| snrt-retingut | 4 | [−0,0194, −0,0075] **MILLORA** | [−0,0370, +0,0136] **no es pot dir** |
| test-fora | 5 | [−0,0238, −0,0022] MILLORA | [−0,0368, −0,0017] MILLORA |
| zouhir-tests | 4 | [−0,0175, −0,0078] MILLORA | [−0,0156, −0,0108] MILLORA |

La ronda **segueix passant** la regla, amb dues millores en comptes de tres: el mínim que demana,
i la prova més gran ja no hi compta. Arreglat al PR #711.

**I el parany de l'altre costat:** no es remostreja tot per capítol. El `cv-zgh-test` són 256
clips independents amb **un sol** valor de capítol, i remostrejar-lo donaria sempre la mateixa
mostra: un interval d'amplada zero que diria «millora» per construcció.


## 28. El llindar: 0,20 i 0,35 són iguals, i per això s'ha de triar 0,20 (20-11, tarda)

> **Això es va corregir a la §37:** les «quatre proves amb veritat humana» són tres, i dues comparteixen 36 de les 95 frases. El que hi ha aquí sota és el que es va creure, i es deixa perquè es vegi per què era fals.

Al matí vaig dir que el braç de 0,20 **no passava la regla** i que 0,35 guanyava. **Les dues
coses eren del mateix error**, i cap de les dues s'aguanta.

**1. B també passa la regla.** El «no passa» sortia de remostrejar frases. Per capítol:

| braç | millora | empitjora | regla |
|---|---|---|---|
| A (0,35) | test-fora, zouhir | cap | ADOPTA |
| B (0,20) | test-fora, zouhir | cap | **ADOPTA** |

**2. Cara a cara, són iguals.** La fila que feia guanyar A era `snrt-retingut`, i allà les dues
execucions van **tallar els mateixos capítols en talls diferents** (A=279/B=296 en un vídeo, 148
comuns): es comparava el 46 % dels talls, triat per una coincidència del tallador. A les quatre
proves amb veritat humana, que casen al 100 %:

| prova | A (0,35) | B (0,20) | B − A |
|---|---|---|---|
| zouhir-tests | 0,1874 | 0,1860 | −0,0014 |
| tfa-226 | 0,1714 | 0,1701 | −0,0013 |
| cv-zgh-test | 0,1440 | 0,1433 | −0,0006 |
| test-fora | 0,2619 | 0,2676 | +0,0057 |

**Les quatre juntes (18 capítols, 704 talls): B − A = −0,0002 [−0,0029, +0,0026].**
Indistingibles.

**3. I per això s'ha de triar 0,20.** El llindar no compra record -- el record és 43,0 % a
tots els llindars, perquè les paraules encertades ja passen al zero. El que compra és
**material**, pagat amb etiquetes falses:

| llindar | talls | precisió de l'etiqueta |
|---|---|---|
| 0,00 (mateix esquelet) | 2.211 | 89,7 % |
| **0,20** | **2.420** | **81,9 %** |
| 0,35 (el d'ara) | 2.971 | 66,7 % |

A igualtat de resultat mesurat, **0,20 dona el mateix amb un terç menys d'etiquetes falses**.
La ronda 2 es fa amb 0,20.

(El 0,15 no és una opció intermèdia: només afegeix **17 parelles** sobre el 0,00.)


## 29. Els espais: quant costen, i què els cura (20-11, nit)

L'orella **enganxa**: diu 5,2 lletres per paraula quan les persones n'escriuen 3,8 i les nostres
etiquetes 3,9. **Les etiquetes no en tenen la culpa.** I diu menys paraules que l'ull el **70 %**
de les vegades.

| prova | CER | el mateix sense espais | quant n'és espai |
|---|---|---|---|
| cv-zgh-test | 0,1440 | 0,1040 | 28 % |
| tfa-226 | 0,1714 | 0,1278 | 25 % |
| test-fora | 0,2619 | 0,2205 | 16 % |
| zouhir-tests | 0,1874 | 0,1672 | 11 % |

**El sostre no és el que s'assoleix.** L'H3 ja va mesurar què fa el model de llengua al feix
sobre 226 versos amb veritat humana: **CER 0,207 → 0,198 i WER 0,712 → 0,640** amb
`corpus_bi α 0,15 β 1,0`. O sigui −0,009 de CER, no −0,044. La feina és **desplegar-ho**, que
la canonada segueix amb greedy des del 15-11.

**Provat i descartat:** tornar a partir la sortida amb Viterbi sobre un lèxic. Amb el lèxic del
SNRT 0,1440 → 0,1464 i amb el de la biblioteca 0,1440 → 0,1444. Empitjora les dues vegades.

**I el filtre de grau A és cec a això:** compara esquelets de consonants, que no tenen espais.
A la rèplica `asywmmpqztvnotxd:52` les tres versions (enganxada, mig partida, ben espaiada) donen
el mateix 0,154, mentre el WER va de 1,000 a 0,500.

## 30. Buscar ample quan hi ha qui ho verifica (20-11, nit)

El camí invers des del significat es limitava amb dos llindars triats a ull (Dice ≥ 0,22, ≥ 2
coocurrències). Mesurant-los contra l'ull:

| cops | dice | cadenes tocades | confirma l'ull | **formes confirmades** |
|---|---|---|---|---|
| 2 | 0,22 (el d'abans) | 342 (7,3 %) | 73 % | ~316 |
| 1 | 0,30 | 380 (8,1 %) | 73 % | ~348 |
| **1** | **0,10** | **736 (15,8 %)** | 63 % | **789** |

**Quan hi ha un verificador independent, la precisió de la cerca no és el que compta**: compta
quantes troballes confirmades en treus. Amb el filtre ample surten **789 troballes** (381 parelles
forma↔significat), contra ~316. Les que més surten: `ⴰⵎⴰⵣⵉⵖ` = amazic, `ⵎⴰⵙⵙ` = senyor,
`ⵎⴰⵙⵙⴰ` = senyora, `ⵣⵡⴰⵔ` = primer, `ntta` = ell. A `formes_pel_significat.json`.

## 31. Números corregits aquesta nit

> **Això es va corregir a la §38:** el −0,044 del model de llengua era el sostre; el guany mesurat és −0,009 de CER. El que hi ha aquí sota és el que es va creure, i es deixa perquè es vegi per què era fals.

| què | deia | és |
|---|---|---|
| preu d'evitar la inflació | 13 % del material | **84 %** (1.849 de 2.190 de grau A, no de 14.426) |
| germanes de la taula de variants | 242 parelles | **216**, i cap a més de 0,5 (abans 26, dotze a 1,0) |
| guany del model de llengua | −0,044 de CER | **−0,009 de CER, −0,072 de WER** (el −0,044 és el sostre) |


## 32. La peça que feia entrar el lèxic al feix no era al repositori (21-11, matinada)

`h3_lexic_al_feix.py` fa `import arpa_lm` i amb ell apedaça pyctcdecode. **`arpa_lm.py` vivia
només al dataset de Kaggle.** És la peça que fa entrar el lèxic al feix: pyctcdecode només mira
la llista de paraules si hi ha un model carregat, i sense fitxer ARPA **el feix ignora el lèxic
del tot**. O sigui que l'únic experiment que ha mesurat el guany del model de llengua
(H3: WER 0,712 → 0,640) **no es podia repetir des del repositori**.

Ara hi és, amb set proves que no demanen GPU: amb logits fabricats on l'acústica prefereix
`nkkim` per mig punt, el feix sense model diu `nkkim` i amb el lèxic diu `nkkin`.

**Els models de llengua, construïts** amb les dues portes de fuita tapades (de la biblioteca
només `train`; del SNRT fora els quatre capítols retinguts, llegits de les sortides de la ronda):

| | frases | formes diferents | bigrames |
|---|---|---|---|
| només biblioteca | 3.545 | 5.292 | 14.518 |
| biblioteca + SNRT | **15.331** | **14.902** | **61.075** |

**I la que gairebé passa.** Els unigrames sortien de `fitxa_fiabilitat.tsv` sencer: **39.519
formes, de les quals 38.250 són la pila «poca cosa»**, les que només diu la nostra orella i cap
testimoni confirma. Posar-les al lèxic del feix és donar permís al model per repetir les seves
pròpies al·lucinacions. El lèxic net en té 15.591.

## 33. No tots els «Tadfi n Tskla» porten tifinag (21-11, matinada)

Dos episodis de la collita han fallat amb:

> `no puc saber quina línia és tifinag i quina àrab: només 3 fotogrames de 12 amb dues línies
> ben diferenciades`

La fàbrica espera dues línies (tifinag a dalt, àrab a sota) i aquests en tenen **una de sola**
la major part de l'estona. El triatge del canal (§24) no ho podia veure: mirava **un sol vídeo
de mostra per programa** i en deduïa el programa sencer.

El que sí que s'aguanta: dels 20 episodis collits, el **97 % de les rèpliques porten tifinag** i
el 100 % porten àrab, amb confiança mitjana 0,938. El material que passa és bo; el que no cal
comptar és que tots els episodis passin.


## 34. Quin model de llengua, decidit sense GPU (21-11, matinada)

La collita d'aquesta nit **no havia entrat enlloc**: `text_triat.jsonl` té els 25 capítols
vells i cap dels 23 episodis collits. Tot el que es va calcular la nit del 20 — glossari, via
del significat, corpus — sortia del material vell.

Per al model de llengua només cal el **tifinag**, que els episodis nous ja tenen (no els cal ni
traducció ni orella). Afegint-los:

| | frases | paraules | formes diferents | bigrames |
|---|---|---|---|---|
| abans | 15.331 | 98.809 | 14.902 | 61.075 |
| **amb la collita** | **25.052** | **168.145** | **21.801** | **96.032** |

**Però més gran no vol dir millor**: el subtítol del SNRT és una traducció normalitzada per
l'IRCAM i podria empènyer la sortida cap a una llengua que ningú no parla. Es decideix amb la
**perplexitat sobre els quatre capítols retinguts**, que cap dels dos models no ha vist:

| model | bigrames | perplexitat | cobertura |
|---|---|---|---|
| només biblioteca (≈ la mida del de l'H3) | 14.518 | **2.674,9** | 88,2 % |
| biblioteca + SNRT | 96.032 | **731,8** | 88,2 % |

**La perplexitat baixa 3,7 vegades.** L'H3 va mesurar −0,072 de WER amb un model de la mida del
primer; el que es desplegarà és molt millor que aquell, i per tant el guany hauria de ser més
gros. Això és una expectativa, no una mesura: el que es mesura aquí és la perplexitat, no el CER.

La **cobertura del 88,2 %** és el sostre de l'altre costat: una paraula que no és al vocabulari,
el feix no la pot proposar per bo que sigui el model.

## 35. El glossari al visor, i el mateix error repetit (21-11, matinada)

El visor diu ara què volen dir les paraules que tenim al glossari (`tamɣart` = dona, `middn` =
gent, sota el subtítol). El casament es fa **al servidor**, amb la mateixa funció d'esquelet que
la resta de la canonada: calcular-la una segona vegada en JavaScript seria tenir dues versions
que un dia deixarien de dir el mateix.

El primer llindar que hi vaig posar era **tres consonants**, i sortien coses com `nnun = dit` i
`yanun = conèixer`, que són falses. Mesurat contra un glossari amb els esquelets barrejats:

| mínim | casen | per atzar | de debò |
|---|---|---|---|
| 3 | 6.240 | 1.737 | 72 % |
| **4** | 2.478 | 170 | **93 %** |
| 5 | 1.262 | 7 | 99 % |

És el mateix llindar i el mateix error que ja havia comès amb el diccionari unes hores abans.


## 36. Qui tradueix millor, i qui no arriba (21-11)

Vaig traduir jo les 411 línies d'un episodi des de l'àrab, i l'acord amb la via del tifinag
(el NLLB) va donar **chrF 0,310**, un 12 % de línies confirmades. Això no deia de qui era la
culpa.

**El control**: les mateixes passades sobre línies on el català **ja està confirmat** per dos
traductors de pagament, amb una mostra de la mateixa mida i la mateixa distribució de llargades.

| | chrF mitjà | confirmades |
|---|---|---|
| traducció ja confirmada | **0,339** | 20 % |
| la meva | 0,310 | 12 % |

**El NLLB arriba a 0,34 encara que a l'altra banda hi hagi una traducció bona per definició.**
El 12 % és el seu sostre, no un suspens meu.

Però la diferència de −0,029 tenia un interval que **excloïa el zero** ([−0,0550, −0,0043]), i
un confós: **són episodis diferents**, amb qualitats d'OCR diferents.

**La prova neta** són les mateixes línies traduïdes per tots dos. 40 línies dels episodis de
control, traduïdes a cegues:

| | |
|---|---|
| chrF contra la traducció confirmada | **0,746** [0,687, 0,799] |
| per sobre de 0,5 | 88 % |

Igual que la primera prova (0,743 sobre 25 línies). **El −0,029 era l'episodi, no el traductor.**

**I a les discrepàncies, de vegades qui falla és l'altre.** L'àrab diu
`فيكون هناك نجاح بين الأستاذ والتلميذ`; la traducció confirmada hi posa «èxit entre el professor
i **l'excel·lència**» i la meva «entre el mestre i **l'alumne**». Van llegir `التميز` on hi diu
`التلميذ`. La frase confirmada no vol dir res.

**Un biaix que s'ha de dir al costat de qualsevol d'aquests números:** el NLLB tradueix una
línia **aïllada**; jo tradueixo amb l'episodi sencer al davant. Part del que sembla error seu
és falta de context, i per això s'ha de mesurar també amb context.


## 37. Les quatre proves són tres, i una no és humana (21-11)

En Pablo: «això de les 4 proves de veritat humana no me'n fio. Què són?». Tenia raó.

| prova | què és | independent? |
|---|---|---|
| tfa-226 | 8 vídeos de Tamazight For All, subtítol de l'autor | — |
| **test-fora** | **el mateix canal**: 36 de les seves 95 frases **són literalment a tfa-226** | **no** |
| zouhir-tests | 4 vídeos diferents | sí |
| cv-zgh-test | Common Voice: text humà, però **parla llegida** | sí |
| snrt-retingut | la referència és **l'OCR del tifinag** | **no és humana** |

O sigui **tres fonts, no quatre**. I la ronda que es va adoptar es basava en «millora a
test-fora i a zouhir», amb test-fora solapant-se amb una prova (tfa-226) que no va millorar.

**El que sí que està net:** dels 283 textos de prova, només **4 són al train, i són paraules
soltes** (`waḫḫa`, `smmus`, `timnsiwin`). No hi ha fuita.

## 38. El model de llengua al feix, mesurat de debò (21-11)

Els logits de les cinc proves estaven **guardats a l'ECS des del 19-11** i ningú no els havia
fet servir: l'experiment B0-B3 només s'havia mesurat sobre **20 parelles**. Descodificant les
proves de debò (sense GPU, només cerca de feix sobre els logits guardats):

| prova | n | greedy | amb LM (B1, α 0,15) | |
|---|---|---|---|---|
| cv-zgh-test | 256 | 0,1463 | **0,1264** | **−0,0199 [−0,0274, −0,0125] MILLORA** |
| test-fora | 101 | 0,2740 | 0,2669 | −0,0071 no es pot dir |
| tfa-226 | 226 | 0,1688 | 0,1674 | −0,0014 no es pot dir |
| zouhir-tests | 121 | 0,2002 | 0,2074 | +0,0072 (va a l'altre costat) |

**Per la nostra pròpia regla no s'adopta**: en millora una, no dues. El model de llengua ajuda
**on la parla és text llegit** (Common Voice) i no ajuda enlloc més — té sentit, perquè està
fet de llengua escrita.

**Em desdic del que vaig dir el 20 a la nit:** vaig vendre això com «l'únic guany gros a
l'abast». No ho és.

## 39. El gir cap a l'àrab (21-11, d'en Pablo)

«Si el model és capaç de traduir del tifinag a l'àrab, després la traducció de l'àrab al català
és trivial.» Provat amb el model que ja hi ha, **sense entrenar-lo mai en aquesta direcció**:

| cap a | chrF contra l'àrab de la pantalla |
|---|---|
| àrab estàndard | **0,266** |
| àrab marroquí | 0,217 |
| català (la direcció per a la qual SÍ està afinat) | 0,308 |

I al vídeo de TFA que no té cap subtítol, l'àrab encerta on el català no:
`azul imddukal timdukalin` → `السلامُ عليكُم يا رفاق` («la pau sigui amb vosaltres, amics»),
mentre el català deia «Bon dia, amigues, senyores, senyores, senyores».

**I el corpus hi és**: 13.757 parelles tifinag↔àrab alineades **pel fotograma**, 9.897 que
passen les portes. El catàleg té **215 capítols** de Tadfi i només 26 fets: acabar-lo donaria
**~107.000 parelles** sense cap cost de traducció.

El que NO funciona per aquest camí és la veu: del tifinag escrit es tradueix a chrF 0,319, del
que sent l'orella a **0,131**. La cadena multiplica errors.

## 40. L'ECS tenia una fàbrica millor, i jo duplicava (21-11)

| | la collita de YouTube (la meva) | la fàbrica de l'ECS |
|---|---|---|
| font | YouTube | **forja.ma**, replay oficial |
| resolució | 720p | **1080p** (el tifinag no es llegeix a 720p) |
| catàleg | 30 | **215 capítols** |

**I dels 184 capítols pendents, només 6 tenen subtítols cremats.** Sondejats tres capítols per
programa: vuit programes no tenen cap text, i 23 capítols la SNRT no els serveix per replay.
Encuar-los tots hauria cremat unes 120 hores de servidor per 6 capítols útils.


## 41. L'alineació forçada: −0,0789, i feia tres dies que hi era (21-11)

El diagnòstic d'alineació (#601, 18-11) es va executar i **ningú no n'havia llegit el resultat**:

| | |
|---|---|
| talls amb l'inici desplaçat **> 0,5 s** | **358 de 589 (62 %)** |
| amb el final desplaçat | 336 (58 %) |
| desplaçaments extrems | de −36 s a +119 s |
| CER amb els límits del subtítol | 0,7370 |
| **CER retallant on el model sent la veu** | **0,6581** |
| **guany** | **−0,0789** |

Per comparar: una ronda del cercle val −0,003 a −0,013; el model de llengua al feix, −0,0199 i
només a Common Voice. **Retallar bé val sis vegades més que la millor ronda**, i no demana
dades noves.

Dels **nostres** talls (els 27 capítols collits): només el **5 % és silenci** als extrems, però
el **85 % comença o acaba amb veu alta**. Això no vol dir trencats — en una entrevista la gent
parla seguit i qualsevol frontera cau dins de la parla. Només l'alineació forçada pot dir si el
tall conté les paraules del seu subtítol o les del veí.

## 42. El corpus tenia tarifit, i el dev n'era el 100 % (21-11)

En Pablo: «no volem coses en tarifit perquè és una altra llengua». El corpus que s'acabava de
pujar en tenia:

| | capítols del Rif | línies |
|---|---|---|
| train | 4 de 21 | 22 % |
| **dev** | **2 de 2** | **100 %** |
| **test** | **2 de 4** | **53 %** |

**El classificador pel lèxic deia «tachelhit» als 27 capítols**, sense cap excepció, i era fals
per dues raons: el lèxic diferencial té **117 marques tachelhit contra 39 tarifit**, i el
subtítol està **normalitzat per l'IRCAM**, que és on les marques dialectals s'esborren. Un
rifeny subtitulat en amazic estàndard s'escriu com un tachelhit.

El senyal bo no passa per cap dels dos filtres: **els topònims a l'àrab**.

| capítol | a l'àrab | el lèxic deia |
|---|---|---|
| `-SyzF2LtAEs` | Tafersit ×26, Rif ×6 | tachelhit 0,83 |
| `hiKMeMfsIxw` | Rif ×30 | 0,85 |
| `XSQcExn0e08` | Rif ×27, Nador | 0,92 |
| `bij1eT0tAW0` | Rif ×17, Driouch ×4 | 0,73 |

**Els sis capítols amb menys puntuació tachelhit són sis dels vuit del Rif**, i els cinc de sota ho són tots: el classificador
els veia, el llindar era massa fluix. Dos senyals independents, i coincideixen.

**Compte de no barrejar dos conjunts.** Aquests **8 del Rif són de la collita nova** (27 capítols, slugs de YouTube). Els **11 tarifit de producció** són els capítols **vells** de Tadfi (slugs de 40 lletres de forja.ma) i **no se'n solapa cap**: 8 i 11 no són dos comptes de la mateixa cosa, són dos conjunts diferents. En total, 19 capítols rifenys coneguts.

Corpus refets: text **4.562 / 599 / 1.278** (de 7.194 / 861 / 1.682), veu **7,4 h** (de 12,7).
Punt de partida net del traductor: **chrF 0,2634** (el contaminat deia 0,2614 — el tarifit no
inflava el número, però el dev hauria triat el model equivocat).

I l'episodi que es va traduir sencer la nit del 20 (Said El Aabouti, Tafersit) **és rifeny**:
val per al visor, no entra a cap entrenament.


## 43. El primer guany de debò amb el material del SNRT: 0,2634 -> 0,3470 (21-11)

Afinant el NLLB per a **tifinag -> àrab** amb les parelles de la pantalla del SNRT:

| | chrF |
|---|---|
| punt de partida (NLLB afinat per al català, demanant-li àrab) | **0,2634** |
| afinat amb 4.562 parelles, millor punt de control | **0,3470** |
| | **+0,0836 · un 32 % relatiu** |

Mesurat al **test net**: partició per capítols (no per línies), sense cap dels 8 capítols del Rif,
4 capítols que el model no ha vist mai.

Per època al dev: 0,4162 · 0,4189 · **0,4258** · 0,4214 · 0,4137. El millor és el **tercer**;
cinc èpoques són massa i a partir de la quarta es desaprèn. S'ha fet servir el millor punt de
control, no l'últim.

El dev (0,4258) queda molt per sobre del test (0,3470): amb 2 capítols de dev i 4 de test, la
diferència entre capítols pesa més que el model. **El número que val és el del test.**

Què en surt, de debò:

| la pantalla diu | el model diu |
|---|---|
| «Espectadors i espectadores del canal amazic, benvinguts» | «Espectadors del canal amazic, benvinguts» |
| «Us dono la benvinguda al vostre programa *La flaire de la literatura*» | «Us volem presentar un programa del programa literari» |
| «El convidat d'avui és un dels grans militants de la cultura amaziga» | «El convidat d'avui és d'entre els **artistes** de la cultura amaziga» |

La primera és bona; la segona es desfà; la tercera encerta l'estructura i falla la paraula
(«artistes» per «militants»). **Serveix per entendre de què es parla, no per publicar.**

Per comparar, el mateix dia: **jo traduint l'àrab a mà fa chrF 0,746**. *(Rectificat el 24-11, §56: aquell 0,746 és **àrab → català**, contra una traducció confirmada, no tifinag → àrab. No són comparables. Traduint tifinag → àrab a cegues sobre 40 línies del test net, faig 0,406 i el NLLB 0,333.)* La distància entre
0,347 i 0,746 és la notícia: el que de debò tradueix avui no és cap model nostre. El model val
per allò que jo no puc fer -- 215 capítols-- i encara no tradueix prou bé.


## 44. La taula norma↔parla tenia 26 entrades que són tarifit (21-11)

Un peó que auditava la documentació va deixar una pregunta oberta: la taula de correspondències
estàndard↔dialecte (§2, 181 correspondències), **està contaminada de tarifit?** No ho va poder
tancar perquè el fitxer viu fora del repositori. Tancada:

**Sí.** Les 74.761 parelles alineades venen de 25 capítols i **11 són del Rif**: **27.180
parelles, el 36,4 %**.

De les 181 correspondències publicades:

| | |
|---|---|
| **només del Rif** | **26 (14 %)** |
| majoria del Rif | 6 més — **32 en total per sobre del 50 %** |
| cap rastre de Rif | 109 (60 %) |

I les 26 no són soroll qualsevol: són **tarifit de manual**.

| la taula deia | i això és |
|---|---|
|  → ,  → ,  →  | la **l → r** rifenya, la marca que fem servir per **detectar** el tarifit |
|  →  | l'interrogatiu rifeny |
|  → ,  →  | fonologia rifenya |

O sigui que la taula que descriu **com el tachelhit s'aparta de la norma de l'IRCAM** contenia,
en un 14 % de les seves entrades, **com se'n aparta una altra llengua**. I la pitjor part: hi
havia la mateixa l→r que el classificador de varietat fa servir com a prova que un capítol és
rifeny. La taula hauria pogut ensenyar a prendre tarifit per tachelhit.

Taula neta a : **149 correspondències**.

**La lliçó, que és la del dia repetida:** el 20-11 vaig descobrir que el corpus d'entrenament
tenia el dev 100 % tarifit. Vaig arreglar el corpus i **no vaig mirar què més s'havia construït
amb el mateix material**. Una contaminació trobada en un lloc s'ha de buscar a tots els que
beuen de la mateixa font.

---

## 45. Retallar amb l'alineació forçada: −0,21 de CER, el guany més gran fins ara (22-11)

> ⚠️ **El número no mesura el que diu.** Les fronteres d'aquesta secció venen d'un alineador
> que no rebia la frase, només els espais entre paraules (**§48**), i el CER d'inferència
> premia escurçar el so, no encertar la frontera (**§49**): retallant endins encara surt
> millor. El guany real del retall està sense mesurar.

**El diagnòstic.** L'alineació forçada de 4.788 talls nostres (MMS-1b-all, Viterbi sobre les
probabilitats de CTC) diu que **el 51 % del so no és la frase**:

| | |
|---|---|
| silenci al davant | mediana **0,79 s** · més de 0,3 s al **84 %** dels talls |
| silenci al darrere | mediana **0,97 s** · més de 0,3 s al **95 %** |
| del so total, és la frase | **49 %** |

**La prova.** 245 talls del capítol `agnkrfivlpeuwz`, el mateix model (MMS-1b-all + `shi`,
sense adaptador), la mateixa referència (el tifinag del subtítol transliterat). L'**única**
cosa que canvia és si el wav va sencer o retallat a `[veu_ini − 0,15 s, veu_fi + 0,15 s]`:

| talls | sencer | retallat | diferència |
|---|---|---|---|
| 25 | 0,8838 | 0,7958 | −0,088 |
| 50 | 0,9909 | 0,8445 | −0,146 |
| 100 | 1,0401 | 0,8490 | −0,191 |
| 150 | 1,0439 | 0,8462 | −0,198 |
| 174 | 1,0645 | 0,8506 | −0,214 |
| **245 (final)** | **1,0818** | **0,8583** | **−0,2235 (−20,7 %)** |

I la distància **creix** amb la mostra, cosa que descarta que sigui soroll de mostreig.
**Millora en 188 dels 245 talls (77 %)**: no és que uns pocs talls arrosseguin la mitjana.

**Per què el CER del so sencer passa d'1,0.** Un CER superior a 1 vol dir que la sortida és
més llarga que la referència: **l'ASR transcriu més del que diu la frase**. El «silenci» no
és silenci — és altra gent parlant, i el model la sent. Retallant, deixa de sentir-la.

**Per situar-ho.** El guany més gran que havíem mesurat en tot el projecte era **−0,0789**
(el diagnòstic del 18-11 sobre talls antics) i el lèxic al feix donava **−0,07**. Això és
**dues vegades i mitja més**, i no demana collir ni un capítol nou: és el material que ja
tenim, ben tallat.

**Quant se'n va.** Provat sobre 250 talls reals: 245 retallats, **1,65 s de mitjana per
tall**, 7 minuts de 250. Escalat als 17.379 talls, són unes **8 hores de so** que ara mateix
entren a l'entrenament sense ser la frase.

**El que falta.** L'alineació només cobreix 9 capítols de 33 a l'ECS (unes 30 h més) i cap
dels 20 que la fàbrica del PC ha fet avui (2.106 talls). Fins que no hi siguin tots, el
retall no es pot aplicar a tot el corpus, i **el guany real s'ha de tornar a mesurar
reentrenant**, no només transcrivint: aquí s'ha mesurat la inferència, no l'entrenament.

**Els guions:** `retalla.py` (aplica el retall sense esborrar els originals),
`prova_retall.py` (aquesta mesura), `alinea_pc.py` (els talls que la fàbrica fa al PC).

---

## 46. L'energia no pot substituir l'alineació, i el perquè confirma la §45 (22-11)

> ⚠️ **Mesura invàlida.** L'energia es compara aquí amb fronteres que estaven mal: el «0 %»
> no és un error de l'energia. **Corregit a la §48.**

L'alineació forçada triga ~25 h per als 20.547 talls perquè fa servir **MMS-1b-all** (4 GB) i
Viterbi sobre les probabilitats del CTC. La temptació és òbvia: per treure silenci del davant
i del darrere, no n'hi hauria prou amb **l'energia del senyal**, que es calcula en minuts?

**Comprovat sense gastar res.** Hi havia 6.354 talls amb la frontera de l'alineació ja
calculada. S'ha calculat la frontera per energia dels mateixos (finestra de 20 ms, llindar
relatiu al terra de cada tall) i s'han comparat 400:

| | mediana de l'error | dins de 0,2 s |
|---|---|---|
| inici | **−0,61 s** | 13 % |
| final | **+0,77 s** | 4 % |
| **les dues alhora** | — | **0 %** |

**No serveix.** Però el més interessant és **el signe**: l'energia diu sistemàticament que la
veu **comença abans** i **acaba després** del que diu l'alineació.

Això **confirma la §45 per un camí independent**. Si el que hi ha al davant i al darrere fos
silenci, l'energia i l'alineació coincidirien. Que l'energia hi trobi senyal vol dir que
**n'hi ha** — i que l'alineació, que sap quin text busca, el descarta perquè **no és la
frase**. El soroll no és soroll: és **una altra persona parlant**.

Per tant el model de 4 GB **no és un luxe**: és l'única cosa que distingeix «hi ha veu» de
«hi ha LA veu». No hi ha drecera.

**El guió:** `prova_energia.py`.

---

## 47. Tres dreceres per no esperar les 26 h d'alineació, i cap no val (22-11)

> ⚠️ **Mesura invàlida, i probablement al revés.** El `MMS_FA` coincideix amb l'alineació
> bona a 0,05 s; aquí es compara amb la trencada. **Corregit a la §48.**

L'alineació de 20.547 talls amb MMS-1b-all triga ~26 h a l'ECS. Val **−0,2235 de CER** (§45),
així que l'espera té sentit — però abans de pagar-la s'han provat tres dreceres. Totes tres es
comproven igual: hi ha 6.354 talls amb la frontera del model gran ja calculada, i es mira si
el mètode barat hi cau a prop.

| drecera | les dues fronteres dins de 0,2 s | velocitat |
|---|---|---|
| **energia del senyal** (§46) | **0 %** | instantània |
| **`torchaudio.pipelines.MMS_FA`** (300 M, fet per alinear) | **5 %** | 1,43 s/tall |
| **MMS-1b quantitzat a int8** | **100 %** (i dins de 0,05 s) | 3,20 s contra 3,64 |

**L'energia i MMS_FA fallen igual i pel mateix motiu.** Les dues posen l'inici **abans** i el
final **després** (−0,37 s i +0,54 s amb MMS_FA; −0,61 i +0,77 amb l'energia). Les dues troben
senyal als extrems perquè **n'hi ha**: una altra persona parlant. Només el model gran amb
l'adaptador `shi`, que coneix la llengua, sap que aquell senyal **no és LA frase**.

Que el biaix sigui el mateix en dos mètodes independents és la tercera confirmació de la §45.

**La quantització sí que és segura: no mou ni una frontera.** Però el guany és **1,14x**, no
el 2-3x que es podia esperar: el càlcul de wav2vec2 no és tot capes lineals. Sobre 26 h,
estalviaria unes 3 h — no val la complexitat d'afegir-la al camí que ja corre.

**Conclusió:** no hi ha drecera. Les 26 h es paguen, i es paguen soles: la màquina no costa
res i ningú no ha d'estar-hi a sobre.

**Els guions:** `prova_energia.py`, `prova_mms_fa.py`, `prova_int8.py`.

---

## 48. L'alineació no alineava la frase: alineava els espais entre paraules (23-11)

Les §45, §46 i §47 d'ahir pengen totes d'un fitxer de fronteres que és **mala mesura**. No pel
mètode: per una línia de codi.

**El que passava.** `ecs_alinea.py` donava el tifinag del subtítol directament al vocabulari del
MMS amb la llengua `shi`. Aquell vocabulari és **llatí**:

```
vocab de 39 · 1abdefghijklmnqrstuwyz|âÿġšεḍḥḫṣṭẓ‐
tifinag al vocab: 0
```

`a_ids` llençava tot el que no hi fos. Del tifinag no hi entra **cap lletra**, i del que quedava
només passaven els **espais**. Mesurat sobre 400 línies de `agnkrfivlpeuwz`, els símbols que
l'alineador rebia de debò:

```
{'|': 2123, '1': 1}
ⴰⵣⵓⵍ ⵉⵎⴰⵏⵏⴰⵢ ⴷ ⵜⵎⴰⵏⵏⴰⵢⵉⵏ ⵏ ⵜⴱⴰⴷⵓⵜ ⵜⴰⵎⴰⵣⵉⵖⵜ  ->  ['|', '|', '|', '|', '|', '|']
```

Sis símbols per una frase de 44 caràcters, i tots sis el **separador de paraula**. El Viterbi
corria sobre una seqüència de buits. Els 9.295 talls alineats no estaven alineats contra la
frase: estaven alineats contra **els espais que hi ha entre les paraules**.

**Com es va trobar.** No pel resultat, que semblava bo. Buscant per què sis capítols es
quedaven al 97-99 % i no pujaven: els talls que faltaven donaven «cap id», i mirant per què vaig
veure el vocabulari.

**El transliterador ja el teníem.** `rica()`, a `tools/lm/kaggle/alineacio_forcada_snrt.py`, fa
exactament la conversió que calia. Amb ell, les mateixes 400 línies passen de **2.150 símbols a
12.169**, i no queda cap caràcter fora del vocabulari.

**Què canvia a les fronteres.** Els 26 talls que hi ha als dos fitxers, comparats un per un:

| | |
|---|---|
| inici | **0,38 s abans** (mediana) |
| final | **0,59 s després** |
| veu que es queda | 2,06 s → **2,95 s** |
| talls amb una frontera que es mou més de 0,2 s | **26 de 26** |

Cap frontera no es queda igual, i el signe és sempre el mateix: **el retall que vaig mesurar
estava tallant veu de debò**.

### Què queda en peu de les §45-47 i què no

**Queda en peu:** el **−0,2235 de CER** sobre 245 talls. És una mesura de sortida, amb el mateix
model i la mateixa referència, i canviant només si el wav va sencer o retallat. Retallar millora,
i millora molt. Això no cau.

**Cau l'explicació.** La §45 deia que el guany venia de treure *una altra persona parlant*, i que
només el model gran «que coneix la llengua» sap que allò no és LA frase. **No pot ser**: el model
no va veure mai la frase. El que funcionava era un detector de buits entre paraules sobre les
emissions del CTC — una mena de VAD barata, no alineació forçada.

**Cau la mesura de les dreceres**, i aquesta és la pitjor. Les §46 i §47 jutgen l'energia i
`torchaudio MMS_FA` comparant-les amb aquestes fronteres, que ara sabem que estaven mal. El «0 %»
de l'energia i el «5 %» del MMS_FA són acords amb una referència falsa, no errors dels mètodes.

I hi ha un indici fort que el **MMS_FA tenia raó**. La §47 el descartava perquè posa l'inici
−0,37 s i el final +0,54 s. L'alineació bona, respecte de la trencada, posa l'inici **−0,38 s** i
el final **+0,59 s**. Diferència: **0,01 s i 0,05 s**. El MMS_FA —300 M, 1,43 s per tall contra 7—
coincidia amb l'alineació bona, i jo el comparava amb la dolenta i el llençava.

Això és un indici, no una mesura: surt de comparar medianes de dues mostres diferents. **La mesura
s'ha de fer** enfrontant MMS_FA amb les fronteres noves sobre els mateixos talls. Si es confirma,
l'alineació de tot el corpus passa de ~36 h a ~8 h.

**El que no sabem i abans crèiem que sí:** quant del so no és la frase (el «51 %» surt de les
fronteres trencades, i amb les bones la veu que es queda creix de 2,06 a 2,95 s), i si el soroll
dels extrems és una altra persona parlant o simplement so.

> ⚠️ La primera d'aquestes dues preguntes té resposta: **17-20 %** amb el marge de 0,15 s, i les
> dues fonts de fronteres bones hi coincideixen sobre els mateixos talls (**§50**). La segona
> segueix oberta. I la mesura que aquesta secció demanava —MMS_FA contra les fronteres noves
> sobre els **mateixos** talls— també és a la §50: **59 % a ≤0,2 s, desacord median de 0,040 s**.

### Arreglat

* `rica()` davant del vocabulari als quatre alineadors (l'ECS i els tres del PC);
* **una comprovació que peta a l'arrencada** si el text no arriba al vocabulari — amb «azul
  tamaziġt» en tifinag, que ha de donar 13 símbols i 12 que no siguin el separador. Això és el
  que faltava: l'error va córrer 22 h sense dir res, perquè escrivia fronteres perfectament
  plausibles;
* els quatre fitxers vells **no s'esborren**: es diuen `*_NOMES_SEPARADORS.jsonl`, perquè
  `retalla.py` no els pugui fer servir sense adonar-se'n i perquè la comparació es pugui refer;
* l'alineació torna a córrer des de zero: 19.422 talls.

**La lliçó, que no és nova.** Un resultat que surt bo no prova que el camí sigui el que et
penses. El −0,2235 era prou gran per no fer-me mirar què rebia el model, i no el vaig mirar fins
que una altra cosa —sis capítols encallats al 97 %— em va obligar. Aquí la mesura del resultat era bona i **la mesura del
mecanisme no existia**.

---

## 49. El CER d'inferència premia escurçar el so, no encertar la frontera (23-11)

La §48 va deixar una pregunta oberta: amb les fronteres bones el guany del retall baixa de
**−0,2235** a **−0,0741**. Per què les fronteres **dolentes** donaven un número millor?

**La sospita.** El CER del so sencer és **1,05**. Per sobre d'1 vol dir que l'ASR transcriu *més*
del que diu la frase: la distància està dominada per **insercions**. I aleshores qualsevol cosa
que escurci el so en treu, encerti la frontera o no.

**La prova.** El mateix model, la mateixa referència i les **mateixes fronteres bones**, canviant
només el marge. Un marge negatiu retalla **endins**, cap a veu que sabem que hi és:

| condició | so que queda | CER sencer | CER retallat | diferència | millora |
|---|---|---|---|---|---|
| fronteres trencades, +0,15 (§45) | 59 % | 1,0818 | 0,8583 | **−0,2235** | 77 % |
| fronteres bones, **−0,30** | 62 % | 1,0551 | 0,8638 | **−0,1913** | **80 %** |
| fronteres bones, +0,15 | 82 % | 1,0479 | 0,9738 | **−0,0741** | 57 % |

**Menjar-se 0,3 s de veu de cada banda millora el CER quasi tres vegades més que retallar bé**, i
millora el 80 % dels talls en lloc del 57 %. L'ordre de la taula segueix el **so que es llença**,
no l'encert de la frontera.

Hi ha més senyal en el mateix sentit. Sobre els 91 talls de la condició bona, la correlació entre
*quina fracció del so es treu* i *quant baixa el CER* és **r = −0,41**; el terç que es retalla
menys (5 % del so) baixa **−0,034** i el terç que es retalla més (35 %) baixa **−0,143**.

**Conclusió: el CER d'inferència no és un jutge vàlid per al retall.** No mesura si hem trobat la
frase; mesura quant de so hem tret. El «guany més gran del projecte» d'ahir era el premi per
haver llençat el 41 % del so, i si el criteri fos aquest, el màxim s'obtindria retallant-ho tot.

### Què se'n salva, i què s'ha de fer

El retall **pot** ser bo: no ho sabem. El que sabem és que **aquesta mesura no ho pot dir**.

L'única pregunta que té resposta és la que l'experiment ja escrit fa: **entrenar** dues vegades,
amb talls sencers i amb talls retallats, i mesurar sobre un **test sempre sencer i el mateix als
dos costats**. Aquí l'escurçament no pot fer trampa, perquè el que es compara és què ha après el
model, no quant de so li has donat a transcriure.

Això ja era al guió `tools/snrt/magatzem/kaggle/retall-sencer-contra-retallat.py` — el test hi va
sencer per disseny. El que ha canviat avui és que ha deixat de ser *la confirmació* d'un resultat
i ha passat a ser **l'únic lloc d'on pot sortir el resultat**.

**Cautela que queda oberta:** qualsevol comparació anterior feta transcrivint so retallat contra
so sencer té el mateix biaix, inclòs el diagnòstic del 18-11 (0,7370 → 0,6581) que era el guany
de referència del projecte. Allà el CER de partida era **0,74**, per sota d'1, i el biaix per
insercions hi és molt més petit — però no s'ha comprovat, i no es pot citar com si s'hagués fet.

**Els guions:** `prova_retall/mesura.py` (ara el marge i el fitxer d'alineació es passen per la
línia d'ordres, que és el que ha permès fer aquesta prova), `prova_retall/prova_el_jutge.py` (el
escombrat de marges amb una sola càrrega del model).

---

## 50. Del so, el que no és la frase és el 17-20 %, no el 51 % (23-11)

La §48 va retirar el número que sostenia tota la feina del retall —«el 51 % del so no és la
frase», amb 0,79 s al davant i 0,97 s al darrere— perquè el va donar una alineació que no va
rebre mai la frase, i va deixar la pregunta oberta. Avui té resposta, i no necessita ni model ni
CER: **són aritmètica sobre les fronteres**, i ara n'hi ha de dues fonts independents corrents
alhora.

**Com es mesura.** De cada tall, `[0, veu_ini]` és el cap, `[veu_fi, durada]` és la cua, i el que
es llença de debò és això menys el marge de 0,15 s que fa servir `retalla.py`. Es dona arran de
la frontera i amb marge, perquè el segon és el número que importa i el primer és el que es pot
comparar amb el 51 % retirat.

**Les dues fonts no miren els mateixos talls** —l'ECS va per ordre de capítol i el MMS_FA
reparteix per índex— així que els seus números globals no són comparables entre ells. Sobre la
intersecció sí:

| | talls | fora de la frase | cap | cua |
|---|---|---|---|---|
| MMS_FA (300 M, PC) | 2.587 | 21,8 % arran · **16,5 %** amb marge | 0,32 s | 0,28 s |
| MMS-1b-all (4 GB, ECS) | 5.072 | 31,1 % arran · **25,7 %** amb marge | 0,40 s | 0,41 s |
| *els mateixos talls* | 2.594 | **16,5 %** vs **19,9 %** | 0,17 vs 0,27 s | 0,13 vs 0,21 s |

**La resposta: entre el 17 i el 20 % del so no és la frase**, no el 51 %. El silenci del davant
és de 0,2-0,3 s i el del darrere igual, no de 0,79 i 0,97 s. L'alineació trencada s'inventava
mig segon a cada extrem, i no per atzar: alineant només els separadors de paraula, la primera i
l'última àncora cauen cap endins.

Quadra amb la §49 pel seu compte: allà, amb fronteres bones i marge +0,15, **quedava el 82 %** del
so —és a dir, se n'anava el 18 %—, i amb marge −0,30 quedava el 62 %. Dues mesures fetes per
camins diferents (una comptant segons, l'altra transcrivint) diuen el mateix.

**I de passada, la mesura que la §48 demanava.** Allà el MMS_FA quedava rehabilitat per un
*indici* —dues medianes de mostres diferents que coincidien a 0,05 s— i deia explícitament que
la mesura calia fer-la sobre els **mateixos** talls. Feta: sobre els 2.594 talls comuns, les dues
fronteres cauen a **≤0,2 s en el 59 %** dels talls, amb un **desacord median de 0,040 s** a
l'inici i 0,040 s al final. Quaranta mil·lisegons són **dos fotogrames** de l'alineador. El model
de 300 M i el de 4 GB diuen pràcticament el mateix, i el de 300 M ho diu en 2,2 s per tall en una
màquina ocupada contra 5,9 s del gran en una dedicada.

Això no vol dir que el gran no calgui: el 41 % restant de talls on no coincideixen a 0,2 s pot
ser on hi ha la diferència. Però per muntar l'experiment del retall, les fronteres del MMS_FA
són prou bones i arriben 14 h abans.

### El tros que es llença no és silenci

L'altra meitat de la pregunta de la §48 era si aquest 17-20 % és **una altra persona parlant** o
simplement so i silenci. La part de «silenci» ja es pot contestar sense model, amb energia, i la
resposta és **no**.

De cada tall es mesura el nivell (RMS en dB) del cap `[0, veu_ini − 0,15]`, de la cua
`[veu_fi + 0,15, final]` i d'un **control de dins de la frase de la mateixa durada**. El que
decideix és la distància al control, no el nivell absolut: un estudi i un carrer no tenen el
mateix terra.

| tros | talls | durada mediana | nivell | sota el control |
|---|---|---|---|---|
| control (dins la frase) | 191 | 0,69 s | −20,8 dB | — |
| cap (es llença) | 113 | 0,53 s | −24,8 dB | **3,7 dB** |
| cua (es llença) | 132 | 0,69 s | −25,4 dB | **4,8 dB** |

Mediana de tots els trossos llençats: **4,6 dB per sota del control**. Només l'**11 %** cau 20 dB
o més per sota, que és el que es diria silenci; el **58 %** és a menys de 6 dB del nivell de la
frase.

**Queda descartada una de les tres respostes possibles.** El retall no és «només un estalvi de
còmput sobre silenci»: el que es llença sona, i sona gairebé tant com la frase.

**El que això NO prova, i cal dir-ho.** Aquests clips són televisió: una banda sonora de fons,
música i ambient hi corren **tot el clip**, frase inclosa. Que hi hagi so fora de la frase no vol
dir que hi hagi una altra **veu**; l'energia no distingeix una persona parlant de música, d'un
aplaudiment o del fregadís d'un micròfon. Per això segueix fent falta transcriure el tros
(`prova_retall/que_hi_ha_al_tros_que_es_llenca.py`, escrit i encara sense córrer: el primer
intent el va matar el sistema per manca de memòria, per haver-lo apilat sobre tres alineadors).

I hi ha una lectura incòmoda que aquesta mesura obre: si just a fora de la frontera hi ha so a
nivell de veu, una frontera que falli per poc fa que el retall es mengi **paraules del parlant**.
El desacord median entre les dues fonts és de 0,040 s, que no fa mal, però el 41 % de talls on
discrepen més de 0,2 s sí que en pot fer. El marge de 0,15 s existeix justament per això.

**El guió:** `tools/snrt/magatzem/hi_ha_so_al_tros_que_es_llenca.py`. Cap model, un segon.

**El guió:** `tools/snrt/magatzem/quant_del_so_no_es_la_frase.py`. No carrega cap model i triga
un segon; es pot tornar a passar cada vegada que creixin els fitxers d'alineació, i els números
d'aquesta secció es refaran amb el corpus sencer.

---

## 51. La via 3 amb tot el material: el TutlAit és àrab de debò (23-11, d'en Pablo)

La pregunta la va fer en Pablo: si l'objectiu és traduir veu amaziga, per què la via 3 (veu →
àrab escrit, §39) s'entrena només amb la SNRT, quan hi ha corpus públics que són exactament
aquesta tasca? No hi havia cap bona raó. La via 3 es va muntar com un experiment sobre la SNRT i
va quedar així.

**El dubte que calia treure abans.** El TutlAit es va recollir de dues maneres: gent llegint en
amazic una frase àrab (parella de traducció) i gent escrivint amb lletres àrabs el que sentia
(transliteració). La segona mena ensenyaria al model el vici que li volem treure —el Whisper
sense afinar ja escriu `أزول` per «azul»—. Es distingeix sense model: una frase àrab de debò
porta paraules funcionals àrabs (article, preposicions, demostratius) que l'amazic no té.

| | frases | amb paraula funcional | amb article |
|---|---|---|---|
| TutlAit | 13.262 | **80 %** | **63 %** |
| SNRT (control: àrab escrit per persones) | 3.815 | 79 % | 61 % |

Indistingibles: **és traducció.**

**El corpus combinat** (`corpus_veu_arab_combinat.py`; només manifests, no copia so):

| | files | hores | SNRT | TutlAit |
|---|---|---|---|---|
| train | 15.427 | **21,4** | 6.069 | 9.358 |
| dev | 1.972 | 2,2 | 1.355 | 617 |
| test_snrt | 2.091 | 2,8 | 2.091 | — |
| test_tutlait | 547 | 0,8 | — | 547 |

Entrenament per varietat: tzm 10,3 h · shi 3,8 h · SNRT sense etiqueta 7,4 h.

Tres coses vigilades, perquè totes tres ja ens havien mossegat:

* **cap parlant del TutlAit és a dos costats** de la seva partició (47 / 23 / 35): comprovat, zero;
* **la fuita per text**: al TutlAit molta gent llegeix les mateixes frases. S'han tret de
  l'entrenament **1.395 files** (1.300 del TutlAit, 95 de la SNRT) amb un àrab que, normalitzat,
  surt en algun dev o test. Sense això el test del TutlAit hauria mesurat memòria;
* **els tests no es barregen**: `test_snrt` segueix comparable amb la via del text i
  `test_tutlait` amb l'article del TutlAit.

**Un número que no era el que es deia.** El comentari del quadern de Kaggle diu que la part de
la SNRT té 10.684 talls d'entrenament i 12,7 h. Al disc n'hi ha **6.164 i 7,4 h** (manifests
del 21-11 a les 12:19). El 23-11 vaig repetir el número del comentari a en Pablo sense mirar el
disc. No sé d'on surt la diferència; el que val és el que hi ha al disc.

**El que queda fora i hi pot entrar:** el corpus d'EMINES (`Tamazight-Speech-to-Arabic-Text`,
~15,5 h de taixelhit), que no tenim baixat; **Baba Ali**, 3.621 parelles so ↔ àrab del Souss que
ja són al catàleg amb la mateixa forma que el TutlAit (sense text amazic, amb l'àrab del
subtítol); i les **sèries de Tamazight TV**: 954 capítols, 284 h al canal de YouTube
(`tamazight-tv.md`), catalogades el 17-11 i mai collides. Per a aquesta via no cal el tifinag
—que és el que obliga a baixar a 1080p—, només la línia àrab, l'hora i el so. A partir d'un sol
capítol mesurat (Illy 1: 306 rèpliques en 30 min) poden ser unes 70-80 h de parla subtitulada;
és una estimació d'un capítol, no una mesura.

> Esmena del mateix dia: aquí deia «67 h de programes de la SNRT amb subtítol només en àrab».
> Era un número copiat del comentari de `corpus_veu_arab.py` que no he sabut trobar d'on surt;
> el que hi ha documentat és el catàleg de sèries de dalt.

**I el canvi d'ordre que això porta.** La via 3 no ha corregut mai, ni una vegada, mentre tres
dies anaven a afinar on es retalla cada tall. No cal esperar l'alineació per llançar-la: amb els
talls sencers ja dona el primer número d'extrem a extrem del projecte, i el retall passa a ser
una variant que es jutja amb aquest mateix número —que és de durada fixa i per tant no té el
biaix de la §49.

**Els guions:** `tools/snrt/magatzem/quin_arab_es_el_del_tutlait.py` i
`tools/snrt/magatzem/corpus_veu_arab_combinat.py`.

## 52. EMINES és traducció, però no és un test: la meitat del que sembla nou ja ho teníem (23-11)

**La pregunta:** el pas 2 del pla volia afegir EMINES (20.344 talls, 15,5 h) al model veu → àrab.
Abans calia saber dues coses: si és traducció o transliteració, i si s'encavalca amb el nostre.

**Traducció.** 77,8 % de frases amb paraula funcional àrab i 50,3 % amb article, contra el 79 %
i 61 % del control de la SNRT. És àrab de debò, amb frases més curtes (diàleg de sèrie).

**L'encavalcament**, llegint només el text i les metadades de Hugging Face (`emines_text.py`, cap
àudio baixat) i comparant per text normalitzat (`norma()`):

| font nostra | files | idèntiques a EMINES | de 4 paraules o més |
|---|---|---|---|
| TutlAit · spk_010 | 2.355 | **755 (32,1 %)** | **642** |
| Baba Ali | 3.571 | 166 (4,6 %) | 31 |
| TutlAit · spk_006 | 3.432 | 47 (1,4 %) | 6 |
| SNRT | 9.515 | 56 (0,6 %) | 3 |
| la resta del TutlAit | | ~0 | 0 |

Fora de `spk_010`, les coincidències són fórmules («إنا لله وإنا إليه راجعون», «بسم الله…»).
**`spk_010` és el mateix material**: frases de 4 paraules o més que coincideixen al 27 %, repartides
per tots els 60 vídeos, no pot ser casualitat. El TutlAit les va agafar de la mateixa sèrie o
d'EMINES mateix.

**I dins d'EMINES:** els vídeos 37/38 (93 %), 39/40 (100 %) i 41/42 (90 %) són el mateix vídeo dues
vegades, i la seva partició train/test reparteix tots 60 vídeos entre les dues. **El test d'EMINES
no és un test.** Qui publiqui un número sobre aquell test mesura frases que el model ja ha vist.

**El que se'n fa:** EMINES va **tot a l'entrenament** (`corpus_emines_veu_ar.py`): es treuen els
vídeos 38, 40 i 42 (938 files), els talls de menys de 0,5 s (15) i tota frase el text de la qual
surti a dev o a un test nostre (178). Queden **19.213 files, 14,6 h**. `spk_010` ja era a train,
així que l'encavalcament no toca els tests congelats; vol dir només que **les 14,6 h no són totes
material nou**: unes 750 frases ja hi eren amb una altra veu (o la mateixa).

**Llicència:** Apache 2.0, apuntada a CREDITS. L'àudio és WAV a 44,1 kHz estèreo; el quadern de la
3a tirada (`veu-ar-afina-emines.py`) el baixa de Hugging Face dins de Kaggle i el passa a 16 kHz.

**Pendent:** la 3a tirada, quan Kaggle alliberi una sessió de GPU per lots, comparada amb la 2a
sobre els mateixos tests.

## 53. La 2a tirada: Baba Ali no mou els tests, i el model encara no havia acabat d'aprendre (23-11)

**Què es va fer:** el mateix quadern que la 1a tirada (Whisper small, 3 èpoques, mateix dev i
mateixos tests congelats) amb Baba Ali afegit a l'entrenament: 18.998 files, 26,1 h, contra les
15.427 files i 21,4 h de la 1a. Sortida desada a `E:/tamazight/_magatzem/tirades/veu_ar_2/`.

| | abans (200) | després (les mateixes 200) | test sencer 2a | test sencer 1a |
|---|---|---|---|---|
| test_snrt | 0,1126 | 0,1836 | **0,1652** | 0,1656 |
| test_tutlait | 0,1191 | 0,1923 | **0,1942** | 0,1892 |

Dev (200 SNRT + 200 TutlAit) per època: 0,1080 → **0,1450 → 0,1745 → 0,1837**.

**El que diu:**

* **Baba Ali no canvia res que es pugui mesurar** (−0,0004 i +0,005). Són 4,7 h d'una sola sèrie
  amb 3.571 frases: massa poc i massa d'un sol lloc per moure un test de 2.091 frases d'altres
  programes. No fa mal i s'hi queda.
* **El dev encara pujava a la 3a època** (+0,009 de la 2a a la 3a). El model no ha tocat sostre:
  amb aquest material, **més passades hi guanyarien** abans que més dades d'una sola sèrie. La
  3a tirada (EMINES) dobla les passos per època sense canviar el nombre d'èpoques, i ho dirà.
* **Tots dos tests continuen lluny de 0,26**, la via del text sense afinar. La via directa encara no
  guanya la cadena.

**20 traduccions llegides a ull** (llavor 1114, 10 de cada test):

* **Ara escriu àrab de debò, no transliteració.** Les frases curtes i fetes surten bé: «هيا بنا» →
  «هيا لنذهب»; «ها هي العمارة…» → «ها هو العمارة، لكنه…». Agafa els noms (أنير, فاطمة, القاضي عبو)
  i paraules soltes (الطيب, الأدب الأمازيغية, طلبات الباحث).
* **El sentit de les frases llargues gairebé mai.** «الطقس اليوم معتدل…» surt com una frase àrab
  correcta que no hi té res a veure.
* **Bucles**: 2 de 20 acaben repetint una paraula fins a 180 fitxes («تسيارة تسيارة…», «أمامي أمامي…»).
  Penalitzen el chrF i no tenen res a veure amb l'oïda del model. La 3a tirada mesura també, com a
  número **secundari**, el mateix test descodificant sense repetir trigrames (`no_repeat_ngram_size=3`).
* **Les referències de la SNRT porten errors de lectura** («نجربة» per «تجربة», «الآدب»): part del
  sostre de test_snrt és soroll de la referència, no del model.

## 54. La 3a tirada: EMINES sí que mou els tests, i el model encara puja (24-11)

**Què es va fer:** el quadern de la 2a tirada amb EMINES afegit només a l'entrenament (§52):
38.211 files, unes 40,7 h. Whisper small, 3 èpoques, mateix dev i mateixos tests congelats. Va
córrer a l'editor de Kaggle (sessió interactiva, persistència «Files only»), en unes 6 h. Com a mesura
**secundària** es tornen a puntuar els tests sencers descodificant amb `no_repeat_ngram_size=3`.

| | abans (200) | després (les mateixes 200) | test sencer 3a | 2a | 1a | 3a sense bucles |
|---|---|---|---|---|---|---|
| test_snrt | 0,1126 | 0,2026 | **0,1815** | 0,1652 | 0,1656 | 0,1986 |
| test_tutlait | 0,1191 | 0,2175 | **0,2199** | 0,1942 | 0,1892 | 0,2348 |

Frases amb chrF ≥ 0,5: test_snrt 44/2.091 (46 sense bucles), test_tutlait 27/547 (30).

Dev (200 SNRT + 200 TutlAit) per època: **0,1673 → 0,1954 → 0,2075**. A la 2a tirada era
0,1450 → 0,1745 → 0,1837.

**El que diu:**

* **EMINES sí que hi guanya, a tots dos tests:** +0,016 a test_snrt i +0,026 a test_tutlait. Baba
  Ali no havia mogut res (§53). EMINES són 14,6 h de 60 vídeos de temes i veus diferents, i no una
  sola sèrie.
* **Cal llegir test_tutlait amb prudència.** El spk_010 del TutlAit i EMINES comparteixen frases
  (§52). spk_010 és a train i no al test, i les frases d'EMINES que eren a dev o test es van treure
  pel text normalitzat. Tot i així, és la mateixa casa.
* **El dev encara puja a la 3a època** (+0,012). El model no ha tocat sostre. La 4a tirada continua
  des d'aquest punt de control amb 2 èpoques més (les que caben en la quota) (`tools/snrt/magatzem/kaggle/veu-ar-afina-continua.py`).
* **Prohibir repetir trigrames val +0,017 i +0,015.** És una mesura secundària, i la principal
  queda com abans. A la 2a tirada, plegar els bucles després (`tools/snrt/magatzem/bucles_a_posteriori.py`)
  hi guanyava +0,010 i +0,006, i 942 de 2.091 frases de test_snrt tenien alguna repetició.
  Per servir el model, `no_repeat_ngram_size=3` és un guany gratuït.
* **Encara lluny de 0,26**, la via del text sense afinar.

**20 traduccions llegides a ull** (llavor 1114, 10 de cada test):

* **TutlAit, frases curtes i fetes: bé o gairebé.** «يتوجّب عليك الذهاب» → «يجب عليك أن تذهب إلى هناك»;
  «و ما ماذا ستفعل» → «ماذا ستفعلين؟»; «انت لم تذهب الى السوق لترى ثمن الماشية» → «…لكي تذهب للسوق
  لترى من أين أصبحت البهائم». Agafa el tema (el mercat, el bestiar) i en part l'estructura.
* **Els noms i el tema, sí; el sentit de la frase llarga, encara no.** «القاضي عبو حمو و أمه يموتون» →
  «قاضي عبو ، أمي و أمي…». Les frases llargues del TutlAit surten com a àrab que no hi té res a veure.
* **SNRT, gairebé tot fora.** De 10, només «سنبدأ بك أولا، السيد الطيب» → «سنعرفه بأنه صديقه الطيب» s'hi
  acosta. En 2 de 10 encara surten paraules amazigues transliterades («تيزي تيزي», «توسيمت»).
* **Bucles en 3 de 20** («ويجب أن يتجمع لها أول مرة» ×3, «الناس الذين يحضرون» ×2).

**On és el model:** a `/kaggle/working/millor` del quadern `veu-ar-afina-emines` (persistència
«Files only»). Una sessió interactiva no deixa sortida de kernel, i `kaggle kernels output` torna
buit. Per això la 4a tirada s'enganxa en aquell mateix quadern, i el primer que fa és copiar el model
de la 3a a `model_3a/`.

## 55. La 4a tirada: dues èpoques més mouen el TutlAit, no el dev (24-11)

**Què es va fer:** es va continuar des del millor punt de control de la 3a (§54), amb el mateix
material, 2 èpoques més i escalfament de 50 passos. Va córrer al mateix quadern de l'editor, on
també hi ha el model de la 3a (`model_3a/`). Durada: 4 h 38 min.

| | 3a, les mateixes 200 | 4a, les mateixes 200 | test sencer 3a | **test sencer 4a** | 4a sense bucles |
|---|---|---|---|---|---|
| test_snrt | 0,2030 | 0,2067 | 0,1815 | **0,1846** | 0,2011 |
| test_tutlait | 0,2175 | 0,2430 | 0,2199 | **0,2387** | 0,2471 |

Frases amb chrF ≥ 0,5: test_snrt 41/2.091 (abans 44) i test_tutlait 37/547 (abans 27).

Dev per època: el punt de partida, tornat a puntuar, dona 0,2075. Després **0,2056 → 0,2101**.

**El que diu:**

* **El dev gairebé no es mou** (+0,003 en dues èpoques). Amb aquest material i Whisper small, el
  model és a prop del sostre. Més passades amb les mateixes dades ja no valen la GPU.
* **Tot i així, test_tutlait puja +0,019**, i les frases bones passen de 27 a 37. test_snrt amb prou
  feines es mou (+0,003). El que encara aprèn és el registre del TutlAit, que és curt i quotidià,
  i el més semblant a EMINES. La notícia de la SNRT, no.
* **La 4a és el millor model fins ara**, i el sense bucles (0,2011 / 0,2471) és el que s'hauria
  de servir. Continua per sota de 0,26, la via del text sense afinar.
* **El pas següent no és més èpoques.** Les opcions són més so de la SNRT o d'altres programes
  (el SNRT de test és on falla), o un model més gran (Whisper medium).

**A ull** (llavor 1114, test_snrt): gairebé les mateixes sortides que la 3a, una mica més
netes («سنأخذها لكي نسميها الطيب»). Un bucle llarg nou: «أمازيغ أمازيغ…».

**On és el model:** `/kaggle/working/millor` del quadern `veu-ar-afina-emines`, al costat de
`model_3a/`.

## 56. La cadena real des del so, i qui tradueix de debò el tifinag (24-11)

**Què faltava:** el 0,2614 / 0,2634 que fèiem servir com a «via del text» tradueix el subtítol
**escrit**: és la cadena amb una transcripció perfecta. La cadena des del so (so → ASR → tifinag →
NLLB → àrab) no s'havia mesurat mai.

**Com s'ha mesurat:** sobre les mateixes files que el model directe i amb el mateix chrF
(`chrf(hip, ref)`, beta 2, el dels quaderns de la via 3).
- **ASR:** MMS-1b-all amb l'adaptador `shi` del Space (`adaptador_shi_zouhir_b.pt`), en llatí
  (`kaggle/veu-ar-cadena-asr.py`).
- **Del llatí al tifinag:** `backend/transliteration.to_forms`.
- **Traductor:** el NLLB de Tamazight-NLP sense afinar (`kaggle/veu-ar-cadena-tradueix.py`). El NLLB
  afinat a 0,3470 (§43) no es pot recuperar: la sortida del kernel `zgh-ar-afina` ja no té el model.
  Amb el NLLB-ca local (`cadena_tradueix.py text`), el text de la pantalla dona 0,2772, pràcticament
  el mateix.

| test_snrt (2.091) | chrF |
|---|---|
| text de la pantalla → NLLB (sostre de la cadena) | 0,2778 |
| **so → ASR → NLLB** | **0,1828** |
| so → àrab directe (4a tirada, §55) | 0,1846 · sense bucles **0,2011** |

| test_tutlait (547) | chrF |
|---|---|
| **so → ASR → NLLB** | **0,2112** |
| so → àrab directe (4a tirada) | 0,2387 · sense bucles **0,2471** |

L'ASR, contra el tifinag de la pantalla: **CER mitjà 0,673, mediana 0,571** (2.005 files amb text).
El so de la tele s'equivoca en més de la meitat de les lletres.

**El que diu:**

* **El model directe ja iguala o guanya la cadena real.** Al SNRT empaten (0,185 i 0,183), i
  descodificant sense bucles el directe guanya per +0,018. Al TutlAit guanya per +0,03.
* **L'ASR es menja gairebé tot el marge del text.** De 0,278 amb el text perfecte a 0,183 des
  del so. La baula feble de la cadena és l'orella, no el traductor.
* **Una reserva:** la cadena fa servir un traductor sense afinar. Un NLLB afinat hi afegia
  +0,08 sobre text (§43). Des del so en guanyaria menys, però podria tornar a passar el directe
  al SNRT. Cal refer el NLLB afinat i desar-lo fora de Kaggle abans de tancar-ho.

### Qui tradueix el tifinag a l'àrab: una prova a cegues amb 40 línies

40 línies del test net de text (`zgh_ar/test.jsonl`, llavor 1114, de 3 paraules o més), traduïdes
sense veure l'àrab de referència. Totes contra la mateixa referència, amb el mateix chrF:

| qui tradueix | chrF | ≥ 0,5 |
|---|---|---|
| NLLB-ca, punt de partida | 0,333 | 5/40 |
| Gemini 2.5 Flash | 0,384 | 10/40 |
| **jo (Claude), a cegues** | **0,406** | 8/40 |
| **Gemini 2.5 Pro** | **0,443** | 13/40 |

Diferència meva contra el NLLB: +0,072 [+0,020, +0,129].

* **Els models grans tradueixen millor el tifinag que el NLLB**, però no gaire: 0,41-0,44, no 0,75.
  El 0,746 de §36 era àrab → català, una parella amb moltíssimes dades.
* **El sostre és baix per a tothom per la referència.** L'àrab de la SNRT surt de l'OCR, amb
  errors («نجدبة», «التدجمة», «جننبا»), i és una traducció lliure: una traducció correcta i
  paraulejada diferent puntua 0,4-0,6. Per sota de 0,3, en canvi, el sentit falla. El NLLB
  confon paraules senceres (مرآة → «سائحة»).
* **Per què el NLLB, amb tants diccionaris, no arriba més amunt:** els diccionaris són paraules, i
  un traductor aprèn de frases aparellades. N'hi ha unes 4.500 del SNRT. Un model gran porta molt
  d'àrab i una mica d'amazic de casa, i encerta pel context i pels manlleus («ssusyuluji»).
* **Conseqüència per al producte:** per traduir text, avui el millor que tenim a l'abast és
  **Gemini 2.5 Pro**, i l'app ja hi té clau. El NLLB propi queda com a recanvi sense cost i sense
  connexió. Falta provar-ho amb els diccionaris dins la petició, sobre més línies.

Fitxers: `E:/tamazight/_magatzem/tirades/cadena/` (`cadena_text.json`, `cec_claude_40.json` amb
les quatre traduccions de cada línia).

## 57. Gemini 2.5 Pro tradueix el tifinag millor que el NLLB; els lèxics hi ajuden poc (24-11)

**Què es va fer:** 200 línies noves del test net de text (`zgh_ar/test.jsonl`, llavor 2026, de 3
paraules o més, sense les 40 de §56). Tifinag → àrab amb tres sistemes, sobre les mateixes línies i
amb el mateix chrF. Gemini en lots de 20 línies, temperatura 0,2 i pensament de 2.048 fitxes
(`tools/snrt/magatzem/gemini_amb_lexic.py`).

| sistema | chrF | ≥ 0,5 |
|---|---|---|
| NLLB-ca (punt de partida) | 0,2767 | 16/200 |
| Gemini 2.5 Pro | 0,3490 | 42/200 |
| **Gemini 2.5 Pro + lèxics** | **0,3566** | **44/200** |

| diferència | mitjana [interval 95 %] |
|---|---|
| Gemini Pro − NLLB | **+0,072** [+0,053, +0,093] |
| Gemini Pro + lèxics − NLLB | **+0,080** [+0,060, +0,102] |
| amb lèxics − sense | +0,008 [−0,008, +0,022] |

Els lèxics són els de `backend/lexicon.grounding_lines`, els que ja fa servir el tutor: Oulhaj,
IRCAM-DGLAI, conjugacions IRCAM i Wikimawal, fins a 12 entrades per línia.

**El que diu:**

* **Gemini 2.5 Pro guanya el NLLB amb claredat.** La millora de §56 aguanta amb cinc vegades més
  línies, i les frases bones passen de 16 a 42.
* **Els lèxics no mouen el número de manera mesurable** (l'interval creua el zero). A ull, però,
  arreglen paraules concretes: «بالتوابل» → «**بالنعناع**», «التأثير» → «**الضغط**», i el nom
  «أيت إعزة». Ajuden on la paraula és rara i el diccionari la té, i són una gota dins del total.
* **Encara no és publicable.** «سأحدي للأساتذة الكرام مقطوعة» surt «لأحيي أساتذتنا», amb el sentit
  general bé i la meitat de la frase perduda. Serveix com a proposta perquè una persona la corregeixi.
* **Per al producte:** per traduir text, el primer de la fila ha de ser Gemini 2.5 Pro amb els
  lèxics. No costen res, no fan mal i arreglen noms i paraules rares. El NLLB queda com a recanvi.
  Per a la veu, el model directe ja iguala la cadena (§56).

Fitxer: `E:/tamazight/_magatzem/tirades/cadena/gemini_amb_lexic.json`.


## 58. Triangulació: l'acord de l'ASR amb la pantalla assenyala els triplets dolents, no els bons (25-11)

**La pregunta (#763):** quan l'ASR, que només sent el so, escriu el mateix que el tifinag cremat a
la pantalla, que ningú no li ha dictat, el triplet so–amazic–àrab és més coherent? Si sí, l'acord
seria un filtre per fabricar dades d'entrenament sense parlant.

**Què es va fer:** ASR (mms-1b-all + `adaptador_shi_zouhir_b`) sobre els 2.091 talls de
`test_snrt`, a Kaggle en fp16. Contra els 605 talls fets a casa en fp32, el CER coincideix en 595 i
difereix 0,08 punts de mitjana: la precisió no hi compta. Per tall: CER entre la sortida
transliterada al tifinag i el tifinag de la pantalla. **Coherència** = chrF de la traducció NLLB del
tifinag de pantalla (§56) contra el subtítol àrab del mateix fotograma. **Control barrejat** = la
mateixa traducció contra l'àrab d'un altre tall. 1.966 talls amb tifinag de 4 lletres o més i ASR
no buit (`tools/snrt/magatzem/triangulacio.py`).

| CER ASR↔pantalla | talls | coherència [IC 95 %] | barrejat |
|---|---|---|---|
| < 0,10 | 46 | 0,320 [0,271, 0,374] | 0,105 |
| 0,10–0,20 | 165 | 0,322 [0,295, 0,351] | 0,123 |
| 0,20–0,35 | 293 | 0,320 [0,301, 0,339] | 0,122 |
| 0,35–0,50 | 320 | 0,298 [0,281, 0,318] | 0,129 |
| 0,50–0,75 | 511 | 0,299 [0,287, 0,313] | 0,121 |
| ≥ 0,75 | 631 | **0,263** [0,251, 0,275] | 0,117 |

Spearman(CER, coherència) = **−0,139** [−0,183, −0,092]. Per tercils de llargada, l'acord alt
(CER < 0,2) contra la resta: curtes **+0,073** [+0,027, +0,124], mitjanes −0,003 [−0,042, +0,039],
llargues +0,030 [−0,007, +0,064].

**El que diu:**

* **El senyal existeix però és feble i va per un sol costat.** Fins a CER 0,35 la coherència és
  plana (0,32); el que cau és el terç de talls on l'ASR no s'assembla gens a la pantalla (0,263). Hi
  ha tall equivocat, so que no és la frase o un ASR perdut, i l'àrab d'aquell tall també encaixa pitjor.
* **No hi ha una «franja d'or».** Els 211 talls amb CER < 0,2 (10,7 %) no són més coherents que els
  de 0,2–0,35. Part de la raó és la regla de mesura: el NLLB arriba a 0,32 com a màxim, i per sobre
  d'aquí no pot distingir una línia bona d'una de perfecta. Amb Gemini Pro (§57) potser sí.
* **Per tant serveix com a filtre negatiu, no positiu:** treure del train el terç amb CER ≥ 0,75, no
  quedar-se només amb l'acord perfecte, que llençaria el 90 % de les dades.
* **Encara no està provat que millori cap model.** El pas següent és mesurable: ASR sobre el train
  del SNRT (6.164 talls), entrenar la via 3 sense el terç pitjor contra sense un terç a l'atzar de la
  mateixa mida, i jutjar-ho sobre els tests congelats.

Fitxers: `E:/tamazight/_magatzem/tirades/triangulacio/` (`cer_kaggle_test.txt`, `coh_test.json`,
`triangulacio_test.json`).
