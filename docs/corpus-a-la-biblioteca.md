# Tot el corpus a la biblioteca, amb la seva varietat

*Pla per a la decisió del 29 d'octubre de 2026: «incorporar tots els corpus disponibles a la
biblioteca de drills, entenent les variants dialectals i fent arqueologia dialectal i gramatical».
Res d'aquest document no s'ha executat a producció: és per aprovar.*

## El que hi ha, comptat

### Ja a la biblioteca (5.159 drills el 29/10)

| regió declarada | drills | d'on |
|---|---:|---|
| Beni Mellal | 2.314 | recull Anki, `private` |
| Aït Mraw (Azilal) + Ait Mraw | 1.366 | veus de la Halima i d'en Driss, Tamazight For All, canals |
| taixelhit (Mètode d'El Mountassir) | 348 | el CD, aparellat per màquina amb el llibre, a `/revisa` |
| Atles Central (corpus TutlAit) | 239 | TutlAit, amb parlant (`spk_006`, `spk_002`…) |
| Marroc (amazic estàndard) | 233 | IRCAM Tamawalt |
| Souss | 205 | — |
| (buit) | 454 | sense regió |

4.407 amb veu · 3.787 amb text amazic · 4.753 amb català.

### A la màquina i fora de la biblioteca

| font | mida | varietat | parlant | text | permís |
|---|---:|---|---|---|---|
| MTNRA | 1.801 clips, 86 min | Souss (taixelhit) | **no en diu** | llatí + tifinag + àrab | sí (en Pablo) |
| Common Voice zgh 27.0 | 1.474 validats, 80 min | **88 % es declaren taixelhit**, 47 Central Atlas | `client_id` (28; dues veus = 83 %) | tifinag | CC-0 |
| CD del Mètode | 348 talls (171 sense comprovar) | taixelhit (llibre) | el CD | llatí ric, del llibre | sí |
| Baba Ali | 643 trams amb àrab llegit | Central Atlas? | un parlant | àrab (Qwen), tifinag (NeMo) | sí |
| Tamazight For All | 766 línies, 686 mudes | Central Atlas | el canal | 654 lectures de màquina | sí |
| SPS shi 5.0 | 332 clips, 164 min | taixelhit espontani | 17 | **15 transcripcions** | CC |
| vídeo del lleó (extret) | 31 parells, 102 s | ? | ? | OCR de tifinag | sí |

### A HuggingFace, catalogat i NO baixat

| dataset | mida | llicència | què és |
|---|---:|---|---|
| `Tamazight-NLP/TOSD` | 587 MB | apache-2.0 | ASR zgh/ber |
| `TutlaytAI/tamazight_asr` | 853 MB | cc | ASR kab + zgh |
| `TutlaytAI/moroccan_amazigh_asr` | 38 MB | cc | ASR zgh |
| `SoufianeDahimi/Tamazight-ASR-Dataset-v2` | 9 GB | apache-2.0 | ASR amb àrab |
| `BounharAbdelaziz/Amazigh_ASR` | 193 MB | **gated** | cal acceptar condicions a HF |
| `Datasmartly/audios-tamazight` | 7 GB, 10.018 fitxers | **gated** | cal acceptar condicions a HF |
| `Tamazight-NLP/IRCAM-CORPUS`, `DGLAI`, Tawalt, Tatoeba | text | cc / other | vocabulari i gramàtica |

Els *gated* els ha d'acceptar en Pablo al seu compte de HF: no es pot fer des d'aquí.

## Les tres regles que no es toquen

1. **El text del parlant és sagrat.** Tot el que llegeix una màquina va a `text_tachelhit_suggested`
   i a `esborranys` amb la seva procedència; al camp d'or només hi escriu una persona des de
   `/revisa`.
2. **La varietat i la font van separades.** `region` diu la varietat; `source_channel` /
   `source_title` / `speaker` diuen d'on ve. L'auditoria del 29/10 va trobar que al corpus
   d'entrenament «varietat» i «font» eren la mateixa variable per a 3 de 5 zones: a la biblioteca
   no pot passar.
3. **El crèdit sí, el permís no.** A l'app hi va qui i quina obra; mai l'estat del permís.

## L'ordre d'entrada

**1. Common Voice zgh (1.474).** La font més neta: parlant conegut, varietat autodeclarada,
tifinag escrit per la persona que grava? No: el text és un *prompt* llegit, de manera que el
text és d'or però la veu llegeix, no parla. Entra com a drill amb veu, `text_tachelhit` (és el
prompt, escrit per una persona), `speaker = client_id`, `region` = la variant declarada o
«Common Voice zgh (sense variant)», `source_channel = Mozilla Common Voice`. **Sense significat
en català**: es queda buit o va a `text_catalan_suggested` per màquina, marcat.

