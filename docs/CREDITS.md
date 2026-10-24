# Crèdits i fonts

Aquesta app no s'aguanta sola: la llengua la posen els parlants, i la gramàtica, el lèxic i el
transcriptor els posa gent que ha publicat la seva feina perquè algú l'aprofiti. Aquí hi ha qui
és, què n'hem fet, i què ens obliga cada llicència.

Regla de la casa: **res de tercers entra al projecte sense quedar escrit en aquest fitxer**, amb
el nom de qui ho ha fet i la seva llicència. Si una llicència demana una citació concreta, la
citació va aquí sencera, tal com la demanen.

---

## 1. Les veus i les frases

El gruix de la biblioteca són gravacions de parlants que han dit les frases per a aquest projecte
— **Halima Akajji** i **Driss Akajji** (Aït Mraw), i els reculls de Beni Mellal i Azilal.
Sense les seves veus no hi hauria ni curs ni Mètode: la llengua que s'ensenya aquí és la que
diuen ells.

Cada drill porta qui parla
(`speaker`, `author`), d'on és (`variety`, `region`) i la llicència que va triar qui va gravar
(`license`; el reproductor la mostra al costat del so). El text del parlant no es reescriu mai amb
una màquina: la sortida automàtica va a `*_suggested` i la decideix una persona.

Material capturat de tercers (vídeos, cançons) guarda `source_url`, `source_title`,
`source_channel`, `source_playlist` i `license`, i el reproductor els ensenya. Les imatges de
domini públic o lliures porten `image_credit`, visible sobre la mateixa imatge.

## 2. La gramàtica del curs

**Compendi de Gramàtica Amaziga**, publicat a [amazic.cat](https://www.amazic.cat/) — autors
**Carles Múrcia** i **Salem Zenia**, amb la col·laboració de Hassan Akioud, Aziz Baha, Said
Bobouh, Carles Castellanos, Marta Barberan, Ali Ait Yahya, Hicham Essahil, Irene Teixidor i
Hassane Benamara; coordinació de la digitalització, Sara Serrano. Primera edició en línia: gener
de 2018.

Les 23 unitats del curs segueixen els capítols del compendi, i el redactor de lliçons en llegeix
les seccions numerades per escriure cada unitat. **Els PDF no es committegen**:
`backend/build_knowledge.py` els baixa d'amazic.cat quan falten i n'extreu el text a
`backend/knowledge/amazigh_grammar.md` (gitignorat).

> **Pendent de verificar:** les pàgines públiques d'amazic.cat no porten cap nota de llicència ni
> de copyright per al compendi. Mentre no ho sapiguem, el tractem com a material de tercers amb
> tots els drets reservats: se cita, no es redistribueix, i el text extret no surt del repositori.

## 2b. El Mètode

L'àrea **El Mètode** és una adaptació, capítol per capítol, d'un manual publicat:

> **Abdallah El Mountassir**, *Méthode de Tachelhit. Langue amazighe (berbère) du sud du Maroc*,
> L'Asiathèque — Maison des langues du monde, Collection Langues & Mondes, París, 2009.
> Edició italiana: *Metodo di tachelhit. Lingua amazigh (berbera) del sud del Marocco*,
> Università degli Studi di Napoli «L'Orientale», Studi Africanistici — Quaderni di Studi Berberi
> e Libico-berberi 6, 2017.

El Mètode el **segueix tan a prop com calgui**: explicacions, estructura, diàlegs i lèxic. El
que es canvia és el que la nostra varietat (Atles central) diu d'una altra manera; la resta es
queda com és. L'autor n'està assabentat i hi està d'acord (23-10-2026).

**El que segueix sent nostre i no ve d'enlloc més:** les veus. Cap frase del Mètode sona si no la
diu una persona de debò que el projecte conegui, i cap veu sintètica es fa passar per amazic. El
llibre pot donar el text; qui el diu el posem nosaltres.

**La varietat es diu sempre.** El manual és tachelhit del Souss i nosaltres ensenyem Atles
central: quan una frase ve del llibre i encara no està adaptada, es diu, i quan en tenim una de
nostra que diu la mateixa cosa, s'ensenyen de costat.

Cada capítol porta aquesta citació al peu. La decisió és a
[ADR 0004](adr/0004-el-metode-parteix-del-llibre.md), que substitueix
l'[ADR 0003](adr/0003-el-metode-pren-el-pla-mai-les-paraules.md) (el que es va decidir abans de
tenir permís, i que es conserva com a registre).

> **Apuntat per si algun dia fa falta:** el que hi ha és de paraula, i l'edició italiana es va
> fer «per gentile concessione dell'autore **e di L'Asiathèque**» — també de l'editorial, que té
> els drets d'edició del llibre de 2009. Un correu que ho deixi per escrit no costa res.

## 3. El lèxic

- **IRCAM — DGLAI**, diccionari general de l'amazic estàndard marroquí
  (`Tamazight-NLP/ircam-dglai`), **CC BY-NC 4.0**. 18.491 entrades. Les glosses que en surten
  van marcades `[IRCAM-DGLAI]` allà on es mostren.
