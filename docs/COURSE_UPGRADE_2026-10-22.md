# El curs de gramàtica, refet (22-10-2026)

Què s'ha canviat aquesta nit, què s'ha mesurat i què queda obert. El codi és al PR #176, que porta
també la correcció urgent del PR #175.

## 1. Les lliçons tenen molt més contingut

| | abans | ara |
|---|---|---|
| explicacions per lliçó | 5-7 demanades, 5 escrites | 7-9 (amb 40 frases o més, menys de 7 no s'accepta) |
| frases per explicació | 3 | 4-6 |
| preguntes | una cada dues explicacions | una després de cada explicació |
| repàs final | cap | 3 preguntes sobre frases noves |
| fons de frases | 60 | 90 |
| taules | inventades | copiades dels paradigmes dels parlants |

El retall a tres era un error del lector de la resposta: el model donava sis exemples i el codi en
llençava la meitat. Una explicació que arriba curta s'omple ara amb frases de la unitat que
contenen el tros ensenyat, comparat **pel so**, de manera que «ghori» entra en una explicació
sobre «ɣur-i» i «izri wass» no hi entra mai. El mateix criteri marca el tros dins de cada frase,
encara que el parlant l'escrigui d'una altra manera.

## 2. Mesura: les 23 lliçons, escrites amb aquest codi

Totes es van escriure en local amb la biblioteca i el compendi reals (no es va tocar producció):

| | mitjana |
|---|---|
| explicacions per lliçó | 7,5 |
| frases citades per lliçó | 36,9 |
| preguntes per lliçó | 10,5 |
| unitats que citen Beni Mellal | 22 de 22 |
| prosa amb tifinag o àrab | cap |

Unitats amb més de 8 explicacions: possessius (10), temps i adverbis (12), demostratius,
preposicions i manlleus (9). Les que en tenen 5 o 6 són les de fons petit: derivació verbal (26
frases), estat d'annexió (35, ara ampliat), aorist, adjectius i numerals.

## 3. Una unitat obre a l'instant

Obrir «ser-tenir» trigava **22 segons** perquè la lliçó s'escrivia dins de la petició. Ara:

- la lliçó guardada torna de seguida; si se n'està escrivint una de nova, la pàgina ho diu i la
  recull tota sola (`GET /grammar/{slug}/lesson`);
- després de cada desplegament el servidor escriu ell mateix les que falten o han quedat velles,
  una a una (`GRAMMAR_SELF_WRITE=0` ho atura);
- el full de regles del compendi es guarda per unitat: reescriure costa una crida, no dues.

## 4. Tots els reculls arriben a les lliçons

El fons omplia les places per ordre de procedència: una unitat amb 90 frases d'Aït Mraw no en
mostrava cap de les 500 de Beni Mellal.

| unitat | abans (mraw/beni/altres) | ara |
|---|---|---|
| perfectiu | 90/0/0 | 36/36/18 |
| pronoms enganxats al verb | 90/0/0 | 36/36/18 |
| noms, gènere i nombre | 90/0/0 | 36/36/18 |

Les **299 llistes de conjugació** del recull de Beni Mellal, que cap lliçó podia tocar perquè no
són frases, són ara les taules de les lliçons (19 unitats en tenen). Revisió sencera del recull:
`docs/BENIMELLAL_REVIEW_2026-10-22.md`.

## 5. Més compendi d'amazic.cat

Cada unitat llegeix dues o tres vegades més seccions dels PDFs. El full de regles fa entre 900 i
1.900 paraules i ara inclou els passos per ensenyar el punt i els errors típics d'un
catalanoparlant. Els mots que un principiant no té («inacomplert», «clític», «díctic»…) es
canvien per la manera planera de dir-ho, encara que el qui escriu se n'oblidi.

## 6. Dades de producció (ja fetes)

| | drills |
|---|---|
| sense unitat, o amb una d'inventada, ara classificats | 43 |
| frases que ara també pertanyen a una unitat que en tenia poques | 562 |
| glosses paraula per paraula, refetes | en curs, 3.148 drills |

Les unitats pobres eren les que escrivien lliçons curtes. Cada candidat es va pesar un per un i
només s'hi va afegir quan la frase és de debò un exemple del que ensenya la unitat:

| unitat | drills abans | ara | frases citables |
|---|---|---|---|
| estat d'annexió | 43 | 227 | 35 → 212 |
| ser, estar i tenir | 273 | 409 | 80 → 205 |
| derivació verbal | 40 | 154 | 26 → 138 |
| possessius | 280 | 320 | 69 → 106 |
| demostratius | 131 | 165 | 44 → 77 |
| fórmules | 24 | 49 | 13 → 36 |
| numerals | 128 | 151 | 70 → 92 |
| imperatiu | 183 | 198 | 65 → 79 |

## El que cal de tu

**Fusionar el PR #176.** En aquest mode no puc fusionar jo. Quan hi sigui, Render desplega i el
servidor escriu les 23 lliçons ell sol.

## Obert

- El correu encara no surt de Render (cal provar «Envia'm una prova» amb una clau de Brevo o
  Resend a la pantalla d'administració).
- `FRONTEND_URL` a Render encara apunta al domini vell.
- Les veus sintètiques en tamazight estan aturades expressament: no les vols.
