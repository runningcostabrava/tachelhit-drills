# Treure el text cremat d'un vídeo

Molts dels vídeos que ens serveixen —contes, taules de gramàtica, lèxic— **no porten subtítols**.
El text hi és, però escrit a dins de la imatge, i la veu de qui parla el va dient a sobre. Aquesta
carpeta prepara aquest material perquè es pugui **llegir**; no el llegeix ella.

Aquesta distinció és tota l'eina. El que en surt és una imatge per frase, amb el seu començament,
el seu final i el tall de veu que li toca. Qui decideix què hi diu és una persona, i el que en
surti entra com a `*_suggested` fins que algú ho confirmi: el text de qui parla és sagrat i no el
pot escriure una màquina.

## Per què no l'OCR

El nostre Space d'OCR llegeix llatí i àrab de subtítols enganxats a baix
([`docs/OCR_FEATURE_SCOPE.md`](../../docs/OCR_FEATURE_SCOPE.md)), i el gruix d'aquest material és
**tifinag**, que els OCR de fora amb prou feines saben llegir.

El que sí que funciona és mirar-s'ho amb la carta de lletres al costat
(`carta_de_lletres.py`), que surt del **nostre propi transliterador** —les mateixes parelles que
fa servir tota l'app— i per tant no afegeix cap criteri nou. A més es comprova sola quan el vídeo
escriu les dues coses: en una taula d'Ait ouarab el títol deia `ⵉⵎⴷⵢⴰⵜⵏ` i el llatí de sota deia
«imdyatn», que és exactament el que en surt signe a signe.

## Les quatre eines

```bash
export TEXT_DE_VIDEO_DIR=~/feina-video      # on van els vídeos i els retalls (fora del repo)

python tools/text_de_video/carta_de_lletres.py          # la carta tifinag -> llatí, per llegir
python tools/text_de_video/pantalles.py <id> --cada 2   # els fotogrames, i una pantalla per tanda
python tools/text_de_video/frases.py <id> --cada 1      # una imatge i un tall de veu per frase
python tools/text_de_video/tira.py <id> 1 8             # vuit frases en una imatge, per llegir-les
python tools/text_de_video/zoom.py <id> 507 0.02,0.15,0.30,0.30 5   # un tros petit, ben gros
python tools/text_de_video/prova_paraules.py izm ixf izf            # com s'escriurien, per comparar
```

## Com es comprova una lectura

Llegir no és endevinar. Quan dos signes s'assemblen —la `x`, la `z` i la `f` són els pitjors—,
**no es tria el que sembla**: s'escriuen les paraules candidates amb el nostre propi
transliterador (`prova_paraules.py`) i es comparen signe a signe amb el `zoom.py` de la pantalla.

Això va passar de debò: a la classe de l'estat d'annexió, dues files eren `izm` o `izf`, i `ixf`
o `izf`. Escrites les tres, la diferència es veu de seguida —la `z` porta un pal al mig de la X i
la `x` no—, i les dues files van quedar resoltes. El que abans anava marcat com a dubtós ja no
ho és, i ho diu el fitxer de dades (`backend/data/annexio.json`, camp `com`).

La regla que se'n deriva: **si després de mirar-ho gros encara dubtes, es queda marcat com a
dubtós i no surt a l'app.** Una lectura insegura que s'ensenya és pitjor que una casella buida.

`pantalles.py` va bé per a **classes amb diapositives** (una taula que s'omple mentre el mestre
parla); `frases.py`, per a **contes amb el text a la imatge** (una frase que canvia cada pocs
segons, amb la veu al damunt).

## El que hem après fent-ho, i que costa de tornar a trobar

- **El vídeo sol.** Per llegir no cal l'àudio dins del vídeo: baixant només la imatge es paga la
  meitat. La veu es baixa a part, perquè és la que es talla per frases.
- **Sense el client `android`, el YouTube diu que vídeos ben vius «no estan disponibles».** Dos
  dels sis contes queien així.
- **La pantalla bona és l'última de la tanda, i quieta.** Una taula es va omplint fila a fila: la
  primera imatge és la taula buida. I just al final hi ha l'animació de passar full, amb mitja
  taula doblegada. Per això es busca l'última imatge **quieta** de cada tanda.
- **La caixa del text no és «el tros de baix».** El dibuix es mou tota l'estona i, si entra al
  retall, cada segon sembla una frase nova. Per això es mesura **només** el tros on seu el text.
- **I aquest tros canvia de canal a canal**, de manera que va escrit a mà a `CAIXES`, dins de
  `frases.py`, mirant un fotograma de cada vídeo. Hi ha un detector automàtic, però proposa: un
  vídeo l'encerta i al següent es menja el fotograma sencer. Mirar-ne un fotograma costa un cop
  d'ull i no falla.
- **Val més tallar de més que de menys.** La primera versió només es quedava les caixes negres amb
  lletra blanca, i d'un conte que en té trenta en treia zero perquè el text hi anava damunt d'un
  dibuix groc. Unes quantes imatges de sobres es llencen amb un cop d'ull; una frase perduda, no.

## El permís no el dona cap eina

Això prepara material de **fonts de fora**. Abans que res d'aquí entri a la biblioteca, mira
[`docs/PERMISOS.md`](../../docs/PERMISOS.md): mentre un canal no hagi dit que sí, se'n pot
catalogar i estudiar, però la seva veu i les seves imatges no entren. El crèdit, en canvi, hi va
sempre: canal, obra, enllaç i minut.

I una cosa que és fàcil de perdre: **la varietat**. Un conte de Figuig no és taixelhit ni Atles
central. Una frase que en surti ha de dir d'on és.