- **IRCAM — «Manuel de conjugaison de l'amazighe»** (`Tamazight-NLP/ircam-conjugations`),
  **CC BY-NC 4.0**. 3.507 verbs.
- **Diccionari anglès–taixelhit de Lahcen Oulhaj** (`Tamazight-NLP/English-Tashlhit-Dictionary`).
  **Tots els drets del contingut són de l'autor**; aquí només fa de base de consulta privada per a
  una app d'aprenentatge personal, i no es redistribueix.

Cap d'aquests fitxers es committeja: `backend/lexicon.py` els baixa de HuggingFace al primer ús,
a `backend/knowledge/lexicon/` (gitignorat).

**Què ens obliga el «NC»:** les dues fonts d'IRCAM no es poden fer servir per guanyar-hi diners.
Això aquí no lliga res, perquè **aquesta app no tindrà mai ús comercial** — decisió de l'amo,
22 d'octubre del 2026, i és una frontera del projecte, no una conseqüència d'aquestes llicències
([SCOPE.md](SCOPE.md)). Si algun dia algú es repensés això, el primer que caldria mirar és
justament aquesta secció: caldria treure IRCAM del lèxic o demanar-ne permís.

## 4. El transcriptor i l'alineador

- **Model:** `ayymen/stt_zgh_fastconformer_ctc_small` — NeMo FastConformer CTC entrenat amb
  Common Voice (amazic estàndard marroquí), **CC BY 4.0**. Escriu tifinag. És el que fa anar el
  Space `Tamazight-NLP/ASR`.
- **Alineació forçada:** `align.py` i `utils/` del nostre Space són el
  `tools/nemo_forced_aligner` de **NVIDIA NeMo**, **Apache 2.0**, tal com els fa servir el Space
  `Tamazight-NLP/NeMo-Forced-Aligner`.

## 5. Els corpus amb què mesurem

Aquests no entren a l'app: serveixen per saber què val el transcriptor
(`tools/asr_eval.py`, informes a `docs/ASR_EVAL_*.md`).

### Mozilla Common Voice (via Mozilla Data Collective)

- **Common Voice Scripted Speech 27.0 — Tamazight (`zgh`)**, `cv-corpus-27.0-2026-09-11`,
  **CC0**. 2.229 clips de 51 parlants; 1.474 validats.
