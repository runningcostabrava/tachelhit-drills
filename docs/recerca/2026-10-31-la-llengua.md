# Què hem après de la llengua

31-10-2026. Issue #530. Resum de la recerca del 30-10 sobre les 12.055 files de la biblioteca i de
tres auditories independents: un dialectòleg, un expert en gramàtica amaziga i un pedagog.

Cap d'aquestes conclusions no s'ha aplicat a producció. Les lliçons continuen com estaven.

## Com s'ha de llegir

Cada afirmació porta una marca:

- **atestat**: és a frases escrites per persones, o al compendi d'amazic.cat. Es pot comptar.
- **inferit**: és una lectura nostra d'un patró. Pot caure.
- **sense verificar**: les dades no ho poden dir. Cal escoltar o preguntar.

Quan diem «la Halima i en Driss» o «Aït Mraw» volem dir això i prou: dues persones d'un poble. No
és «tota la ruta». El compendi (§1.4.2) diu que hi ha parles de la vall del Dadès que no afluixen
les velars, així que a la mateixa zona es poden sentir altres formes.

## Els límits, abans de res

- **Ningú no ha escoltat cap àudio.** Tot el que diem del so ve de com està escrit. «Té veu» vol
  dir que hi ha un fitxer, no que l'hàgim sentit.
- **Les proves d'Aït Mraw són poques.** Unes 2.000 paraules, escrites a mà per gent que no és
  lingüista, amb grafia lliure. Frases riques, unes 180, i moltes repetides. **Tota regla d'Aït
  Mraw d'aquest document descansa en poques desenes de frases.** Frases negatives diferents, unes
  40. Si una forma no hi surt, vol dir «no en tenim cap», no pas «no es diu».
- **No sabem qui va escriure les frases** de la Halima i en Driss. Si va ser una sola persona, part
  del patró pot ser hàbit de qui escrivia.
- **El text de les unitats és una còpia del 24-10.** Llegir-les de producció pot posar a escriure
  una lliçó caducada, i no es podia escriure a producció.
- **No hem trobat cap publicació** que parli d'Aït Mraw ni de la vall del Mgoun.

## El que hem après, per ordre d'importància

### 1. La Halima i en Driss tenen un perfil propi

**Atestat en l'escriptura; el so, sense verificar.**

