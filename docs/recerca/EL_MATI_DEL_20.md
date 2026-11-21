# El matí del 20 de novembre, en una pàgina

*El detall és a `DESXIFRAT.md` §20; les lliçons d'ofici, a `METODE.md` §13-16.*

Em vas demanar dues coses: seguir treballant i **validar el que vaig aprendre anit amb altres
parts del catàleg**. Això segon era el que calia, perquè tot el de la nit surt del mateix lloc:
material de la SNRT, llegit pel nostre ull i sentit per la nostra orella. Podia estar mesurant
una manya del sistema i no una propietat de la llengua.

## El que ha resistit la prova

**1. El sostre el posa el subtitulador, no la nostra orella.** Mateix codi, mateixa orella,
mateixa mesura; l'únic que canvia és qui escriu la referència:

| referència | acord | CER mediana |
|---|---|---|
| Zouhir, retolat a mà | **71,9 %** | 0,000 |
| CV zgh (frases llegides) | 67,9 % | 0,000 |
| TFA-226 (transcripció humana) | 61,4 % | 0,000 |
| la nostra parla, mai sentida | 52,4 % | 0,200 |
| **subtítol del SNRT** | **23,1 %** | 0,667 |

El número que més diu és la **mediana zero**: contra veritat humana, la paraula del mig casa
exacta. Contra el subtítol, 0,667.

**2. El lèxic de varietats sap de llengua, no de model.** Aplicat al manifest de la biblioteca
—6.628 gravacions, text escrit per persones, etiquetes que no surten de cap mesura meva— posa
tots els grups al costat tachelhit, amb raó 3,65. Amb les etiquetes **a l'atzar** (200
repartiments): mediana 1,05, màxim 3,21. Cap dels 200 no arriba al de debò (p = 0,005).

**3. El filtre d'esquelet ordena de debò.** Per frase, contra veritat humana, el CER ric puja
monòtonament amb el d'esquelet: 0,063 → 0,108 → 0,166 → 0,260 → 0,477 → 1,007. Això és el que
justifica el filtre.

## El que m'he hagut de desdir (tres vegades, i totes en la mateixa direcció)

- **«A 0,35 esperava >90 % de precisió per paraula»** → és **74,4 %**.
- **«A 0,35 entraran frases amb CER ric per sobre de 0,3»** → no hi entren; la mitjana és 0,151.
- **«El `kab` i el `rif` han de coincidir més entre ells, que són llengües del nord»** → la
  parella que més coincideix és **`shi`~`kab`**, que és la que comparteix el model base.

El patró és sempre el mateix: **espero que les coses fluixes siguin pitjors del que són, i que
la semblança entre models vingui de la llengua quan ve de la màquina.**

I un error d'altura que valia una recomanació: de la mesura per paraula en vaig treure «el train
de la ronda 2 s'ha de triar amb esquelet idèntic». El train es tria **per frase**, i per frase
estrènyer costa una quarta part del corpus. La recomanació bona és provar **0,20**: conserva el
76 % de les frases i treu un 16 % de l'error de l'etiqueta (0,151 → 0,127).

## El corpus rifeny, que ja existeix

