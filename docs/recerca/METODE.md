# El magatzem de la paraula sentida

*Mètode per anar desxifrant la parla a poc a poc, sense llençar res. 19-11-2026.*

Escrit a partir de l'encàrrec d'en Pablo del 19-11-2026: «pots escoltar amb el nostre model i
determinar que molt probablement estàs escoltant bé; pots catalogar el que escoltes amb un índex
de fiabilitat per paraula; no ho fas al buit, la transcripció en tamazight estàndard et dona
pistes; quan tinguem molta dada podràs reprocessar-la; comença pels sons més clars».

## 1. Per què això i no el cercle d'ara

El cercle virtuós demana al model que aprengui de parelles so↔text on el text **no és el que es
diu**: els subtítols de la SNRT són la norma de l'IRCAM i l'actor parla dialecte. Mesurat el
19-11-2026: després d'alinear, el CER d'esquelet es queda a 0,705 i només 175 de 589 talls
baixen de 0,5. Entrenar-hi no mou res.

La sortida no és un text millor. És **deixar de necessitar que el text sigui veritat**. El
subtítol passa de ser la resposta a ser **un testimoni més**, i el que decideix és l'acumulació.

## 2. La unitat és la paraula sentida, no la línia

Una línia barreja trossos segurs i trossos impossibles, i tractada sencera els iguala pel pitjor.
El magatzem guarda **ocurrències de paraula**. Cada ocurrència és una vegada que una paraula
s'ha sentit, en un lloc concret d'un so concret.

Cada ocurrència porta:

| camp | què és |
|---|---|
| `so`, `de`, `a` | d'on surt i en quin segon: permet **tornar-hi** amb un model millor |
| `sentit` | el que el model va escriure |
| `conf` | la confiança acústica d'aquella paraula (del CTC, no de la línia) |
| `norma` | la paraula de la norma que li toca al subtítol, si l'alineació la troba |
| `esquelet` | consonants de `sentit`, sense vocals ni ortografia: la clau per agrupar |
| `zona`, `parlant` | d'on és qui parla |
| `model` | **quin model ho va sentir**: sense això no es pot reprocessar |

És un fitxer **que només creix**. Res no es reescriu: una passada nova afegeix ocurrències noves
amb un `model` nou, i les velles es queden. Així una millora del transcriptor no esborra la
història, i es pot preguntar «què en dèiem al novembre?».

## 3. Els quatre graus, i cap no es llença

Això és el «comença pels sons més clars», fet explícit:

- **A — clar i d'acord.** Confiança alta i coincideix amb la norma. És veritat utilitzable:
  entra a entrenar avui.
- **B — clar i NO d'acord.** Confiança alta però diu una altra cosa que el subtítol. Això **no és
  un error**: és una correspondència estàndard ↔ dialecte (el `rad` escrit i el `ad` dit). És el
  material més valuós que tenim i avui es llença com si fos soroll.
- **C — fosc però repetit.** Confiança baixa, però el mateix esquelet surt moltes vegades en
  contextos diferents. La prova no és cap ocurrència: és la **coincidència entre ocurrències**.
  Aquí és on es recupera el que en Pablo demana: si una paraula s'ha sentit a mitges en una frase
  i es torna a sentir més clara en una altra, la segona rescata la primera.
- **D — ni clar ni repetit.** Es cataloga i s'espera. Potser d'aquí a sis mesos un model millor
  o vint ocurrències més el pugen a C.

**Cap grau s'esborra.** El que avui és D pot ser A quan el model millori, i només pot ser-ho si
la gravació i el segon hi són apuntats.

## 4. Com es decideix una forma (el rescat per repetició)

Les ocurrències s'agrupen per **esquelet consonàntic**, no per la grafia: la grafia és justament
el que no sabem. Dins d'un grup:

1. es mira si hi ha una forma que surti amb confiança alta en **més d'un parlant i més d'un
   capítol** — si n'hi ha, mana;
2. si no, mana la forma més repetida, i es marca com a **hipòtesi**, no com a fet;
3. la norma del subtítol **no desempata**: hi entra com a columna a part, perquè la pregunta que
   volem respondre és precisament en què es diferencien.

