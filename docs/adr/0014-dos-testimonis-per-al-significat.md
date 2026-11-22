# 0014 · Dos testimonis per al significat, i el desacord es catalogua

**Data:** 20-11-2026 · **Estat:** acceptat (decisió d'en Pablo) · **Issue:** #703

## Problema

El català d'una rèplica del SNRT surt de l'àrab cremat, traduït per dos models que es comproven
l'un a l'altre (`chrf_ab ≥ 0,5` → «confirmat»). En Pablo ho va veure abans que jo: «és molt
important que tinguem un lector OCR d'àrab perfecte, si no les traduccions seran falses».

**Dos traductors del mateix text no són dos testimonis.** Si l'OCR llegeix malament una paraula
àrab, tots dos tradueixen la paraula equivocada i hi estan d'acord: l'acord actual mesura si dos
models tradueixen igual, i **no pot detectar un error de lectura**. És l'únic punt de la cadena
on un error és invisible — el tifinag en té un de segon (l'orella: si l'OCR falla, deixa de casar
amb el so), i l'àrab no en té cap.

Dues coses més, mesurades sobre l'episodi `QhO1I6l2w_k` (20-11-2026):

- el testimoni que sí que ho detectaria —el tifinag, **un altre OCR d'una altra escriptura**— ja
  és al codi (`catala_de_tifinag`, `chrf_tif_ar`) i **no s'executa mai**: viu en un Space gratuït
  que es dorm (`Space no disponible: The read operation timed out`; **0 de 851** rèpliques el
  tenen);
- i el que no arriba a l'acord es **llença**: 142 rèpliques (17 %). Mirades una per una, el
  llindar castiga les maneres de dir diferents: dues traduccions amb chrF 0,30 deien exactament
  el mateix (una data i un títol) i es van perdre totes dues.

## Opcions

1. Un tercer traductor de l'àrab. **No serveix:** comparteix l'error de lectura amb els altres dos.
2. Un OCR d'àrab millor. Cal igualment, però no fa l'error detectable: el fa menys freqüent.
3. **Creuar les dues escriptures i catalogar el desacord (triada).**

## Decisió

**El significat es corrobora per vies, no per traductors.** Tres vies, i el que val és que no
comparteixen els errors:

| via | d'on surt | independent de |
|---|---|---|
| A · àrab → català | el subtítol àrab | el nostre OCR de tifinag, la nostra orella |
| B · tifinag → català | el subtítol tifinag | la nostra orella |
| C · el que diu la veu → català | la nostra orella | el subtitulador sencer |

Aquest ADR fa A i B. La via C queda per a un altre, perquè demana decidir què es tradueix quan
l'orella escriu dialectal.

- **El NLLB en local**, `josepabloucr/nllb-600m-tamazight-catala-ct2-int8` (CTranslate2 int8, CPU),
  en comptes del Space. Gratis i no es dorm.
- **Estats nous de `catala_estat`:** `creuat` (A i B coincideixen: corroborat per dos OCR
  independents, el millor que tenim), `confirmat`, `tercer`, i **`sense_acord`** en comptes de
  `descartat`.
- **El desacord es catalogua.** `sense_acord` desa les lectures i una `catala_proposat` marcada
  com a proposta. **El camp `catala` només es omple quan hi ha acord**, de manera que res no
  presenta com a fet un significat que no ho és.
- **Cap porta nova encara.** `chrf_tif_ar` es desa i es mesura, però **no descarta res**: primer
  cal saber quina part del desacord entre A i B és error d'OCR i quina part és que el nostre
  traductor és fluix. Tinc apuntat que discrepaven el 78,7 % de les vegades, i tancar la porta
  amb aquell número llençaria la major part del corpus per la raó equivocada.

## Conseqüències

- Qui llegeixi el catàleg ha de distingir **quatre** estats, i la pantalla ha de marcar-ho: una
  frase `creuat` i una `sense_acord` no poden semblar iguals (`docs/SCOPE.md`: qui aprèn no pot
  aprendre coses falses sense saber-ho).
- La fàbrica puja de dependències: el model de traducció es baixa un cop (uns 600 MB) i es desa a
  `<TD_TV>/models/`. A canvi, l'etapa 04 deixa de dependre d'un Space que es dorm.
- La traducció del tifinag costa CPU on abans costava una crida: més lent per episodi, zero
  diners. Amb la quota del Model Studio esgotada el 20-11, això ha passat de millora a condició.
- Quan es calibri el llindar de `chrf_tif_ar`, caldrà un ADR nou: aquell sí que tancarà una porta.