La feina de les tres orelles **sí** que va córrer (05:28; t'havia dit que no). Les tres van
sentir els 3.517 talls. I la troballa de la independència canvia què val:

| | talls | |
|---|---|---|
| les tres coincideixen (amb el `rif`, base independent) | 1.862 | 52,9 % |
| dues, i una és el `rif` | 962 | 27,4 % |
| dues, però `shi`+`kab` (**mateixa base**: no és corroboració) | 198 | 5,6 % |
| cap parella no casa | 489 | 13,9 % |

**`corpus_consens_rifeny.jsonl`: 2.824 rèpliques amb suport independent i significat en català,
3,56 hores.** El número que et vaig donar anit (4.492, 5,2 h) estava inflat un 59 %.

Segueix sent grau C. El que el faria grau A no és tècnic: **cent línies llegides per algú del
Rif.**

## I l'app, que és el que tenies a la pantalla

El servidor de producció es moria de memòria cada ~70 minuts tota la nit. La cadena, mesurada:
adreces `/mitjans/…` que el lector no sap obrir → cada lectura falla → l'app hi torna de vuit en
vuit cada deu minuts per sempre (201 gravacions encallades) → cada fallada deixa un client de
Gradio amb el fil viu i 1-2 MB que no tornen → 512 MB en 70 minuts.

- **PR #701** — l'arreglament (728 proves passades). *No fusionat: fusionar-lo desplega.*
- **PR del visor** — obert a tothom com vas demanar, amb el vídeo allotjat encara tancat, i la
  pàgina ja no et diu que no ets administrador quan el que passa és que el servidor no hi és.

I una cosa que no és meva: Render diu **«Payment failed»** i tens 4 serveis suspesos.

## Afegit a mig matí

**Les marques fonètiques són a la parla, no al nostre adaptador.** Mesurat sense subtítol i
sense alineament —només quina proporció de `r` i de `š` escriu cada orella a cada episodi—, dos
models sense cap parentiu donen el mateix:

| | la nostra (`shi`) | la rifenya (altra base) |
|---|---|---|
| tachelhit | r 51,6 % · š 19,1 % | r **52,7 %** · š 23,8 % |
| Atles central | r 50,0 % · š 29,9 % | — |
| tarifit | r **67,6 %** · š 53,1 % | r **66,6 %** · š 61,8 % |

Episodi a episodi **no hi ha cap solapament**: tachelhit entre 49,1 i 55,0 % de `r`, rifenys
entre 61,6 i 78,0 %. Separació perfecta sobre 22 episodis.

**Dos episodis no estan ben col·locats**, i són precisament els dos que la regla va decidir pel
criteri més feble (l'acord alt, perquè el presentador no era concloent): **SAID OU BOULMAN** i
**MOHAMED EL GHAZOULI**, tots dos amb `š` molt alta i `r` normal —el perfil de l'est sense ser
del Rif— i el primer amb un lèxic (89,2 sh/1000) que cau dins del marge de l'Atles central. Si
ho fossin, les hores d'Atles central passarien de 2,07 a unes 2,8. **Això no ho decideix cap
màquina: ho decideix algú escoltant deu minuts de cada episodi.**

**I la ronda 2 ja corre**, però no és la que esperaves: no adopta M₁ (això segueix sent decisió
teva). És el **mateix M₀ i la mateixa recepta amb el corpus filtrat a 0,20** en comptes de 0,35
—717 talls en comptes de 1.678, etiquetes millors— per contestar amb una mesura la pregunta que
§20.7 deixa oberta. Els dos braços conviuen i es comparen amb el mateix codi.

## Les dues rondes, contestades

**1. Adoptar M₁ inflaria el filtre?** (la teva pregunta: «M té un biaix o no el té?»)

Mesurat: els 1.849 talls que M₁ va veure contra els de grau A dels capítols retinguts, amb les
dues bandes processades igual. **Inflació +0,0103, interval [−0,0028, +0,0243]: passa per zero.**
La firma hi és —als vistos la millora creix amb la distància de partida (+0,013 → −0,054), als no
vistos no té tendència— però 151 talls de control no decideixen.

**I la decisió no en depèn.** El corpus que vol la ronda 2 no són els talls que ja tenim: són els
**1.137 que es queden just a fora del llindar** més els **335 que ja passen i M₁ no ha vist mai**.
Deixar fora els 1.849 vistos no costa el que busques. Per això: **adopta M₁ i que la ronda 2
trii el corpus només d'allò que M₁ no ha vist** — no perquè la inflació estigui provada, sinó
perquè evitar-la és gratis.

**2. El llindar 0,20 que jo mateix havia recomanat: dolent.** Mateix M₀, mateixa recepta,
mateixes proves, 707 talls en comptes de 1.678. **No passa la regla del cercle** (una sola prova
millora, en calen dues) i cara a cara perd on es juga: **+0,0150 [+0,0100, +0,0199]** al SNRT
retingut. Etiquetes més netes no compensen mig corpus menys.

Sisena predicció meva refutada aquest matí — però aquesta per un experiment dissenyat per
refutar-la, que és com ha de ser.