Una hipòtesi es converteix en fet **quan una persona l'ha escoltada**, mai per acumulació sola
(ADR 0003: el text del parlant és seu). El magatzem prepara la feina de la persona i la posa per
ordre de rendiment: primer les formes amb més ocurrències, que són les que més text desbloquegen.

## 5. Què hi entra

Tot el so que tenim, i no només el d'alta concordança:

- els 6.652 parells literals de la biblioteca (text escrit per una persona): són el **patró**,
  serveixen per saber com de fiable és la `conf` del model;
- el so de la SNRT, amb el subtítol com a columna `norma`;
- el que vingui després.

Els de la biblioteca són els que calibren: sabent el que es diu de debò, es pot mesurar quina
confiança correspon a quin encert, i llavors la `conf` de la SNRT vol dir alguna cosa. Sense
aquest calibratge, un 0,9 és un número sense unitats.

## 6. On viu

`E:\tamazight\_magatzem\`

```
ocurrencies.jsonl    una línia per paraula sentida (només creix)
formes.jsonl         una línia per esquelet: les seves ocurrències i el grau
correspondencies.jsonl   norma ↔ dialecte amb el recompte de vegades
passades.json        quin model ha fet cada passada i quan
```

A E: i no a C: perquè això ha de créixer durant anys i a C: hi caben 20 GB.

## 7. Què NO fa

- No publica res: el so de la SNRT és de recerca (permís del 17-11-2026).
- No escriu a la biblioteca pública. El que en surti va a `*_suggested` i ho mira una persona.
- No decideix ortografia. Proposa formes amb proves al darrere.

## 8. El primer pas, i com se sabrà si val

1. Calibrar amb la biblioteca: passar els 6.652 parells pel model i fer la taula
   «confiança → probabilitat d'encert». Sense això no es pot dir «confiança alta».
2. Buidar-hi la SNRT que ja està llegida (6.300 rèpliques) i comptar quants graus A, B, C i D
   surten.
3. La xifra que diu si serveix: **quantes paraules passen de D o C a A** en una segona passada,
   sense que ningú hi hagi escoltat res de nou.

Si aquest número és zero, el mètode no val i s'ha de dir.

---

## 9. El que la nit del 19 al 20 va afegir al mètode

Tres regles, totes tres apreses equivocant-me.

### 9.1 La variació surt de l'ACORD, no del desacord

La idea primera era natural i és dolenta: buscar les diferències norma ↔ parla allà on l'ull i
l'orella **discrepen** (el grau B). Allà és on la informació és més dèbil, i el que s'hi recull
són artefactes: filtrant per repetició en boques diferents només sobreviuen vuit parelles, i
**totes vuit** són la frase *tutlayt tamaziġt* aparellada amb un lloc de desplaçament.

La regla bona és la contrària: **dues formes sentides diferents que casen totes dues amb la
mateixa paraula escrita**, cada una acordada diverses vegades. Això no és un desacord, són dos
acords, i la diferència entre ells és la variació. Així surten 97 parelles i amb elles la llista
de canvis de consonant (ġ~ḫ, k~š, l~r, s~z, ḍ~ṭ, g~y) amb el seu pes.

I l'escapçament es separa de la variació sense opinar: un escapçament és un **tros** de la forma
plena, i el filtre es fa contra la paraula **escrita**, no entre les dues formes — `ns` i `nn`
són tots dos trossos de `nns` i comparats entre ells semblarien un canvi n~s.

### 9.2 Un canvi que l'orella fa sempre no és de la parla

Les parelles de 9.1 barregen dues coses: la variació del parlant i les confusions sistemàtiques
del model. Es separen amb una **segona orella**: si un altre model, entrenat per una altra gent
amb altres dades, sent el mateix, és parla; si només ho sent el nostre, és nostre. Amb una
condició que vaig aprendre fallant-hi: **la mostra ha d'arribar al fenomen**. El ġ~ḫ, amb 37
paraules, el `kab` no el feia cap vegada i vaig concloure que era nostre; amb 377 el fa al 7,7 %
i el `shi` al 6,6 %, o sigui que és de la parla. Zero de 37 no vol dir zero.

### 9.3 Una marca que es concentra val més que una que es reparteix

Un canvi que apareix per igual a tots els episodis és del model. Un que es concentra en uns
parlants és d'ells, i llavors el número no diu només que la variació existeix: diu **qui parla
com**. Aquesta és la mesura que val, i la que va portar a la hipòtesi del rifeny: k→š i l→r
correlacionen entre elles (+0,58) i amb l'acord (−0,46), i assenyalen els mateixos deu convidats.

### 9.4 I la regla que les sosté totes

Set hipòtesis meves van morir aquesta nit i cap no era absurda: totes eren raonables. El que les
va matar sempre va ser el mateix — **mesurar-les amb un testimoni que no hi tingués interès**.
Cada vegada que vaig triar per raonament (el tifinag «perquè és la llengua del programa»,
rellegir «perquè el text és vell», la plantilla amb més IoU, la llargada de la frase perquè ho
semblava en vuit exemples) em vaig equivocar. Cada vegada que vaig deixar decidir l'orella,
l'àrab, la topologia o un model d'uns altres, va sortir bé.

**El mètode no és tenir bones idees. És tenir un àrbitre.**

## 10. Una nota d'ofici que val una nit

Els guions del magatzem feien la feina **a nivell de mòdul**, de manera que importar-ne un per
fer servir `esquelet()` tornava a escriure `text_triat.jsonl` en silenci. Durant hores cada
anàlisi refeia el corpus pel camí, i si una hagués fallat a mitges hauria deixat el fitxer
truncat sota els peus de la següent.

La feina va dins de `main()` i es crida sota `if __name__ == "__main__":`. Els tres guions que la
feien —`tria_el_millor_text.py`, `alinea_paraules.py`, `parla_arab_o_amazic.py`— ja ho tenen.

La regla general: **un mòdul del qual algú importarà una funció no ha de fer res en importar-se.**

## 11. On s'ha de fer córrer cada cosa

Aquesta nit la màquina es va quedar sense memòria i el sistema va aturar dues feines de fons. La
causa no era cap error: era carregar un model de **mil milions de paràmetres** a la CPU d'aquí
mentre ja hi corria una altra cosa.

Els números de la nit, sobre els mateixos 639 talls i el mateix model:

| | temps |
|---|---|
| GPU de Kaggle | **172 s** |
| CPU d'aquesta màquina | **~35 min** |

Dotze vegades més lent, i amb risc que el sistema talli la feina a mitges. La regla:

- **Un model gros (MMS-1b i amunt) va a Kaggle**, encara que la cua de GPU faci esperar mitja
  hora. Esperar surt més barat que forçar-ho aquí.
- **En local només el que és petit** o el que no es pot pujar.
- **Mai dues feines de model alhora en local.**
- I si la cua no es mou, val més deixar-ho encuat i fer una altra cosa que buscar una drecera:
  la nit del 20 la drecera va costar 190 talls de 240 i una feina morta a mitges.

El que sí que va sortir bé d'haver-ho fet dues vegades: la passada de Kaggle i la local van donar
**el mateix text exacte als 639 talls**, i això va servir de comprovació que cap dels dos camins
no tenia un error. Si es repeteix la duplicació per accident, val la pena comparar-les.

## 12. Una regla amb interval es llegeix amb interval

La regla del cercle diu «cap prova no empitjora **amb IC** i almenys dues milloren **amb IC**».
La nit del 20 la vaig llegir primer a punts i vaig dir que no es complia: quatre proves milloraven
i una pujava 0,0026. Calculat l'interval, aquell +0,0026 era [−0,0025, +0,0079] — **soroll**, i la
regla es complia.

La regla demana interval justament perquè un punt no distingeix un empitjorament d'un sorteig.
Dir «no es compleix» mirant punts no és ser prudent: és fer servir una altra regla.

I la manera de no equivocar-s'hi és la que va funcionar: **llegir la regla al codi**
(`cercle_virtuos.py:122`) en comptes de recordar-la.

## 13 · Un llindar es tria mirant el record, no la precisió

El filtre de grau A es va posar a 0,35 «perquè deixa passar la variació consonàntica real». Vaig
donar per fet que això costaria poca brossa. Mesurat contra veritat humana: a 0,35 la precisió
d'esquelet és **74,4 %**, i a 0,15 és **99,2 %** — i el record de les paraules exactament
correctes és **99,7 % als dos**.

La lliçó no és el número sinó on mirar: jo havia triat el llindar pensant en **què hi entra**, i
la pregunta bona era **què hi perdo si l'estrenyo**. Quan afluixar un llindar no recupera res que
sigui bo, afluixar-lo només afegeix soroll.

I el corol·lari pràctic: amb paraules de 3 a 6 consonants, qualsevol llindar per sota de 0,17 vol
dir «idèntic». Els llindars continus en coses curtes són una il·lusió de precisió; la decisió de
debò era binària i no me n'havia adonat.

## 14 · Un zero absolut vol dir que miro el camp equivocat (segona vegada)

0 formes del lèxic en 9.278 paraules. No era una troballa: les files eren en tifinag i el lèxic
en llatí. És la mateixa lliçó del 10-11 («el `common-voice` amb guionet») i me l'he tornat a
trobar. **Un zero perfecte no és mai un resultat; és una pregunta sobre la canonada.**

## 15 · Tota separació es prova contra l'atzar

«El lèxic posa la biblioteca al costat tachelhit» no vol dir res fins que se sap què faria un
lèxic fet amb etiquetes a l'atzar. Aquí: raó de debò 3,65, mediana de l'atzar 1,05, màxim 3,21
en 200 repartiments. Sense aquesta segona línia, la primera és una anècdota.

Val per a tot el que separa grups: varietats, parlants, èpoques, fonts. **Barreja les etiquetes i
torna-ho a mesurar.**

## 16 · Una mesura feta a una altura no decideix a una altra

El 20-11, el mateix llindar i el mateix corpus: **per paraula**, estrènyer de 0,35 a 0,15 no
costava ni una paraula bona (record 99,7 % als dos costats); **per frase**, estrènyer de 0,35 a
0,20 costa un 16 % de les frases. De la primera mesura en vaig treure una recomanació sobre el
train, que es tria per frase. No es podia.

Abans de recomanar res a partir d'una mesura: **preguntar a quina unitat es pren la decisió**, i
mesurar en aquella.

## 17 · Una calibració diu on tallar, no quant et quedarà

El mateix llindar (0,20) conserva el 76 % de les frases a les proves amb veritat humana i el
42 % al corpus del SNRT. **La relació entre la mesura barata i la qualitat es transporta; la
distribució no.** Abans de prometre «es perd poc», comptar-ho al corpus que es filtrarà.

## 18 · Un total que no es pot reconstruir dels seus trams és un error

El 20-11 una mesura aparellada em va donar una inflació de +0,0989 mentre la taula per trams en
deia 0,01-0,04. No era un matís: era que l'aparellament, amb els talls ordenats per
`(mesura_abans, mesura_després)`, agafava sempre el primer dels empatats — **el que més havia
millorat**. Em triava els millors jo mateix.

La regla: **desfer els empats a l'atzar**, sempre, quan s'aparella per una variable que té valors
repetits. I abans d'això, la que el va atrapar: **mirar si el total quadra amb els trams.**

## 19 · Una etiqueta millor no fa un model millor

El 20-11 vaig mesurar bé que el llindar de 0,20 dona etiquetes més netes (CER ric 0,151 → 0,127)
i en vaig deduir que el model milloraria. La ronda diu que no: perdent la meitat del corpus, el
model **empitjora** on es juga (+0,0150 al SNRT retingut, interval que no toca el zero).

La lliçó no és «la qualitat no importa», és que **entre una mesura de l'entrada i el resultat hi
ha un pas que només una ronda pot fer**. Mesurar la qualitat de les etiquetes és barat i útil per
ordenar hipòtesis; decidir amb això, sense córrer la ronda, és saltar-se la part cara i és
justament la que contesta.


## 20. Un llindar es mesura contra un fals (20-11)

Quan una regla té un número a dins (quantes consonants han de casar, quin CER passa, quantes
boques calen), el número no es tria a ull: es mesura **quant en dona l'atzar**. Es fabrica una
versió falsa de la cosa amb què es compara — un diccionari amb les mateixes lletres i les
mateixes llargades, un repartiment de capítols a sorts — i es mira quantes coincidències surten
sense que hi hagi res a trobar. El que queda és el que val.

Amb dues consonants el diccionari fals en donava **1.479 de 1.833**: el llindar que semblava
prudent deixava passar vuit casualitats de cada deu.

## 21. La unitat del remostreig és la que es va mostrejar (20-11)

Un interval de confiança respon «si tornés a fer l'experiment, què sortiria». Si l'experiment va
ser **triar quatre capítols**, el remostreig ha de tornar a triar capítols, no frases: les frases
d'un capítol comparteixen veu, gravació, soroll i lector, i remostrejar-les com si fossin
independents fa l'interval més estret del que toca.

Però no val a l'inrevés tampoc: una prova de 256 clips independents amb un sol nom de capítol
remostrejada per capítol dona un interval d'**amplada zero**, que diu el que sigui per
construcció. La unitat es tria per prova, i es diu quina s'ha fet servir.

## 22. El heredoc es menja les barres, i hi he tornat a caure (20-11)

Un pedaç amb `delimiter="\t"` escrit dins d'un heredoc de bash arriba a Python amb un TABULADOR
de debò, i l'àncora no casa mai. Ja ho tenia apuntat. **Els pedaços s'escriuen amb l'editor.**


## 23. Un verificador independent canvia què s'ha d'optimitzar (20-11)

Si hi ha un testimoni que pot dir si cada troballa és bona, **no s'ha d'afinar la cerca perquè
encerti molt: s'ha d'eixamplar perquè trobi molt**, i deixar que el testimoni filtri. El que
compta és el nombre de troballes confirmades, no el percentatge.

Amb el filtre estret: 342 cadenes, 73 % d'encert, ~316 formes bones. Amb l'ample: 736 cadenes,
63 %, **789 formes bones**. Pitjor percentatge, dues vegades i mitja més resultat.

Això només val quan el verificador és **de debò independent**. Aquí l'ull llegeix la imatge i
no ha sentit res; si el filtre i el verificador sortissin del mateix model, el percentatge seria
una conversa del model amb ell mateix.

## 24. El sostre d'una cura no és la cura (20-11)

Vaig mesurar que els espais pesen l'11-28 % del CER i ho vaig donar com el guany d'arreglar-los.
No ho és: és el que passaria **si fossin perfectes**. El guany real del mètode que els arregla
estava mesurat des de feia cinc dies i era **quatre vegades més petit**. Abans de dir què val una
cura, s'ha de buscar si ja està mesurada.


## 25. Una peça que no és al repositori és una peça que no existeix (21-11)

`arpa_lm.py` feia funcionar l'experiment més important que hem fet amb el model de llengua, i
era només al dataset de Kaggle. Durant cinc dies vaig creure que el resultat era reproduïble.
**Si un resultat depèn d'un fitxer que no és sota control de versions, el resultat no és
reproduïble**, per molt que el número estigui apuntat.

## 26. Una mostra per grup no descriu el grup (21-11)

El triatge del canal mirava **un vídeo per programa** i etiquetava el programa sencer. Dos
episodis de Tadfi han fallat per no tenir tifinag, cosa que aquell triatge donava per impossible.
Quan el que es decideix és «collir tot aquest programa», la unitat de la mesura ha de ser
l'episodi, no el programa.


## 27. Es pot triar abans de pagar (21-11)

Decidir quin model de llengua desplegar semblava demanar GPU: provar-los tots dos descodificant.
No calia. La **perplexitat sobre text que cap dels dos no ha vist** els separa per un factor de
3,7 en dos segons i sense cap model acústic.

Quan una decisió sembla que demana l'experiment car, val la pena buscar quina mesura barata hi
està correlacionada. No substitueix l'experiment — el que es mesura és la perplexitat, no el
CER — però tria quin experiment val la pena fer.

## 28. El mateix error en un altre lloc és un error nou (21-11)

El llindar de tres consonants el vaig mesurar i corregir al diccionari a la tarda, i unes hores
després el vaig tornar a posar al glossari del visor. Saber per què una cosa està malament en
un lloc no impedeix repetir-la en un altre: quan es corregeix un llindar, s'ha de buscar on més
es fa servir aquella mateixa comparació.


## 29. Un número baix no diu de qui és la culpa (21-11)

L'acord entre dues vies va donar 0,310 i el vaig llegir com una propietat de la meva traducció.
No ho era: el control —la mateixa mesura amb una traducció bona per definició a l'altra banda—
va donar 0,339. **El número mesurava el sostre del verificador, no la qualitat del verificat.**

Quan una mesura d'acord surt baixa, abans de concloure res s'ha de córrer amb una entrada que
se sap bona. Si allà també surt baix, el que és fluix és la mesura.

## 30. Una diferència significativa pot ser d'una altra cosa (21-11)

El −0,029 entre la meva traducció i la confirmada tenia un interval que excloïa el zero, i tot
i així no volia dir el que semblava: eren **episodis diferents**. Un interval diu que la
diferència no és atzar; **no diu de què és la diferència**.

La prova que ho resol és l'aparellada: les MATEIXES línies, els dos tractaments. Allà va sortir
0,746, el mateix que la primera prova.

## 31. Les discrepàncies no són soroll (21-11, d'en Pablo)

«Quan hi hagi discrepàncies en les traduccions, en aquells casos t'ho has de mirar especialment.»
Mirant-les va sortir un error a la traducció que teníem per **confirmada**: havien llegit
«excel·lència» on hi deia «alumne». Amb tres camins cap a la mateixa frase, el que queda sol és
el sospitós, i no sempre és el que t'esperes.


## 32. Dues proves del mateix lloc no són dos testimonis (21-11)

`tfa-226` i `test-fora` són del mateix canal i comparteixen el 38 % de les frases. Durant dos
dies he dit «quatre proves amb veritat humana» com si fossin quatre testimonis independents.
**Abans de dir que una cosa està confirmada per N proves, s'ha de mirar d'on surt cadascuna** —
l'identificador dels clips ho deia, i no ho havia mirat mai.

## 33. El resultat que ningú no ha llegit no existeix (21-11)

Els logits de totes les proves estaven calculats i guardats des del 19-11. L'experiment que els
necessitava es va mesurar sobre 20 parelles i es va deixar. La mesura que faltava des del 15-11
es va poder fer en deu minuts i sense GPU.

Abans de muntar un experiment, s'ha de mirar què hi ha ja calculat.

## 34. No inventar la part d'un identificador que no es té (21-11)

Tenia un identificador retallat a 14 caràcters per pantalla i en vaig completar la resta per
endevinar. L'ordre va fallar amb «no dona adreça» i hauria pogut acusar el servidor. Un
identificador incomplet es torna a demanar; no es completa.


## 35. Saber de quina llengua és el material, abans d'entrenar-hi (21-11)

Vaig construir dos corpus d'entrenament sense comprovar en quina varietat eren. El fitxer de
varietats classificava **uns altres** capítols i els meus sortien tots com a desconeguts; no ho
vaig mirar fins que en Pablo m'ho va recordar.

## 36. Un classificador desequilibrat diu el que té més marques (21-11)

117 marques d'una banda contra 39 de l'altra: amb aquest lèxic, qualsevol episodi tendeix a
sortir del costat gros. El classificador no estava trencat — **ordenava bé** els episodis, i els
rifenys eren els de puntuació més baixa — però el llindar absolut no valia. Quan un
classificador diu el mateix de tots els casos, s'ha de mirar si les dues bandes tenen el mateix
pes.

## 37. El senyal bo és el que no passa pel filtre que sospites (21-11)

El tifinag està normalitzat per l'IRCAM, i la normalització **esborra justament** allò que es
vol mesurar. Els topònims a l'àrab no passen per aquella normalització, i per això van poder
dir el que el tifinag no podia.
