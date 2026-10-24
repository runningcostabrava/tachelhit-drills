# Auditoria de les 23 unitats de Gramàtica — 24-10-2026

Llegit **el que serveix producció**, no el que diu el codi: les 23 unitats i els seus 23 nivells
«a fons», tal com els rep una persona que obre l'app (`GET /grammar/<slug>` i `/deep`).

> Com es refà: `fetch_units.py` baixa les unitats, `audit_units.py` passa les comprovacions
> mecàniques i `render.py` les converteix en text llegible. Els tres són a l'scratchpad de la
> sessió; el que importa és el que hi ha escrit aquí.

## El resum

L'**estructura** està bé i no s'ha de tocar: cada unitat té entre 19 i 25 passos, de 6 a 9
explicacions, de 9 a 12 preguntes, una taula, un consell i una nota de dialecte. Les 23 unitats
resolen **totes** les seccions del compendi que citen (de 1,7 k a 45 k caràcters de referència):
la canonada d'amazic.cat funciona.

El que falla és **el que s'hi posa a dins**: quines frases s'ensenyen, què se'n diu, i què es
promet en una taula que després no se sent enlloc.

---

## 1. El nivell «a fons» no existeix — 22 de 23 unitats

Només `possessius` té el seu nivell «a fons» escrit (32 passos). Les altres 22 responen
`writing: true` i dos passos de farciment («S'està escrivint aquesta lliçó ara mateix»).

No s'escriuen perquè Gemini està a 402 des del 23-10 (#295). I quan torni a escriure'n, hi ha
un segon problema: `main.py` només li passa el compendi **si Gemini està disponible** —

```python
lesson = grammar_course.get_lesson(db, slug, _load_grammar() if gemini_available() else "", …)
```

— de manera que, amb DeepSeek de reserva (#297), una lliçó es pot reescriure **sense el compendi
d'amazic.cat a la mà**. Això s'ha d'arreglar abans de reescriure res.

## 2. Les notes «per què hi és» diuen coses que no són

Cada frase d'una lliçó porta una nota automàtica. Moltes són correctes; moltes altres són
farciment repetit, i unes quantes són **falses**. De la unitat dels sons:

| frase | el que diu la nota | què hi ha |
|---|---|---|
| `lxdmt` «feina» | «la 'l', la 'x', la 'd' i la 'm' actuen com a nuclis sil·làbics» | quatre nuclis en una paraula de dues síl·labes: no |
| `akshud` «fusta» | «ens mostra les tres vocals fonològiques de l'amazic: /a/, /u/» | en diu tres i en compta dues |
| `trt` «busca-la» | «la 'r' i la 't' actuen com a nuclis sil·làbics, un tret distintiu» | la mateixa frase, igual, a quatre paraules diferents |
| `Shore` «espera'm» | «podria ser una transliteració que no reflecteix el sistema vocàlic» | això és un defecte de la nostra grafia, no una lliçó |

I el vocabulari: **uvular, al·lòfon, tautosil·làbic, nucli sil·làbic, faringal fricativa sonora,
atac sil·làbic** — a una unitat de nivell 1, per a algú que no ha estudiat lingüística.

El redactor ja té una llista de paraules prohibides (`BANNED_TERMS`) i la instrucció de respondre
«-» quan una frase no ensenya res de la unitat. Cap de les dues coses es **comprova** després:
si el model les ignora, la nota s'escriu igual.

## 3. Hi ha exemples que no mostren el so (o el punt) que s'explica

A la unitat dels sons:

- **§9, el so š**: els exemples són `Shore`, `Shora`, `tshua`, `skrtn`, `Sharjm`, `3afaš`.
  `skrtn` «mireu-les» **no té cap š**.
- **§11, «Consonants emfàtiques: ṭ, ḍ, ṣ, ẓ»**: els exemples són `ishQa`, `SSukr`, `AzrQiy`,
  `Annojo`, `Lishiber`, `Tazerbit`. **Cap no porta ḍ ni ẓ**; dos són exemples de la vocal breu.
- **§1, «Les vocals bàsiques: a, i, u»**: obre amb `Zr` i `trt`, dues paraules **sense cap vocal**.

A `imperatiu`, dues explicacions («Ordres per a 'vosaltres' (femení)», «Imperatius inclusius»)
es queden **sense cap exemple**: la biblioteca no en té, i la lliçó no ho diu.

## 4. Les taules prometen formes que no se senten enlloc

De 175 caselles de taula amb una paraula amaziga, **65 no surten a cap exemple de la unitat**.
Una part és normal (una taula de numerals ha de ser sencera encara que no tinguem gravat el «sis»),
però la persona que aprèn no ho sap: veu `smmus`, `ṣḍiṣ`, `-nnɣ`, `-nnun`, `nttat`, `allig`,
`assatx` i no les pot escoltar enlloc.

I dues són **inventades**: la taula «Sons difícils i la seva escriptura» cita `meddn` per a la ḍ
(no en té, de ḍ) i `Tabrat` per a la ṭ — paraules que no són a la unitat.

## 5. Frases sense veu dins la lliçó

| unitat | exemples a la lliçó | sense veu |
|---|---|---|
| `numerals` | 54 | **21** |
| `demostratius` | 26 | **9** |
| `pronoms-personals` | 49 | 9 |
| `adjectius-qualitat` | 41 | 5 |
| `ser-tenir`, `temps-adverbis` | 47 / 51 | 4 |
| `negacio` | 51 | 3 |

La tria ja posa davant les frases amb veu i imatge; quan la unitat no en té prou, hi entren les
mudes. `numerals` i `demostratius` són les que més pateixen, i són de nivell 1.

## 6. Les grafies de xat, dins la lliçó que ensenya les lletres

42 frases diferents escrites a l'estil del mòbil — `3` per ɛ, `gh` per ɣ, `kh` per x, `sh` per š,
`Q` per q, `x` per ɣ — surten com a exemples del curs:

```
3afaš · i3rQ · A3wni · shba3 · ifq3 ghif-Rashid · jm3 ixf-nnsh!
astkh golaghd 3trgh achko jngh · ha n3na3 · lsigh ihroyn fisa3 astkh
```

El text del parlant **no es toca** — és seu. Però la unitat que ensenya que la ɛ s'escriu `ɛ` no
hauria de triar, podent-ho evitar, la frase que l'escriu `3`. Hi ha 779 frases diferents entre
les 23 unitats: n'hi ha prou per triar.

## 7. Procedència

Les varietats són les nostres (Beni Mellal 515, Aït Mraw/Azilal 410) — això està bé. Però **115
exemples no porten cap procedència** i **56 porten «gravació»**, que no és un lloc. La nota de
dialecte de cada unitat sí que anomena la nostra varietat (23 de 23).

## 8. La tifinag desada de 9 frases ha perdut lletres

Comparant la tifinag guardada amb la que en treu el transliterador d'avui: 9 frases de 779 hi han
perdut una lletra, sempre la mateixa mena — la `ʷ` alçada, la `ġ` i la `ε`:

| id | llatí | desada | hauria de ser |
|---|---|---|---|
| 3906 | `igʷma` | ⵉⴳⵎⴰ | ⵉⴳⵯⵎⴰ |
| 3685 | `izelleε digh taḍut` | ⵉⵣⴻⵍⵍⴻ ⴷⵉⵖ ⵜⴰⴹⵓⵜ | ⵉⵣⴻⵍⵍⴻⵄ ⴷⵉⵖ ⵜⴰⴹⵓⵜ |
| 447 | `ur ġiġh ad ssnuġ…` | ⵓⵔ ⵉⵀ ⴰⴷ ⵙⵙⵏⵓ… | ⵓⵔ ⵖⵉⵖⵀ ⴰⴷ ⵙⵙⵏⵓⵖ… |

(les altres: 448, 3414, 3934, 3974, 6704, 6705). Es refà amb el transliterador, que ja ho entén
des de #296: no és text de ningú, és una conversió.

> **Esmena, el mateix dia.** Nou n'eren poques. Aquesta comparació es va fer amb el text tal com
> ve de la base de dades, i resulta que **283 frases —275 amb veu— guarden les lletres separades**:
> la `š` és una `s` i un capelló a part, la `ġ` és una `g` i un punt a sobre a part. El
> transliterador no les veia i servia una ALTRA lletra: `sġix` sortia `ⵙⴳⵉⵅ` (una g) i `3afaš`,
> `ⵄⴰⴼⴰⵙ` (una s) — totes dues, exemples d'aquesta mateixa unitat dels sons. Arreglat a **#304**
> (PR #305): `to_forms()` i `sound_key()` ajunten el text abans de mirar-lo. Qualsevol comprovació
> futura sobre `ɣ ɛ ḥ ḍ ṭ ẓ ṣ ṛ š` dins el text d'un drill ha de fer el mateix, o es deixa una
> desena part de la biblioteca fora sense adonar-se'n.

---

## Què s'ha de fer, per ordre

1. **Que el compendi arribi sempre a qui escriu la lliçó**, Gemini o DeepSeek (§1).
2. **Comprovar la nota abans de desar-la**: fora jargó, fora citacions que no són a la frase, i
   «-» quan la frase no ensenya res (§2).
3. **L'exemple ha de portar el que s'explica**: a la unitat dels sons, el so; a les altres, la
   marca del punt. Si no n'hi ha, dir-ho en comptes d'omplir (§3).
4. **Marcar a les taules el que no tenim gravat**, i treure les caselles inventades (§4).
5. **Triar les frases ben escrites quan n'hi hagi**, sense tocar el text de ningú (§6).
6. **Refer la tifinag de les 9 frases** (§8) i netejar «gravació» com a procedència (§7).
7. **Escriure els 22 nivells «a fons»** que falten, un cop 1 i 2 estiguin fets (§1).

Res d'això demana reescriure una sola frase d'un parlant.