**2. MTNRA (1.801).** Text d'or en tres escriptures (llatí, tifinag, àrab). `region = Souss
(MTNRA)`, `speaker` buit **i dit**: «parlant no identificat pel corpus». `text_arabic` tal qual.

**3. Les 474 parelles CV↔MTNRA.** El mateix text, dues veus de dos llocs. Entren lligades:
`variant_of` del drill del CV cap al del MTNRA, `variant_kind = "so"` (mateixa paraula, altra
pronúncia). És el primer corpus paral·lel de pronúncia entre varietats i ja existeix.

**4. Baba Ali (643).** Veu + àrab llegit pel Qwen a `text_arabic`? **No**: el Qwen és màquina.
Va a `text_arabic` només si una persona el confirma; mentrestant a `esborranys` amb
`model = Qwen2.5-VL`. Tifinag del NeMo a `text_tachelhit_suggested`. Pila `per-escriure`.

**5. Tamazight For All (686 mudes, 654 llegides).** Ja són drills; només hi falten els
`esborranys` amb procedència, com les 206 de la pila. Igual que es va fer el 29/10.

**6. El CD del Mètode (348).** Ja hi és, a la pila `casa-amb-el-llibre`. Les 171 posicionals
depenen dels 30 talls que escolta en Pablo: si més de tres són dolents, surten de la pila.

**7. Els datasets de HF.** Primer TOSD i TutlaytAI (llicència clara, mida raonable); el
SoufianeDahimi v2 (9 GB) quan hi hagi lloc; els *gated* quan en Pablo els accepti. Cadascun
entra amb el mateix patró que el MTNRA i **es cataloga abans d'entrar**: varietat, parlant,
escriptura, què hi ha de persona i què de màquina.

## L'arqueologia: com es lliga el que és el mateix

La biblioteca ja té `variant_of` i `variant_kind` («so» = mateixa paraula escrita diferent /
pronunciada diferent; «paraula» = una altra manera de dir-ho). El que cal fer, i es pot mesurar:

- **Mateix text plegat, fonts diferents** → `variant_kind = "so"`. Ara: 474 (CV↔MTNRA), 31
  (CD↔Souss de la biblioteca). Es troben amb el plegat de sempre a 26 lletres.
- **Mateix significat en català, text amazic diferent** → candidats a `"paraula"`. Ja hi ha la
  pila `dos-amazics` (259) que fa exactament aquesta pregunta.
- **El lèxic i la gramàtica per varietat**: a partir dels drills lligats, una taula
  *forma → varietat → font* per a cada paraula del glossari. Això és «en el futur» i surt sol
  quan les parelles estan lligades; no s'ha de construir abans.

## El que NO es fa

- Cap OCR ni ASR al camp d'or.
- Cap font sense `region` i sense `source_*`.
- Cap *gated* sense que en Pablo n'hagi acceptat les condicions.
- Cap text en català inventat: buit o `*_suggested`.

## Què cal d'en Pablo abans d'executar

1. Aprovar aquest ordre, o canviar-lo.
2. Acceptar a HF els dos datasets *gated*, si els vol.
3. Dir si el Common Voice ha d'entrar amb «veu que llegeix un prompt» marcat d'alguna manera a
   l'app (és diferent de «veu que parla»).
