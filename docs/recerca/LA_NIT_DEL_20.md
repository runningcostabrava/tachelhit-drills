# La nit del 19 al 20 de novembre, en una pàgina

*El detall és a `DESXIFRAT.md` §12 i §13; el mètode, a `METODE.md` §9.*

## El que s'ha trobat

**Els 25 capítols de *Tadfi n Tskla* no són una llengua: són tres.** Un convidat per episodi, i
cadascú parla la seva.

| varietat | episodis | hores | acord ull↔orella |
|---|---|---|---|
| tachelhit | 11 | 7,95 h | **27,2 %** |
| amazic de l'Atles central | 3 | 2,07 h | 19,3 % |
| tarifit | 11 | 7,67 h | **1,6 %** |

Això era l'enigma de la nit: deu episodis amb ~1 % d'acord entre el que es veu escrit i el que
el nostre model sent. No era cap avaria. **La nostra orella és de tachelhit i aquells convidats
són del Rif.**

**I una correcció de les 04:00, que és la part més important:** «el model no entén aquells
parlants» era massa fort. **L'orella els sent, almenys en part; el que no casa és el subtítol.**
Mesurant els arabismes —paraules que el convidat diu i que el subtítol àrab també escriu— surt
que als episodis rifenys l'orella n'encerta **igual o més** que als tachelhit (3,8 % contra
2,4 %) i en canvi casa amb el tifinag tres vegades menys (12,8 % contra 38,3 %). El subtítol està
escrit en la norma de l'IRCAM, i per al rifeny la norma canvia el **vocabulari sencer**.

I això té un abast que va més enllà del Rif: **el sostre de l'acord no el posa la nostra orella,
el posa el subtitulador.** On la pantalla escriu *amawal* el convidat diu *lmuεjam* (المعجم); on
escriu *amzruy*, diu *ttariġ* (التاريخ); on escriu *tufrayin*, diu *lmašaεir* (المشاعر). El
subtítol escriu el neologisme de l'IRCAM i la gent diu el manlleu. Per això el tachelhit s'atura
al 38 % i no hi pujarà, per bo que es torni el model.

Tres conseqüències que valen més que l'explicació:

1. **L'acord de debò sobre tachelhit és 27,2 %, no el 13 % que deia ahir.** Aquell 13 %
   barrejava tres llengües i castigava el lector amb episodis que no eren del seu idioma.
