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
— Halima i Driss (Aït Mraw), i els reculls de Beni Mellal i Azilal. Cada drill porta qui parla
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

**Què ens obliga el «NC»:** mentre el curs i les glosses s'aguantin en aquestes dues fonts
d'IRCAM, **l'app no pot tenir ús comercial**. Si algun dia es vol cobrar per res, primer cal
treure-les o demanar permís.

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
3. CC BY-NC a dins vol dir **app sense ús comercial**.
4. Les dades d'Awal no es fan servir sense nomenar CIEMEN i el projecte Awal.
5. Dels parlants de Common Voice no se'n busca la identitat.
6. Res de material de tercers (PDF, diccionaris, clips de corpus) es committeja al repositori.
7. El que un parlant nostre ha dit és seu: no s'hi passa cap màquina per sobre.

> **Falta encara:** això és un fitxer del repositori, i qui fa servir l'app no el veu. Els crèdits
> s'han de poder llegir també a dins de l'app — issue oberta.