- **Common Voice Spontaneous Speech 5.0 — Tashlhiyt (`shi`)**, `sps-corpus-5.0-2026-09-11`,
  **CC0**. 332 clips de 17 parlants (només 15 transcrits, per això no s'hi mesura res).

CC0 no exigeix atribució, però els citem igualment: sense la gent que va gravar i validar aquests
clips no sabríem què val res. **Sí que hi ha una condició que vam acceptar en baixar-los:** no
intentar esbrinar qui són els parlants («you agree to not determine the identity of speakers in
the dataset»). Els clips es queden fora del repositori.

### Tutlait v1 (Ma-OpenHub)

**CC BY 4.0.** 21 hores de tamazight parlat per 118 persones, amb l'accent etiquetat: **9.053
talls de l'Atles**, 3.015 del Souss, i restes del Rif i de Cabília. Cada tall porta
identificador de parlant i una **traducció a l'àrab estàndard — no una transcripció**: el que es
va dir en amazic no està escrit enlloc, i això és justament el que el fa útil i el que el limita.

La llicència demana atribució, i aquí queda:

> Chadi, Mohamed-Amine; Ait El Arbi, Ezzahra; Khayoub, Ismail; Fadili, Aymane; Ennhili, Yassine;
> Bouali, Jadjigua; Inhid, Hanane; Ameksa, Mohammed; Mousannif, Hajar (2026).
> *Tutlait v1: Tamazight Speech with Arabic Translations*. Hugging Face.
> https://huggingface.co/datasets/Ma-OpenHub/Tutlait-v1

Cada frase que n'entri a la biblioteca porta `license = CC BY 4.0`, `source_url` a aquesta
pàgina i, com a parlant, l'identificador del corpus («TutlAit · spk_010»), no un nom nostre: són
veus que el projecte no coneix i no ho faran veure.

### Awal Tamazight Dataset (CIEMEN / projecte Awal)

**CC BY 4.0.** Condició que posa el mateix conjunt de dades, textualment:

> No use without attribution to CIEMEN and the Awal project. Usage of Common Voice localization
> strings must comply with Mozilla Public License 2.0.

Per tant, aquí queda dit: dades del **projecte [Awal](https://awaldigital.org/)**, creades per
**[CIEMEN](https://www.ciemen.cat/)** amb finançament de l'Ajuntament de Barcelona i de la
Generalitat de Catalunya. Les cadenes de localització de Common Voice que inclou venen de
[Pontoon](https://pontoon.mozilla.org/zgh/common-voice/) i es regeixen per la **Mozilla Public
License 2.0** ([Pontoon Terms of Use](https://pontoon.mozilla.org/terms/)) — si mai es fan servir,
és sota aquella llicència, no sota la del conjunt.

Citacions que el conjunt demana si se'n fan servir les dades:

> *Awal – Community-Powered Language Technology for Tamazight.*
> Alp Öktem, Farida Boudichat.
> TICAM'25, Rabat, Morocco, December 2025. https://arxiv.org/abs/2510.27407

> *Correcting the Tamazight Portions of FLORES+ and OLDI Seed Datasets.*
> Alp Oktem, Mohamed Aymane Farhi, Brahim Essaidi, Naceur Jabouja, Farida Boudichat.
> Proceedings of the Tenth Conference on Machine Translation (WMT 2025) – OLDI shared task,
> Suzhou, China, November 2025. https://aclanthology.org/2025.wmt-1.82/

**Estat actual: baixat i mirat, encara no fem servir res.** És tot text (contribucions de la
comunitat, proverbis català–amazic, transliteracions de Tatoeba, localitzacions, traduccions de
documents), el mateix contingut que `collectivat/amazic` a HuggingFace. El projecte Awal sí que
recull veu — el seu article parla de «6,421 translation pairs and 3 hours of speech data» — però
aquelles gravacions **no són** dins del conjunt publicat. Si algun dia n'entra res a l'app, l'avís
de dalt ja hi és i s'ha de poder llegir també dins de l'app.

## 5b. Dos vídeos de l'alfabet — PERMÍS DEMANAT, ENCARA NO CONCEDIT

Per al capítol dels sons hem estudiat dos vídeos públics de YouTube. **Cap dels dos no és
a l'app**: ni el so, ni les imatges, ni cap retall. Són material amb tots els drets reservats
(llicència estàndard de YouTube), i fins que qui els va fer no digui que sí, aquí només
hi ha la nota i les còpies de treball, fora del repositori.

| | |
|---|---|
| **«Apprends le Tamaziɣt berbère, leçon N°1 — L'alphabet gréco-latin et tifinaɣ avec les illustrations»** | Brahim Mansoub (muntatge: Mohamed Elaamrani) · [youtube.com/watch?v=MZJVoHUGljE](https://www.youtube.com/watch?v=MZJVoHUGljE) · 18-06-2020 · 11 min |
| Què n'hem tret | El vocabulari il·lustrat: una o dues paraules per lletra amb el seu significat en francès (`aɣrum` pa, `afus` mà, `tasa` fetge, `udem` cara, `adrar` muntanya…). |
| **«ⵉⵙⴽⴽⵉⵍⵏ ⵏⵜⵎⴰⵣⵉⵖⵜ — Amazigh alphabet»** | canal *Atlas* · [youtube.com/watch?v=ASkEo4Y9IEI](https://www.youtube.com/watch?v=ASkEo4Y9IEI) · 03-03-2018 · 1 min 29 |
| Què n'hem tret | La veu de les 33 lletres, una per una: 33 talls alineats amb la lletra que es veia a la pantalla en dir-la (`ⴰ` Ya, `ⴱ` Yab, `ⴳⵯ` Yagʷ…). |

**El que falta fer, per ordre:**

1. Escriure a tots dos canals i demanar permís per fer servir, a una app gratuïta per aprendre
   la llengua, (a) el vocabulari il·lustrat i (b) els 33 talls de veu, amb el seu nom a sota.
2. Mentre no contestin: el capítol dels sons pot fer servir les **paraules** (una paraula i el
   seu significat no són seus: són de la llengua) però cap **imatge** i cap **so** d'ells.
3. Si diuen que sí: pujar els talls amb `license` i `source_url`, i el nom del canal visible al
   costat del botó de so, com qualsevol altra font.
4. Si diuen que no, o no contesten: gravar les 33 lletres amb les nostres veus (Halima, Driss)
   i esborrar les còpies de treball.

## 6. Eines i serveis

**Google Gemini** escriu els esborranys de lliçó i dibuixa les il·lustracions de les targetes (cap
text de parlant no en surt mai: les seves propostes van a `*_suggested`) · **Cloudinary** guarda el
so, les imatges i el vídeo · **HuggingFace Spaces** fa anar el transcriptor i l'alineador ·
**Brevo** envia els correus de recuperació de compte · **Render** i **Vercel** allotgen el
servidor i el web.

---

## Què hem de fer, en una llista

1. Qualsevol font nova de tercers: apuntar-la aquí amb autor i llicència **abans** de fer-la
   servir.
2. CC BY i CC BY-NC: dir el nom de qui ho ha fet i la llicència allà on es vegi el resultat.
3. L'app no té ús comercial: per això el material CC BY-NC hi pot ser.
4. Les dades d'Awal no es fan servir sense nomenar CIEMEN i el projecte Awal.
5. Dels parlants de Common Voice no se'n busca la identitat.
6. Res de material de tercers (PDF, diccionaris, clips de corpus) es committeja al repositori.
7. El que un parlant nostre ha dit és seu: no s'hi passa cap màquina per sobre.

> **Això també es llegeix des de l'app.** `GET /credits` serveix aquest mateix fitxer i la pantalla
> «Crèdits i fonts» el pinta — hi ha enllaç al peu del perfil i a la pàgina de Gramàtica. Un sol
> fitxer, però, perquè una còpia dins de l'app s'acabaria allunyant d'aquesta.