2. **Tenim 2,07 hores d'amazic de l'Atles central**, que és la varietat que aquest projecte
   documenta (Aït Mraw, Azilal–Kalaat M'Gouna). Estava amagada dins del promig.
3. **I 7,67 hores de tarifit**, una varietat molt més pobra en recursos, amb so, subtítol, àrab
   i català. No és rebuig: és un corpus — i, vist el de dalt, **no és un corpus de transcripció
   sinó de traducció**: parla rifenya amb el seu significat escrit en la norma. Que també serveix,
   però per a una altra cosa.

## Com se sap, i per què s'hi pot confiar

Tres senyals **independents**, i cap no necessita que ningú tradueixi res a mà:

1. **El presentador diu d'on és el convidat**, i això arriba per l'àrab → català, un camí que no
   toca ni el nostre OCR ni la nostra orella. Correlació de les mencions del Rif amb l'acord:
   **−0,79**. Acord mitjà on domina el Rif: 1,7 %; on no: 22,7 %.
2. **Dues marques fonètiques al so**, que soles separen les tres varietats: k→š creix d'oest a
   est (1,8 % → 5,7 % → 12,1 %) i l→r marca el rifeny (1 % → 1,3 % → 12,9 %).
3. **L'acord mateix**, que es desploma quan la varietat no és tachelhit.

Abans d'arribar-hi es van descartar, una per una i amb mesura, set explicacions meves: que l'ull
llegís malament (l'àrab el confirma paraula per paraula), un índex desplaçat (d=0 guanya als 22),
un desfasament en temps, que parlessin àrab (un transcriptor d'àrab de debò: 1 encert de 625),
frases massa llargues (correlació −0,09), so dolent (nivell i instant correctes), l'orella que
es menja finals (és més llarga el 40 % de les vegades), el subtítol condensat i la banda estreta
(idèntica).

## El que també s'ha arreglat

| | abans | ara |
|---|---|---|
| capítols amb lectura utilitzable | 19 de 25 | **25 de 25** |
| rèpliques de grau A amb significat | 1.560 | **2.190** (2,14 h) |
| formes amb índex de fiabilitat | — | **39.274**, 680 al nucli |
| taula de variació consonàntica | — | **97 parelles** |
| català sense trencaments objectius | — | **99,5 %** |

Quatre capítols donats per morts (0,0 % d'acord) van de 0 a 17–30 % només rellegint-los del
vídeo de 1080p amb la seva franja. I el `kab` contra el `shi` sobre 3.515 talls: **guanya el
`shi`** (21,8 % contra 20,2 %), o sigui que no hi havia millora gratuïta.

## El que he hagut de desdir-me

Cinc vegades, i totes del mateix vici — **llegir una regularitat en un grapat d'exemples triats
per mi**:

- les **13.422 paraules de grau A** estaven inflades pel doble: l'aparellament no mirava l'ordre.
  Són **6.779**.
- les **181 parelles norma↔parla** eren artefactes d'alineació. Filtrades honestament queden 8, i
  totes vuit són la mateixa frase desplaçada un lloc.
- la **fàbrica no guanya** als capítols bons: aquell número era d'abans d'arreglar la geometria.
- el **ġ~ḫ no és nostre**: amb 37 paraules semblava que sí, amb 377 les dues orelles el fan igual.
- i **Said Ou Boulman no és rifeny**, encara que la meva primera regla ho digués: és l'episodi
  amb més acord de tots.

## L'orella rifenya: provada, i la meva hipòtesi refutada

Vaig buscar una orella de rifeny per obrir aquelles vuit hores, i n'hi havia dues. El resultat:

| | el nostre `shi` | el rifeny |
|---|---|---|
| als 2 episodis **tachelhit** | 37,6 % | **26,6 %** |
| als 10 episodis **rifenys** | 0,4 % | **0,4 %** |

Aquell 26,6 % és la clau: el model rifeny **sí** que sap casar amb un subtítol en tifinag
estàndard quan el subtítol diu el que es parla —ho fa escoltant tachelhit, que no és la seva
llengua— i escoltant **la seva pròpia llengua** cau al 0,4 %. O sigui que no hi ha cap orella que
pugui obrir aquells episodis, perquè el que hi ha escrit no és el que s'hi diu.

La predicció que vaig escriure deia «el rifeny ha de ser millor al tarifit i pitjor al
tachelhit». La segona meitat es compleix i la primera no: **la prova que vaig dissenyar per
confirmar la meva hipòtesi l'ha refutada.**

I perquè no quedés l'excusa que els dos models comparteixen base, una tercera orella que no
comparteix res (un Whisper afinat en rifeny, altra arquitectura, altra ortografia): als episodis
rifenys coincideix amb la nostra el **35,8 %** i amb el subtítol el **0,0 %**.

La cadena sencera, cinc mesures independents i una rèplica exacta CPU–GPU, és a `DESXIFRAT.md`
§15.6.

## El que es pot fer amb les vuit hores de rifeny

No són un corpus de transcripció, però les dues orelles coincideixen entre elles al 67,6 %, i
això és un **pseudo-transcrit de consens**: unes **4.492 rèpliques (5,2 hores)** amb transcripció
i significat, de grau C — no verificat, però catalogat. El que el pujaria a grau A no és tècnic:
**cent línies llegides per algú del Rif** donarien la mesura de quant val el consens.

## La ronda: el cercle es tanca per primera vegada

Train de 3.090 talls (3,14 h): 1.669 del grau A més 1.421 de Zouhir. Cinc proves, abans i
després, amb interval de confiança:

| prova | Δ CER | interval 95 % | |
|---|---|---|---|
| snrt-retingut | −0,0133 | [−0,0196, −0,0073] | **millora** |
| zouhir-tests | −0,0128 | [−0,0177, −0,0080] | **millora** |
| test-fora (parla nostra mai sentida) | −0,0121 | [−0,0240, −0,0025] | **millora** |
| cv-zgh-test (256 clips nets) | −0,0023 | [−0,0069, +0,0023] | no es pot dir |
| tfa-226 | +0,0026 | [−0,0025, +0,0079] | **no empitjora** |

La regla del cercle demana que cap prova no empitjori amb interval i que almenys dues millorin.
**Cap no empitjora i tres milloren: `adopta = True`.** És la primera ronda que passa la seva
pròpia regla.

I el que ho ha fet no és un model millor: és **la selecció del corpus**. El filtre de qualitat
del nucli passava el **0,9 %** dels talls el 17 de novembre i ara passa el **80 %**, perquè
compara esquelets de consonants en comptes de text amb vocals contra un subtítol que no les
escriu.

**Els quatre capítols retinguts, i la predicció:**

| | abans | després | |
|---|---|---|---|
| Akounad (tachelhit) | 0,5768 | 0,5392 | **−3,8 punts** |
| Zahour (tachelhit) | 0,6955 | 0,6592 | **−3,6 punts** |
| Abarnous (tarifit) | 0,8271 | 0,8272 | +0,0 |
| Khbiza (tarifit) | 0,9072 | 0,9389 | **+3,2 punts** |

Havia predit que milloraven els dos de tachelhit i que els dos de tarifit no es movien. Els de
tachelhit milloren gairebé quatre punts en capítols **sencers i mai vistos**; l'Abarnous no es mou
gens; i el Khbiza **empitjora**, que és més del que havia dit i confirma des d'un altre lloc que
són llengües diferents.

**Adoptar M₁ és decisió teva**, no meva: el model és de recerca i no es desplega enlloc. El que
diu la regla és que qualifica.

## Dues coses aturades i una errada meva

- **El Baba Ali** (190 talls dels 240) i **les tres orelles sobre els episodis rifenys**: el
  sistema va aturar les feines locals per falta de memòria i no les he reprès sense demanar-ho.
- **La ronda es va reiniciar a les 04:36 per un descuit meu**: vaig deixar viu un guió de cua que
  la tornava a llançar quan s'alliberés GPU. El resultat és vàlid (passada completa de 68 minuts
  amb les mateixes dades), però la primera hora i vint es va perdre.

## El que espera la teva mà

`posa_el_text_triat_al_visor.py --escriu` — posa el text bo als dotze capítols on la relectura
guanya. Està escrit i comprovat, i no l'he executat: és una escriptura a producció, no me l'has
demanada, i el 29 d'octubre una càrrega massiva va deixar sense memòria un treballador de Render.
