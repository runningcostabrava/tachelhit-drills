# ADR 0010: Un tall del CD sona al Mètode també quan la lectura rica el confirma

- **Estat:** acceptada
- **Data:** 2026-10-31
- **Decideix:** Pablo (propietari)
- **Issue:** #536

## El problema

L'ADR 0007 fa sonar al Mètode només els talls del CD que ha sentit una persona: 127 línies en cinc
capítols. En Pablo, el 31-10: «totes les paraules i frases utilitzades amb el Mètode han de tenir
veu, s'ha d'extreure del CD», i «si hi ha veu, s'ha d'utilitzar». Escoltar-ho tot una persona no
arriba: el CD té 663 talls i els capítols escrits, 661 línies.

El 31-10 els 663 talls s'han tornat a llegir amb l'adaptador ric (ADR 0009) i s'han aparellat amb
el llibre per ordre (ancoratges segurs i alineació monòtona entre ells): 413 talls amb línia.
Mesura, amb les 130 escoltes d'en Pablo del 29-10 com a patró: en el tram d'acord ≥ 0,80 entre la
lectura i la línia, 39 de 40 escoltes eren «sí»; entre 0,65 i 0,80, 7 «sí» i 1 «no»; per sota,
la majoria eren «tros» (el tall diu només part de la línia).

## Les opcions

| opció | a favor | en contra |
|---|---|---|
| No fer res: només el que sent una persona | cap error de màquina al Mètode | 302 talls amb acord ≥ 0,80 no sonen; en Pablo hauria d'escoltar-ho tot |
| Fer sonar tota parella de la màquina | tot sona | per sota de 0,65 la meitat són «tros»: un botó que promet la línia i en fa sonar un bocí |
| **Llindar calibrat: ≥ 0,80 sona, 0,65–0,80 a escoltar, la resta no** | la mesura diu que ≥ 0,80 és «sí» 39 de 40; el que és dubtós el sent una persona | 1 de 40 pot ser un tros; cal tornar a mesurar quan canviï el model |

## La decisió

Un tall entra a `capitols` de `backend/data/cd_metode.json` quan una persona l'ha sentit, o quan la
lectura rica i la línia coincideixen amb acord ≥ 0,80; en aquest segon cas `com` diu «lectura rica
≥0,80 (calibrada 39/40)», perquè com s'ha sabut no s'amagui. Entre 0,65 i 0,80 el tall va a
`per_comprovar` i a la pàgina d'escolta; per sota, no entra. Els talls es pugen a Cloudinary com
fins ara (ADR 0007).

## Què en ve al darrere

- El llindar és del model d'avui (`adaptador_shi_ric`, ADR 0009): si el model canvia, es torna a
  calibrar amb les mateixes 130 escoltes abans de tornar a aplicar-lo.
- Una línia que una persona digui que és «tros» o «no» es treu de `capitols` encara que l'acord
  sigui alt: la persona mana.
- Cada capítol pot guanyar una secció amb els exercicis del llibre que el CD llegeix; el text és
  del llibre (ADR 0004) i la veu, de l'autor.