On un llibre escriu g, a les seves frases hi ha j: `tjit` «ets» (#275), `ija` «és» (#276), `manij`
«on» (#14). On un llibre escriu k, sovint hi ha š: `ghorsh` «tens» (#28), `chiyin` «tu» (#262).
A les paraules de prova, la forma amb g o k no surt mai a les seves files.

No passa sempre. `Aska` «demà» (#153), `imik` (#47) i `nkin` «jo» (#520) guarden la k, i `isgasn`
«anys» guarda la g. La regla de quan passa és **inferida**.

Beni Mellal comparteix la š, però no la j: hi escriuen g. Per tant no són un sol interruptor, tot i
que el compendi explica les dues coses com un afebliment de les velars.

Com sona de debò no ho sabem. El compendi dona sons més suaus per a la zona, però no parla d'Aït
Mraw. **Una regla d'escriptura no és una instrucció de pronunciació**: el curs ha de dir «ho has de
sentir».

### 2. Les dues «sèries d'Aït Mraw» probablement no són d'Aït Mraw totes dues

**Conclusió forta, però no demostrada. El que falta és una prova, no una intuïció.**

| | sèrie 1 | sèrie 2 |
|---|---|---|
| qui | Halima, Driss, els seus vídeos | canal Tamazight For All |
| etiqueta | `Aït Mraw (Azilal)` | `Ait Mraw` |
| formes | `tjit`, `ghorsh` | `tgit`, `g°mak` (#7043) |

**Atestat:** són 723 files, totes del canal, totes creades el 26-10 en poques hores. Els altres
textos del mateix narrador no porten regió. Cap document, guió ni commit no lliga el canal amb Aït
Mraw, i `docs/TAMAZIGHT_FOR_ALL_CHANNEL.md` el classifica com a amazic estàndard. A més de sons,
canvien paraules: `imiq` / `imik`, `ann ax` / `itkh`, `nkkin` / `nkin`.

**Inferit:** la regió va venir d'un lot, no de res que se sabés de qui parla.

**En contra:** un text pot estar normalitzat i amagar la pronúncia; hi ha coses compartides (`hat`,
`ixṣṣa`/`ikhsa`, `dɣi`, la -t de «tu»); i no podem excloure algú de la zona que escrigui estàndard.
L'àudio del canal escrit pel nostre ASR tampoc no prova res: el model no ha après mai la j.

**Què ho decidiria:** fer sentir #7043 i #7029 a la Halima, i preguntar a l'autor del canal d'on és.

Mentre tant: `grammar.py` a `main` encara compta aquestes files com a Aït Mraw (la branca
`fix/tfa-no-es-veu-nostra`, #524, ho arregla i encara no s'ha fusionat), i qualsevol resultat d'ASR
donat com a «Aït Mraw» per aquesta etiqueta mesura de fet el canal. Dins de la mateixa etiqueta hi
ha un tercer grup: les 67 files de la classe d'Azilal, que guarden k i g.

### 3. Jo i tu amb i, els altres amb a

**Atestat.** És la regla que més rendeix i el curs no la deia. Molts verbs que a la tercera persona
acaben en a porten i per a «jo» i «tu»: `jigh` «soc» (#499), `tjit` «ets» (#275), però `ija` «és»,
`nja` «som» (#278), `jan` «són» (#280). Igual amb anar i dir. Compendi §5.2.2.1.

**Excepcions.** `tjim` «sou» (#279), d'en Driss, porta i, i `tdam` (#269) porta a: cal preguntar-ho.
Els verbs com `ittu` no canvien. Aquesta regla **no substitueix** els passos que ensenyen les
terminacions de persona: s'hi afegeix.

### 4. El perfectiu no és «passat»

**Atestat.** Sovint es tradueix en passat, però no sempre: `mani s tdit` és «on vas?» (#266). Vol
dir que la cosa es presenta com a feta o com a estat (compendi §5.2.2.2). El títol de la unitat
deia «(passat)». Ja no.

### 5. La negació: una i, i ur sol

**Atestat.** Amb ur, la forma de les coses fetes agafa una i: `Driss ishua` / `Driss ur ishui`
(#211, #210), i `urtn fhimgh` «no els entenc» (#454). Hi ha excepcions a les mateixes frases: `Ur
ghori tahla` (#111), al costat de `or ihli` (#423).

**Atestat.** «Mai» a Aït Mraw és sobretot `Ur jint` (#112) i `urjint` (#231). `ur jigh`, que la
unitat donava per «mai», vol dir «no soc»: `Ur jigh labas`, «no estic bé» (#357).

**Atestat per a les nostres frases.** Reforços ša i bu: cap, ni a Aït Mraw ni a Beni Mellal. Però
el compendi diu que ka/ca és obligatori en alguns parlars del sud (§7.2.2.1). No és un error del
llibre: és «a les nostres frases no surt». De `walu` i `kul`, que són de Beni Mellal, a la Halima i
en Driss no els en tenim cap.

### 6. El pronom salta al davant

**Atestat.** El petit mot «em», «et», «li» va darrere del verb (`A3wni` «ajuda'm», #115) llevat que
davant hi hagi ur, ad, ar, da, is, una paraula de pregunta o un relatiu: `isi tfhmt` «m'entens?»
(#172), `Maydas tnit?` «què li has dit?» (#75). Compendi §4.1.2.2. Que no salti darrere de `hat` és
**atestat** en poques frases, sense suport del compendi.

### 7. ar i da

**Inferit.** Sembla que la Halima i en Driss fan servir ar per al que està en curs i da per al que
es fa de costum. Són unes 13 files de cada, el compendi ho diu per a «alguns parlars de l'Alt
Atlas» sense dir quins, i hi ha contraexemples (#445, d'ahir amb ar). A Beni Mellal no hi ha aquest
repartiment: da val per a tot. Sense preguntar-ho no es pot afirmar.

### 8. «Tu» amb -t o amb -d

**Atestat en l'escriptura; sense verificar si és només grafia.** La Halima i en Driss escriuen -t
(`tjit`), Beni Mellal -d. En Driss també té algun -d (`tKid`, #253). A MTNRA el -d és una convenció
d'escriptura, així que aquesta diferència pot ser menys del que semblava. El mateix val per a la
-ɣ / -x de «jo».

### 9. Beni Mellal serveix per al vocabulari, no per a les terminacions

**Atestat.** És el recull gran més proper i l'únic amb paradigmes complets, però hi escriuen g, -d i
-x. Bon recurs per a una paraula que falta; mal model per a un verb conjugat. I `iɣrm` hi vol dir
«casa», mentre que a Aït Mraw és «poble»: s'ha de mirar paraula per paraula.

### 10. «Souss» a MTNRA i Common Voice no és una varietat

**Atestat.** Un centenar de files porten formes del nord i cap marca del Souss, i la regió de
Common Voice descriu qui llegeix, no el que llegeix. Per a alternatives del Souss, val més el llibre.

### 11. Vocabulari: la feina que queda és de comprovar, no de trobar

**Atestat.** Dels 166 mots revisats a mà, 154 tenen un drill amb veu de persona on el català del
mateix drill en confirma el sentit. 12 han caigut. 59 encaixen en un capítol escrit del Mètode (1 a
5) o en una unitat, i 95 no encaixen enlloc escrit: moltes són de les lliçons 6 a 10, i el pla del
llibre es queda.

La lliçó útil: **el drill «amb veu» que proposava la recerca sovint era d'una altra paraula.** `mašš`
«però» apuntava a `ait mash` «els teus germans» (#28); `xss` a un `xs` «excepte»; `ussu` «llit» a un
verb «es movia». Una llista de coincidències de lletres no és una llista de paraules. Cada drill
s'ha tornat a mirar. Dels 154, 35 només tenen el català de màquina al drill, i es diu a cadascun.

## Coses que vam creure i que les auditories van tombar

Cal guardar-les perquè no tornin.

| es deia | per què no |
|---|---|
| «`dari` també és d'Aït Mraw» | una sola fila, negada, amb un artefacte de captura. **Proposta descartada** |
| «i → yi: no a Aït Mraw» | els plurals regulars no prenen y al compendi, i era una regla d'escriptura feta instrucció. **Proposta descartada** |
| `makh` és d'Aït Mraw i `max` de Beni Mellal | és el mateix mot en dues grafies |
| `maca` / `masha` és una diferència de paraula | és una diferència de grafia |
| «cinc maneres» de fer la forma llarga | és l'ordre d'un vídeo; el compendi en dona tres |
| `lwt onzar` | quasi segur és `Iwt`, una I llegida com L |
| a Beni Mellal ar va «sobretot en el segon verb» | de 49 files, només 7 |
| «sobretot tty-» | repetició d'un sol verb; per lemes, ttu- no queda enrere |
| g → j i k → š són «un sol fenomen» | Beni Mellal té l'una sense l'altra |
| `na` com a relatiu d'Aït Mraw | només surt a un conte dubtós |
| `iksan` «pastura» | és un participi, no un nom |

## Quant de les propostes queda

De les 29 propostes de canvi al curs, **27 sobreviuen** amb els canvis demanats i **2 cauen**, les
de la taula: `ser-tenir` i la tercera d'`estat-annexio`. Cap no ha sortit sense retocs: en conflicte
s'ha pres sempre el més prudent. Tres passen de lloc: dues a «a fons» i una a `imperatiu`.

Les dades de Tamazight For All no fan d'exemple enlloc. Els textos es van comprovar per guió contra
la biblioteca, lletra per lletra, incloses les lletres guardades descompostes.

El que sí que canvia amb aquesta PR: cinc títols de `backend/grammar.py` que prometien coses falses,
la pista del perfectiu per al classificador i l'encàrrec al model, que deia «passat». Una lliçó ja escrita no
canvia per això: `LESSON_VERSION` no es toca. Passar els textos nous a les lliçons vol dir escriure a
producció amb `PUT /grammar/{slug}/lesson`, i ho decideix l'amo.

## Preguntes per a la Halima i en Driss

Passa abans la veu pel model i proposa una sola forma, mai una llista.

**Les que decideixen alguna cosa**

1. `ar tsagh` i `da tsagh`: és el mateix? Un és «ara» i l'altre «sempre»?
2. Escolta #7043 i #7029: es parla així a casa?
3. `tjim` o `tjam`, per a «sou»?
4. `tniti qad tugholt`: què és aquest `qad`?
5. `ur dari ili`: és normal? O sempre `ghori`?
6. `ur ssingh cha`: es pot dir?

**Formes que dubtem**

7. #197: `ibrdn` o `ibardan`?
8. `Ur ghori tahla` o `tahli`?
9. `nsagh`: a #17 és «camino», a #150 és «comprem». Quina és quina?
10. `tadwart`: gata o carn? I `tdwart`?
11. `n ighfns`: hi ha una y que no s'escriu?
12. `izdar`: a #139 hi diu «baixar», a Beni Mellal és «a sota». Quin és?
13. #304: què vol dir que hi escrius «Ouarzazate» i «Azilal»?

**Per gravar, que no ho tenim**

14. Salutació, bon dia, si us plau, adeu a un home i a una dona.
15. Del 4 al 7 amb un nom.
16. Com es diu «no és»? I «res»?
17. Una prohibició amb pronom, com «no li diguis», en una frase sense el nom de cap criatura.
18. #6943, #6878, #6941, #6868: frases d'Aït Mraw sense veu.

## Per a qui administra

- Canviar la regió de les 723 files del canal, i mirar `Aït Mraw (Azilal)`, que és fals: és Tinghir.
- Decidir el català de #533 (el text diu -as, «li», i el català diu «m'ha dit») i de #174.
- Dir si `iɣrm` és «casa» o «poble» a la parla que ensenyem.
- Mirar #385, #562 i #393: tenen veu, però no sabem qui parla.
- Les frases #443-448, a les files de la Halima, són d'una altra mà i no sabem de qui.
- La pista de `estat-annexio` encara cita `n yirgazn`. Expert i pedagog la discuteixen, el dialectòleg
  no en diu res, així que aquesta PR no la toca.
- #528: 283 frases sense gravació sonen amb veu sintètica, cosa que l'abast prohibeix. El text proposat
  no en fa servir com a exemple, però això no ho arregla.
