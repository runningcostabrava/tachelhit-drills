# El curs de gramàtica, refet (22-10-2026)

Què s'ha canviat aquesta nit, per què, i què queda obert. Tot és a la branca `feat/paradigms`
(PR #176), que porta també la correcció urgent del PR #175.

## 1. Les lliçons tenen més contingut

| | abans | ara |
|---|---|---|
| explicacions per lliçó | 5-7 | 7-9 |
| frases per explicació | 3 (el lector en retallava la resta) | 4-6 |
| preguntes | una cada dues explicacions | una després de cada explicació |
| repàs final | cap | 3 preguntes sobre frases que no havien sortit |
| fons de frases | 60 | 90 |
| taules | 1, inventada | 1-2, copiades dels paradigmes dels parlants |

El retall a tres era un error del lector: el model donava sis exemples i el codi en llençava la
meitat. A més, una explicació que arriba curta s'omple amb frases de la mateixa unitat que
contenen el tros que s'ensenya, comparat pel so, de manera que «ghori» serveix per a una
explicació sobre «ɣur-i» i «izri wass» no hi entra mai.

## 2. Una unitat obre a l'instant

Abans la lliçó s'escrivia dins de la petició: obrir «ser-tenir» trigava 22 segons, i qualsevol
canvi de format feia esperar el primer que entrava. Ara:

- la lliçó guardada torna de seguida; si se n'està escrivint una de nova, la pàgina ho diu i la
  recull tota sola al cap de pocs segons (`GET /grammar/{slug}/lesson`);
- després de cada desplegament el servidor escriu ell mateix les lliçons que falten o que han
  quedat velles, una a una, vint segons després d'arrencar (`GRAMMAR_SELF_WRITE=0` ho atura);
- el full de regles que es llegeix del compendi es guarda per unitat, així que reescriure una
  lliçó costa una crida i no dues.

## 3. Tots els reculls arriben a les lliçons

El fons d'exemples omplia les 90 places per ordre de procedència, de manera que una unitat amb 90
frases d'Aït Mraw no mostrava mai cap de les 500 de Beni Mellal. Ara es reparteix entre els tres
reculls i descarta les frases que sonen igual que una que ja hi és. La revisió sencera del recull
de Beni Mellal és a `docs/BENIMELLAL_REVIEW_2026-10-22.md`.

## 4. Més compendi d'amazic.cat darrere de cada unitat

Cada unitat llegeix ara dues o tres vegades més seccions dels PDFs, i el full de regles inclou
els passos per ensenyar el punt i els errors típics d'un catalanoparlant. Els fulls fan entre 900
i 1.900 paraules.

## 5. Dades de producció

- 43 drills que no tenien unitat (o en tenien una desconeguda) ja la tenen.
- Les glosses paraula per paraula s'estan escrivint per a tota la biblioteca (3.166 drills; cap
  del recull de Beni Mellal en tenia).
- 299 llistes de conjugació passen a ser taules de lliçó.

## El que cal de tu

**Fusionar el PR #176.** Jo no puc fusionar en aquest mode. Quan hi sigui, Render desplega i el
servidor escriu les 23 lliçons ell sol; no cal fer res més.

## Obert

- El correu encara no surt de Render (cal provar «Envia'm una prova» amb una clau d'API de Brevo
  o Resend a la pantalla d'administració).
- `FRONTEND_URL` a Render encara apunta al domini vell.
- Les 23 veus catalanes que van fallar amb error de servidor estan per repetir.
