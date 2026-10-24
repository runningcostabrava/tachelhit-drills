# Auditoria del Mètode — 24-10-2026

Llegit el que serveix producció per als deu capítols (`GET /method/` i `/method/<slug>`).
Company de [`AUDITORIA_GRAMATICA_2026-10-24.md`](AUDITORIA_GRAMATICA_2026-10-24.md).

## On som

| cap. | capítol | escrit | seccions | frases a la biblioteca | **frases nostres al capítol** | imatges | preguntes | test |
|---|---|---|---|---|---|---|---|---|
| 1 | sons | sí | 6 | 24 | **0** | 0 | 0 | no |
| 2 | salutacions | sí | 10 | 207 | 26 | 0 | 0 | sí |
| 3 | el-cami | **no** | — | 1.257 | — | — | — | no |
| 4 | la-botiga | sí | 8 | 1.607 | 352 | 0 | 0 | sí |
| 5 | que-fas | **no** | — | 1.748 | — | — | — | no |
| 6 | el-mercat | **no** | — | 917 | — | — | — | no |
| 7 | qui-ets | **no** | — | 969 | — | — | — | no |
| 8 | el-metge | **no** | — | 1.114 | — | — | — | no |
| 9 | el-viatge | **no** | — | 1.571 | — | — | — | no |
| 10 | els-convidats | **no** | — | 1.632 | — | — | — | no |

**Set capítols de deu no estan escrits**, i tots set tenen entre 900 i 1.750 frases de la
biblioteca esperant-los.

---

## 1. El capítol dels sons no sona

Les sis seccions del capítol 1 porten `ours_total: 0`: **ni una sola frase nostra**. Tot el que
s'hi llegeix són les paraules del llibre —`imi`, `immi`, `aḍar`, `tiṭṭ`, `aɣrum`— escrites, sense
veu i sense imatge. Un capítol que diu «no passis d'aquí fins que distingeixis `imi` de `immi`»
i no deixa sentir cap de les dues no es pot fer servir.

La biblioteca sí que en té, de frases amb aquestes paraules. El que falla és el lligam:
`attach_library()` busca la veu d'una **paraula del vocabulari** entre les frases del capítol,
però no busca res per als **exemples** de les seccions, i per al capítol 1 la llista de frases
del capítol és buida, de manera que no hi ha on buscar.

**Què cal:** que una línia del capítol —exemple, fila de columna, fila de taula o paraula— trobi
la frase de la biblioteca que diu exactament això, a tota la biblioteca i no només a les frases
del capítol, i en prengui la veu i la il·lustració.

## 2. L'alfabet del capítol 1 està a mitges

La secció «L'alfabet del manual» arriba fins a la **ṣ**: catorze lletres de trenta-tres. Falten
t, ṭ, u, w, x, y, z, ẓ, ɛ, ḥ, h, k, kʷ, gʷ, i, j, l, c…, i amb elles la paraula que les porta.

Tenim d'on treure-les. Del vídeo «Apprends le Tamaziɣt berbère, leçon N°1» de Brahim Mansoub
(vegeu `CREDITS.md` §5b) hi ha una o dues paraules per lletra, i **26 estan confirmades, una per
una, al diccionari DGLAi** que ja tenim a `backend/knowledge/lexicon/`:

```
a  aɣrum pa · b bba pare · ḍ aḍil raïm · e tilelli llibertat · f afus mà · g agris gel
ḥ  aḥizun coix · ḥ aḥyuḍ boig · ž tujjut olor · k akal terra · k talkiwt finestra
l  alim palla · l aqlil gerra · m almu prat · q aqrab moneder · r adrar muntanya
ṛ  taɛṛabt àrab · t tadawt esquena · ṭ tiṭṭ ull · ṭ aṭṭan malaltia · u ul cor
w  tawla febre · x axlul moc · y tiyni dàtils · z azzar cabells · ɛ aɛban roba
```

Les altres 30 paraules del vídeo no són al DGLAi amb aquesta grafia (són verbs conjugats,
plurals o variants: `ičča`, `tuɣmas`, `iḍudan`, `siwel`…). **No entren** fins que una segona font
les confirmi: el vídeo és una classe, no un diccionari.

> La **veu** de les lletres —els 33 talls del vídeo del canal *Atlas*, alineats un per un amb la
> lletra que es veia a la pantalla— **no entra fins que ens donin permís**. Mentrestant, o bé la
> graven les nostres veus, o la secció es queda sense so i ho diu.

## 3. Cap capítol té imatges ni preguntes

Zero imatges a les seccions dels tres capítols escrits, i zero preguntes. Un `MethodExample` ni
tan sols té camp d'imatge, i una secció no té on posar una pregunta: això vol dir tocar el model
i la pàgina, no només el contingut.

El que hi ha a prop i es pot aprofitar: les il·lustracions que dibuixem per a les frases
(`/illustrations/`, que `attach_library` ja sap enganxar a una paraula del vocabulari) i les
preguntes de les unitats de Gramàtica, que ja existeixen i són de la mateixa matèria.

## 4. La prosa catalana sortia escrita en tifinag

La taula «Les set que no tenim» del capítol 1 servia això:

| so | explicació | la seva «tifinag» |
|---|---|---|
| ɣ | com la r francesa de «Paris» — aɣyul «ase» | `ⵛⵓⵎ ⵍⴰ ⵔ ⴼⵔⴰⵏⵛⴻⵙⴰ ⴷⴻ ⴱⴰⵔⵉⵙ ⴰⵖⵢⵓⵍ ⴰⵙⴻ` |

És a dir: la frase catalana sencera transliterada lletra a lletra, que no vol dir res. Arreglat a
#296 (PR #298): ara només reben tifinag les paraules que **només poden ser amazigues**. Queda
comprovar-ho a producció quan hi hagi desplegat.

## 5. Frases sense veu dins dels capítols escrits

`salutacions` 61 · `la-botiga` 271. Són frases de la biblioteca que el capítol ensenya i que no
es poden escoltar. La llista de què gravar ja existeix (`GET /grammar/wishlist`), però ordena per
unitat de gramàtica, no per capítol del Mètode.

---

## Què s'ha de fer, per ordre

1. **Lligar les línies del capítol amb la biblioteca** (§1): la més barata i la que més canvia.
2. **Acabar l'alfabet del capítol 1** amb les 26 paraules confirmades (§2), sense veu de tercers.
3. **Escriure els set capítols que falten** (3, 5, 6, 7, 8, 9, 10), un a un, amb els tres
   auditors de sempre.
4. **Imatges i preguntes**: camp d'imatge a l'exemple, bloc de preguntes a la secció (§3).
5. **Una llista de «què gravar» per capítol del Mètode** (§5).
6. Comprovar a producció que la tifinag de la prosa ja no hi és (§4).
