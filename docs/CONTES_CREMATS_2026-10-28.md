# Sis contes amb el text cremat a la imatge (28-10-2026)

Sis vídeos que el propietari ha passat el 28-10-2026, de **dos canals nous** per a nosaltres.
Això és un catàleg: diu què hi ha i com hi és. **No n'ha entrat res a la biblioteca**, perquè cap
dels dos canals no ha donat permís encara ([`PERMISOS.md`](PERMISOS.md)).

El que tenen en comú: **cap no porta subtítols pujats** (ni escrits per algú ni automàtics, que
tampoc no en voldríem). El text hi és **cremat a la imatge**, i la veu de qui narra el va dient a
sobre — o sigui frase, significat i so alineats, que és la forma d'una frase de la biblioteca.

| vídeo | canal | durada | com hi va el text | tall mesurat |
|---|---|---|---|---|
| `ce3s668AaSw` | Rajae Marzouki fg | 2:02 | caixa negra a baix: **tifinag + àrab** | 0.34, 0.855, 0.70, 1.0 |
| `6jN4ob9u4eQ` | Rajae Marzouki fg | 1:41 | a baix, sense caixa: **tifinag + àrab** | 0.20, 0.800, 0.80, 0.97 |
| `issyx0SahJc` | Rajae Marzouki fg | 3:08 | damunt del dibuix: **llatí en cursiva + tifinag** | 0.15, 0.520, 0.85, 0.82 |
| `13v1ggb7LJM` | Rajae Marzouki fg | 2:11 | damunt del dibuix: **llatí en cursiva + tifinag** | 0.14, 0.400, 0.87, 0.79 |
| `WMb3hNiuYLM` | Hafida Benkahia | 10:05 | plafó negre a la dreta, **un tros sencer en tifinag** | 0.42, 0.030, 1.00, 0.97 |
| `wcUZI6__nk4` | Hafida Benkahia | 2:23 | damunt del dibuix: **tifinag** | 0.15, 0.780, 0.85, 0.96 |

Els quatre números són el tros de pantalla on seu el text (esquerra, dalt, dreta, baix, en tant
per u), mirats un per un; viuen a `CAIXES`, dins de
[`tools/text_de_video/frases.py`](../tools/text_de_video/frases.py).

## Dues coses que canvien com s'han de tractar

**La varietat.** En Rajae Marzouki és de **Figuig** — ni taixelhit ni Atles central. Una frase
seva ha d'anar marcada com a seva (`variety`, `region`), i no es pot barrejar amb la resta com si
fos el mateix. La Hafida Benkahia encara no té varietat establerta; queda per mirar.

**El permís.** Els contes són obra de qui els explica i de qui els ha escrit; el dibuix de molts
d'aquests vídeos, a més, és de terceres persones. Mentre no contestin: se'n pot catalogar i
estudiar, i no hi entra ni la veu ni la imatge.

## Què s'hi ha fet, i fins on

L'eina ([`tools/text_de_video/`](../tools/text_de_video/)) en treu **una imatge per frase** amb
començament, final i el tall de veu que li correspon. Això prepara la lectura; **no la fa**: el
tifinag el llegeix una persona amb la carta de lletres del nostre transliterador al costat, i el
que en surti va a `*_suggested`.

Una comprovació feta, perquè consti que el camí funciona: a `ce3s668AaSw`, la primera frase del
conte es llegeix `ijjn wass n laz d tɣaṛt`, i l'àrab que hi ha a la mateixa caixa vol dir «un dia
dels dies de la fam i la sequera». Les dues línies diuen el mateix, i això és el que fa creïble
la lectura: no l'ha dit una màquina, i a més el mateix vídeo la contrasta.

## El que encara no va bé

- A `issyx0SahJc` el text seu damunt d'un dibuix amb **llumenetes que es mouen**, i el tall en
  surt massa partit (una frase per segon en comptes d'una cada pocs segons). Cal estrènyer-li el
  tros o separar les frases d'una altra manera.
- El detector automàtic de la caixa **no serveix** com a únic criteri: un vídeo l'encerta i al
  següent es queda el fotograma sencer. Per ara, mirar-ne un fotograma i apuntar-ho.
