# ADR 0005: Un curs d'iniciació en anglès, i prou

- **Estat:** acceptada
- **Data:** 2026-10-29
- **Decideix:** Pablo (propietari)
- **Issue:** #487

## El problema

L'app és tota en català i l'abast la fa «per a catalanoparlants». La gent que ve a córrer a
l'Atles amb Nomatrails sovint no parla català: en Pablo vol que trobin dins l'app unes quantes
frases molt bàsiques —salutacions, gràcies, pa, aigua, «em dic…»— amb la veu d'algú de la zona i
una mica de context de la llengua, la gent i les valls d'Azilal i el M'Goun.

## Les opcions

| opció | a favor | en contra |
|---|---|---|
| No fer res | cap cost | qui no llegeix català no té per on entrar |
| Una pàgina a part (artifact) | es fa en una hora | queda fora de l'app, que és el que en Pablo no vol |
| **Una sola pàgina en anglès dins l'app** | petita, reversible, fa servir les veus i el transliterador de l'app | l'anglès viu en un fitxer del codi, no a la base de dades |
| Tota l'app en anglès (selector d'idioma) | serveix a tothom | setmanes de feina; tot el curs s'hauria de traduir |
| Un camp `text_english` a cada drill | serveix per a tota la biblioteca | canvi de model, migració i revisió a `/revisa` |

## La decisió

Una pàgina, `/start` («Start here · English»), l'única de l'app en anglès. La lliçó és una llista
d'ids de drills amb l'anglès al costat (`frontend/src/lessons/startEnglish.ts`); l'amazic, el
tifinag i la veu es llegeixen en viu de la biblioteca. Una paraula sense drill hi surt tal com la
va escriure en Pablo i diu que encara no té veu.

## Què en ve al darrere

- L'abast (`docs/SCOPE.md`) diu ara que hi ha aquesta porta en anglès; la resta continua en català.
- El significat en anglès no passa per `/revisa`: el revisa qui toca el fitxer, en un PR.
- Quan una paraula de la lliçó rebi veu a la biblioteca, cal posar-hi l'id al fitxer: la pàgina no
  la troba sola.
- Si un dia es vol tota l'app en anglès, aquesta pàgina no ho resol: és una ADR nova.
