# ADR 0004: El Mètode parteix del llibre

- **Estat:** acceptada — **substitueix l'[ADR 0003](0003-el-metode-pren-el-pla-mai-les-paraules.md)**
- **Data:** 2026-10-23
- **Decideix:** l'amo del projecte
- **Issue:** —

## El problema

L'[ADR 0003](0003-el-metode-pren-el-pla-mai-les-paraules.md) va decidir, el mateix dia, que el
Mètode prendria **només el pla** del manual d'Abdallah El Mountassir i cap de les seves paraules.
Aquella decisió es va prendre sense permís, i era la correcta sense permís.

Amb el Mètode ja obert, es veu què costava: el capítol 1 («Els sons i com s'escriuen») surt amb
**0 de 1 seccions a punt**, perquè la fonètica no és un punt que s'etiqueti a cap frase, i la
resta de capítols ensenyen frases nostres sense cap explicació al voltant. Un curs sense
explicacions no és un curs: és una llista.

**L'amo ha trucat a l'autor i l'autor ens deixa fer servir el llibre** (2026-10-23).

## Les opcions

| opció | a favor | en contra |
|---|---|---|
| Seguir amb l'ADR 0003 | no depèn de ningú | descartem un permís que ja tenim, i el curs es queda sense explicacions ni diàlegs durant mesos |
| **Partir del llibre, tan a prop com calgui** | explicacions, estructura i diàlegs de debò des del primer dia; la feina passa a ser **adaptar-los a la nostra varietat**, que és el que de debò aporta | cal mirar-s'ho cada vegada: el que val al Souss pot no valer a l'Atles |
| Reescriure-ho tot des de zero amb altres fonts | independència total | és fer dues vegades una feina que algú ja ha fet bé, i surt pitjor |

## La decisió

**El nostre Mètode és el llibre, enriquit amb els nostres drills i les nostres explicacions.**
(Precisió de l'amo, 23-10-2026.)

Això vol dir, sense voltes: **el llibre es tradueix i es fa servir.** Les explicacions es
tradueixen al català, els diàlegs es porten, el lèxic es porta. No es reescriu per reescriure.

El que hi afegim —i que és el que el fa nostre— és:

- **els nostres drills**: al costat de cada exemple del llibre, la frase nostra que diu el mateix,
  amb la veu de qui la diu, el seu poble i la seva varietat;
- **les nostres explicacions**: on la nostra varietat funciona d'una altra manera, o on el
  compendi d'amazic.cat ho diu millor, o on falta alguna cosa que un catalanoparlant necessita i
  un italià no;
- **les nostres veus**, que no són del llibre ni poden ser-ho.

L'adaptació és una qüestió de llengua, no d'estil: **es canvia el que la nostra varietat diu
d'una altra manera**. El manual és tachelhit del Souss i nosaltres ensenyem Atles central, així
que una forma correcta allà pot ser falsa aquí. Es mira frase per frase; la resta es queda com és.

**I es dona crèdit, sempre.** Cada capítol porta d'on surt. Això no és una formalitat: és la
condició.

Tres coses que **no** canvien:

1. **La veu és sempre nostra.** Cap frase sona si no la diu una persona de debò que el projecte
   conegui, i cap veu sintètica es fa passar per amazic (docs/SCOPE.md). El llibre dona el text;
   la veu la posem nosaltres.
2. **La varietat es diu sempre.** El manual és tachelhit del Souss i nosaltres ensenyem Atles
   central. Quan una frase ve del llibre i encara no està adaptada, es diu; quan una frase és
   nostra i diu la mateixa cosa d'una altra manera, s'ensenyen de costat.
3. **La citació viatja amb cada capítol**, i diu **«Basat en…»** i res més. A la pantalla s'hi
   diu d'on ve el material, no quins permisos tenim: què ens deixa fer l'autor és cosa nostra i
   d'aquest registre, no de la targeta d'un capítol. (Decisió de l'amo, el mateix dia.) Que el
   crèdit hi sigui **no és negociable**: és la condició amb què es fa tot això.

## Què en ve al darrere

- **La feina canvia de naturalesa.** Deixa de ser «escriure un curs» i passa a ser **adaptar-ne
  un**: mirar cada explicació contra la nostra varietat, substituir cada exemple per una frase
  nostra quan en tenim, i marcar el que encara no hem recollit.
- **Queda apuntat, per si algun dia fa falta:** el que ens autoritza l'autor és de paraula, i
  l'edició italiana es va fer *«per gentile concessione dell'autore e di L'Asiathèque»* — també
  de l'editorial, que té els drets d'edició del llibre de 2009. Un correu que ho deixi per
  escrit no costa res. Això no atura res del que hi ha decidit aquí.
- **Es pot copiar malament.** Una explicació del Souss aplicada a l'Atles central pot ser
  senzillament falsa (les formes no són les mateixes). Adaptar vol dir mirar-s'ho cada vegada,
  no traduir i passar pàgina.
- **L'ADR 0003 no s'esborra.** Queda com el que era: la decisió correcta mentre no hi havia
  permís, i el registre de per què es va triar així.
