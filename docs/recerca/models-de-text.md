# Quin model de text ens fa la feina: mesura del 16-11-2026

Pregunta d'en Pablo: Gemini és car i no en tenim; podem fer servir les claus dels models xinesos,
i com van en comparació? Resposta en dues parts: **què contesta de debò** amb les claus que tenim, i
**com ho fa** sobre una tasca nostra amb veritat.

## Què contesta (16-11, matí)

| via | estat | models |
|---|---|---|
| Gemini (clau de `backend/.env`) | **402, crèdit esgotat** des del 24-10 | — |
| DeepSeek directe (clau de `nomatrails-seo-pipeline/.env`) | **contesta**, saldo 22,62 $ | `deepseek-chat` (alias, no raona), `deepseek-flash` (raona), `deepseek-v4-pro` (raona) |
| DashScope / Model Studio d'Alibaba (clau vella) | llista 102 models però cada crida torna «account not in good standing» | Qwen3.8 (flash, max, 27b, 2.4t), DeepSeek per Alibaba |
| HuggingFace Inference Providers (els dos tokens) | 402: «Purchase pre-paid credits» | Qwen, GLM, Kimi, MiniMax, DeepSeek |

Conclusió pràctica: **avui només DeepSeek**. Per tenir Qwen cal un compte de Model Studio en regla
(en Pablo n'obre un de nou el 16-11 al migdia, amb fitxes gratuïtes per a comptes nous); GLM,
Kimi i MiniMax demanen crèdits a HuggingFace o un compte propi a cada casa.

## Com ho fan: traduir 60 frases de la biblioteca al català (`tools/lm/compara_models.py`)

La tasca: 30 frases en taixelhit (tifinag, `tamazight.drills`) i 30 en tamazight de Beni Mellal
(llatí, el recull de l'Anki), de 2 a 12 mots, llavor 1114. La veritat és el català de la fitxa.
Dues condicions: la frase sola, o la frase amb el que diuen el diccionari de l'IRCAM i les taules
de conjugació de les seves paraules (`lexicon.grounding_lines`; 50 de 60 frases en tenen alguna).
Temperatura 0. Mesura: chrF (n-grames de caràcters 1-6, β = 2) contra la veritat; latència mediana;
fitxes de raonament; cost a preu de llista en hora punta.

| model | fonts | chrF (60, buit = 0) | **buits** | chrF només contestades | chrF de `chat` sobre les mateixes | latència | cost de les 60 |
|---|---|---|---|---|---|---|---|
| `deepseek-chat` | sense | 0,303 | 0 | 0,303 | — | 1,4 s | 0,003 $ |
| `deepseek-chat` | amb | 0,347 | 0 | 0,347 | — | 1,4 s | 0,010 $ |
| `deepseek-flash` | sense | 0,359 | 12 | 0,449 | 0,305 | 12,7 s | 0,19 $ |
| `deepseek-flash` | amb | 0,390 | 11 | 0,478 | 0,346 | 13,7 s | 0,20 $ |
| `deepseek-v4-pro` | sense | 0,340 | 25 | 0,582 | 0,307 | 75,6 s | 0,90 $ |
| `deepseek-v4-pro` | amb | 0,375 | 22 | **0,592** | 0,375 | 87,4 s | 0,95 $ |

**Els buits no són del model, són del pressupost.** Comprovat tornant a demanar una de les frases
buides a `v4-pro`: `finish_reason = length`, 6.000 fitxes de raonament i cap resposta; el final
del raonament és el model rumiant sobre una paraula que no coneix («*ḍu* might mean *to return*
in that dialect? Let's search mental dictionary…»). Amb el sostre de 6.000 fitxes, `flash` es queda
sense resposta 1 cop de 5 i `v4-pro` 2 de 5, i les buides es cobren igual.

Mostra a ull (veritat → chat amb fonts → v4-pro amb fonts):

- «Doneu-me la meva part.» → «Dona'm la meva part.» → «Doneu-me la meva part.»
- «Em fan mal els ulls.» → «Els meus ulls no em van creure.» → «Els meus ulls em fan mal.»
- «Continua parlant.» → «M'hi dedico encara només.» → «Encara estic ocupat.»
- «Allà hi ha l'home a qui vaig donar els diners.» → «L'home aquell de qui es va vanar els diners.» → «Heus aquí l'home a qui vaig donar els diners.»
- «Ho vam donar als nens» → «passar la nit» → (buit)

## El que se'n treu

1. **Cap dels tres sap amazic del tot**, però els que raonen en saben força més quan contesten:
   sobre les mateixes frases, `v4-pro` 0,59 i `flash` 0,48 contra `chat` 0,35-0,38. `chat` sol
   (0,30) és una de cada tres frases bé i la resta aproximacions o invents (`ihla idnnx` «és bo
   amb nosaltres» → «passar la nit»): el que diu `SERVEIS_IA.md` des del 24-10.
2. **Les fonts ajuden a tots tres**: +0,03 a +0,05 de chrF, i +0,08 a +0,10 sobre el taixelhit,
   que és on el diccionari de l'IRCAM casa més. Lèxic amb procedència (`LEXIC_VALIDAT`, el
   creuament) i model que raona van junts: l'un sense l'altre es queda curt.
3. **Com fer-los servir.** Per a lots amb fonts, **`flash` amb un sostre de raonament més alt o
   amb `chat` de recanvi** quan torna buit (0,003 $ per frase, 13 s). **`v4-pro`** només per al
   que mana (auditar una traducció del Mètode, jutjar un creuament): és el millor quan contesta,
   però costa deu vegades més, triga de 75 a 90 s i necessita pressupost de raonament gran.
   **`chat`** per a lots grans on la precisió no mana (resums en dàrija, classificar).
   `deepseek_client.py` ja té el sostre dels raonadors a 6.000 (`THINKER_FLOOR`): per a l'amazic
   cal pujar-lo o caure a `chat` quan el contingut és buit.
4. **Gemini no es pot comparar** sobre aquesta tasca: no tenim crèdit i no hi ha cap mesura
   anterior de Gemini traduint amazic amb fonts. El que consta de Gemini als registres és
   d'àudio (transcriure clips curts, CER 0,19 el 17-10, i resumir una faula sentint-la), i això
   avui ho fa millor el nostre Space.

Resultats sencers: `Veus-tachelhit\_escoltats\models\compara_resultat.json`.

## Els Qwen, amb el compte nou de Model Studio (16-11, migdia; `tools/lm/compara_models_qwen.py`)

En Pablo obre un compte nou d'Alibaba Cloud (internacional, Singapur) i activa Model Studio: **70
models amb un milió de fitxes gratuïtes cada un, 91 dies**. Dues trampes trobades pel camí: la clau
nova (`sk-ws-…`) només funciona pel **punt d'accés de l'espai de treball** que surt al diàleg de la
clau (`DASHSCOPE_BASE_URL` a `backend/.env`), no pel genèric `dashscope-intl`; i la màquina d'en
Pablo té una **variable de sistema** `DASHSCOPE_API_KEY` del compte vell que `load_dotenv` no
sobreescriu si no se li diu (`override=True`). Les mateixes 60 frases, mateixes fonts, mateixa
regla; als Qwen se'ls apaga el raonament (`enable_thinking=False`) llevat d'una fila:

| model | raona | fonts | buits | chrF (60) | `v4-pro` sobre les mateixes | `flash` | `chat` | latència | fitxes de sortida (60) |
|---|---|---|---|---|---|---|---|---|---|
| `qwen4-max` | no | sense | 0 | 0,409 | 0,582 | 0,449 | 0,303 | 3,6 s | 3.298 |
| `qwen4-max` | no | amb | 0 | 0,443 | 0,592 | 0,478 | 0,347 | 3,6 s | 781 |
| **`qwen3.8-max`** | no | sense | 0 | **0,471** | 0,582 | 0,449 | 0,303 | **1,9 s** | 632 |
| **`qwen3.8-max`** | no | amb | 0 | **0,473** | 0,592 | 0,478 | 0,347 | 2,0 s | 693 |
| `qwen3.8-flash` | no | sense | 0 | 0,286 | | | | 1,7 s | 686 |
| `qwen3.8-flash` | no | amb | 0 | 0,339 | | | | 1,6 s | 615 |
| `qwen3.8-27b` | no | sense | 0 | 0,161 | | | | 1,7 s | 672 |
| `qwen3.8-27b` | no | amb | 0 | 0,240 | | | | 1,8 s | 940 |
| `qwen4-max` | **sí** | sense | 1 | **0,496** (0,487 amb el buit) | 0,582 | 0,449 | 0,306 | 23,7 s | 102.123 |
| `qwen4-max` | sí | amb | 1 | 0,481 | 0,592 | 0,481 | 0,344 | 12,2 s | 65.089 |
| `deepseek-v4.1-flash` (per Alibaba) | sí | sense | 11 | 0,449 contestades | 0,617 | 0,467 | 0,321 | 12,9 s | 191.946 |
| `deepseek-v4.1-flash` (per Alibaba) | sí | amb | 6 | 0,461 contestades | 0,603 | 0,484 | 0,349 | 14,4 s | 178.559 |

(Les columnes `v4-pro`, `flash` i `chat` són els DeepSeek d'abans sobre les mateixes frases
contestades, perquè es pugui comparar fila a fila.)

**El que se'n treu.**

1. **`qwen3.8-max` sense raonar és el segon auditor que buscàvem**: chrF 0,47, cap resposta buida,
   2 segons per frase, i de franc fins al milió de fitxes. Fa el mateix que `deepseek-flash` quan
   aquest contesta (0,45-0,48) sense el problema dels buits, i millor que `deepseek-chat` (0,30-0,35).
2. **El millor traductor segueix sent `deepseek-v4-pro` quan contesta** (0,58-0,62 sobre les mateixes
   frases), i el segon `qwen4-max` raonant (0,50, 1 buit de 60, 12-24 s). Per al que mana, un o
   l'altre; per als lots, `qwen3.8-max` i `deepseek-flash`.
3. **Les fonts del diccionari ajuden els petits i gairebé gens els grans**: `qwen3.8-flash` +0,05,
   `qwen3.8-27b` +0,08, `qwen4-max` sense raonar +0,03; `qwen3.8-max` +0,002 i `qwen4-max` raonant
   −0,015. Els grans ja saben el que diu el diccionari de l'IRCAM; el que els falta no hi és.
4. `qwen3.8-27b` (0,16-0,24) i `qwen3.8-flash` (0,29-0,34) no serveixen per a l'amazic: val només per
   a feines de català o d'àrab.
5. **Independència**: Qwen i DeepSeek són cases diferents amb dades diferents; quan coincideixen en
   una traducció d'amazic, la coincidència val. És la regla de «dos auditors i només l'acord» amb
   dos auditors de debò per primera vegada des que Gemini va caure.

El que ve: `backend/qwen_client.py` amb la mateixa forma que `deepseek_client` i Qwen com a segon a
`serveis.py`; provar `qwen3.8-omni` sentint l'àudio en dàrija de TFA; 10 dibuixos de targeta amb
`qwen-image-3.0`. Resultats sencers: `Veus-tachelhit\_escoltats\models\compara_qwen_resultat.json`.

## `qwen-image-3.0` per a les targetes (16-11, tarda)

Deu targetes que ja tenen il·lustració a producció (#199 «Aigua calenta», #458 «Flor», #228 «Afilat»,
#138 «Barbero», #230 «tot el temps», #175 «la entens?», #160 «De res», #177 «Esperam», #205 «Hort»,
#235 «Jo he vist»), redibuixades amb `qwen-image-3.0` pel punt d'accés natiu de Model Studio
(`/api/v1/services/aigc/multimodal-generation/generation`; el compatible d'OpenAI no el coneix), amb
l'estil i el pas d'escena d'`illustrate.py` (l'escena la posa `qwen3.8-max`). Quatre passades, 8-11 s
per dibuix, quota gratuïta. Fulls de contacte i registre a `Veus-tachelhit\_escoltats\models\imatges\`.

| passada | prompt | dibuixos amb lletres |
|---|---|---|
| 1 | el d'`illustrate.py` tal qual (estil + «The sentence: «…»») | **10 de 10**: escriu la frase catalana al dibuix, en lletres grans |
| 2 | estil + només l'escena en anglès, sense la frase | 3 de 10 (lletres inventades) |
| 3 | com la 2 + `negative_prompt` amb «text, letters, words…» | 5 de 10 (pitjor) |
| 4 | com la 2 sense la frase «Absolutely no text…» de l'estil | 9 de 10 |

El que se'n treu: és un model de cartell, li agrada escriure. (1) Mai la frase al prompt: la pinta.
(2) La prohibició de text de l'estil ajuda (de 9 a 3) i el `negative_prompt` no. (3) Amb la
configuració bona (passada 2) en surten netes 7 de 10: per fer-lo servir cal un comprovador de text
(`qwen3-vl-plus`: «hi ha lletres?») i tornar a dibuixar les que en portin; amb 2.000 imatges gratuïtes
hi ha marge. (4) Les escenes són més riques i més marroquines que les actuals de FLUX (gent, cases
d'adob, oliveres), però posa te de menta i tagín a TOTS els dibuixos perquè l'estil els anomena:
caldria dir-los «quan l'escena ho demani» més fort o treure'ls. (5) Encerta el significat a les
concretes (afilat, barber, hort, flor, esperar) i falla a les abstractes igual que FLUX («tot el
temps» → quatre vinyetes; «Jo he vist» → algú que s'assenyala els ulls).

## Dos auditors de debò sobre les 1.643 traduccions pendents (16-11, tarda; `tools/lm/auditors_traduccions/`)

Les frases d'MTNRA (959) i Common Voice (684) que el 31-10 van quedar amb l'etiqueta
`traduit-per-maquina`, passades per `qwen3.8-max` i `deepseek-chat` com a auditors independents
(mateix encàrrec, diccionari i conjugació de cada paraula, la llista d'errors sistemàtics de la màquina,
temperatura 0; `TRIA: <text>` / `FORA` / `NO-HO-SE`). 3.286 crides, 17 minuts, 5,3 M fitxes d'entrada
(Qwen gratis; DeepSeek ≈ 0,75 $). Resum sencer i veredictes a
`Veus-tachelhit\_escoltats\traduccions\auditors\resum.md`.

| auditor | TRIA | FORA | NO-HO-SE |
|---|---|---|---|
| `qwen3.8-max` | 659 | 188 | 796 |
| `deepseek-chat` | 351 | 122 | 1.170 |

Acord (la regla del 31-10): **186 confirmades** (116 amb el text de la màquina tal qual, 70 amb el
mateix retoc pels dos: «bossa» → «tabaquera» per *aqmqum*, «veloç» → «intel·ligent» per *unẓiẓ*,
«conill» → «mufló» per *udad*), **31 descartades** pels dos (`tam` → «Ocho», `agri` → «Granota»,
*ubrray ixcnn* «ocell molt bonic» que és «ferida dolenta»), 108 amb tots dos TRIA però text
diferent (66 amb chrF ≥ 0,7: mateix sentit, altres paraules; no entren) i 1.318 sense acord, la
majoria perquè el DeepSeek diu NO-HO-SE (71 % de les seves respostes).

El que se'n treu: (1) l'acord és del **13 %**, contra el ~50 % dels dos auditors Claude del 31-10:
els models de màquina són molt més prudents amb el diccionari a la mà, i el DeepSeek sobretot. Val com a
tercer filtre barat, no com a substitut. (2) Els 70 retocs coincidents són tots de la llista d'errors
sistemàtics: el que els dos saben és el que se'ls ha dit. (3) Els 108 «TRIA però diferent» demanarien
una regla de sentit (no de text) o un tercer que triï: feina per a una altra passada. (4) Cap escriptura:
`canvis.json` (217) s'aplica només amb `aplica.py --escriu` a mà del propietari.

## Traductors web amb «tamazight» (16-11, tarda; peó `mt-web`)

Nou serveis mirats sobre les mateixes 60 frases. Només dos tenen cap llengua amaziga: **Google
Translate** («Tamazight» `ber-Latn`, «Tamazight (Tifinagh)» `ber`, des del juny de 2024; API pública
`translate.googleapis.com/translate_a/single?client=gtx` sense clau) i **Glosbe Translate** (motor
NLLB-200, `tzm`, només web). Microsoft/Bing, DeepL, Yandex, Lingvanex i Apertium: cap. L'IRCAM no té
traductor automàtic (té el DGLAi i les eines TALAM: corrector, conjugador, transliterador, i un OCR
amazic públic a `tal.ircam.ma/ocr/`, només per navegador); amazic.cat és diccionari.

| servei | entrada | chrF (60) | shi | Beni Mellal | buits |
|---|---|---|---|---|---|
| Google Translate | tifinag `ber` | **0,428** | 0,401 | 0,455 | 0 |
| Google Translate | llatí `ber-Latn` | 0,402 | 0,415 | 0,390 | 0 |
| Google tifinag → en → ca (`deepseek-chat`) | tifinag | 0,427 | | | 0 |
| Glosbe (NLLB, `tzm`) | tifinag | 0,193 (0,297 contestades) | | | 21 (HTTP 500) |
| *ref.* `deepseek-chat` / `qwen3.8-max` / `deepseek-v4-pro` | | 0,303 / 0,471 / 0,58 quan contesta | | | |

El que se'n treu: (1) Google és un esborrany gratuït i instantani que sempre contesta, entre DeepSeek
Chat i Qwen Max; clava les curtes freqüents («No parlo àrab», «On és la dona?») i quan no sap una
paraula la deixa en llatí o s'inventa un nom (Jesús, Mubarak). Val com a veu independent barata al
costat dels auditors, no com a font. (2) Envieu-li tifinag: el llatí de l'Anki (γ grega, guions) el
bloqueja. (3) Glosbe/NLLB no val. Informe i crus: `Veus-tachelhit\_escoltats\models\web\`.

## El tercer auditor, i el parell sobre Baba Ali (16-11, vespre)

**Tercer auditor** (`qwen4-max` raonant, `audita_tercer.py`), només sobre les frases d'MTNRA i Common
Voice que els dos primers no van tancar (649: un TRIA o un FORA contra un NO-HO-SE, un TRIA contra un
FORA, o dos TRIA diferents), amb la regla «dos de tres amb el mateix text»: 290 TRIA, 48 FORA, 137
NO-HO-SE sobre les primeres 475; 17 s per frase. Resultat final de les 1.643: **341 confirmades**
(186 pel parell + 155 pel tercer: 80 amb el text de la màquina, 75 retocades igual) i **135
descartades** (31 pel parell + 104 pel tercer), 1.167 queden com a proposta. A ull, els descartats
són els «[?]» de la màquina i les frases sense sentit («e, beb, geg» → «On, on, on»); els retocs
del tercer casen amb el diccionari (*taẓuṛi* art, no història; *addur* honor, no regal). Acord
total: 29 % (abans del tercer, 13 %).

**Baba Ali** (`audita_arab.py`, 3.621 rèpliques amb subtítol àrab d'OCR i català de màquina, sense
text amazic): aquí els dos models sí que saben la llengua d'origen. Qwen TRIA 3.609 / FORA 2 /
NO-HO-SE 8; DeepSeek 3.517 / 59 / 45. Parell: **2.165 confirmades** (1.700 iguals que la màquina,
465 amb el mateix retoc: «bresca» → «mel», «clar com l'aigua» → «clar i evident»), 109 sense acord
i 1.347 on tots dos diuen TRIA però retoquen diferent (el tercer les està mirant). La taxa de FORA
tan baixa diu també que l'àrab de l'OCR és bo. Costos: Qwen gratis; DeepSeek ≈ 0,45 $.

**Baba Ali, amb el tercer** (16-11, nit): el tercer auditor sobre les 1.769 obertes (TRIA diferents,
TRIA/NO-HO-SE, TRIA/FORA) va tancar-ne 855: total **3.018 confirmades** de 3.621 (1.700 iguals que la
màquina pel parell + 568 pel tercer; 465 + 285 amb el mateix retoc), 2 descartades, 578 amb tres TRIA
tots diferents (mateix sentit, tres redaccions: no entren) i 23 sense acord. El 83 % de les rèpliques
de Baba Ali queden amb el català confirmat per dos auditors independents contra l'àrab.

## Traductors dedicats a l'amazic (16-11, nit; peó `mt-hf-github`, informe a `Veus-tachelhit\_escoltats\models\hf\`)

Cercats 629 models i ~300 datasets d'amazic a HuggingFace, més GitHub, OPUS, Tatoeba i FLORES+. De
traducció executable només hi ha NLLB (base i els afinats de Tamazight-NLP i ayymen), MADLAD-400 i
Google Translate; cap traductor de l'IRCAM ni universitari és públic. Les mateixes 60 frases:

| sistema | entrada | chrF | shi | Beni Mellal |
|---|---|---|---|---|
| **NLLB afinat de Tamazight-NLP (el del nostre Space), `tzm_Tfng` → anglès, + `deepseek-chat` en→ca** | tifinag | **0,521** | 0,548 | 0,494 |
| ídem amb `taq_Tfng` → anglès + DeepSeek | tifinag | 0,497 | 0,536 | 0,457 |
| ídem `tzm_Tfng` → català directe | tifinag | 0,447 | 0,493 | 0,402 |
| ídem `taq_Tfng` → català directe (**= com estava el backend**) | tifinag | 0,424 | 0,444 | 0,405 |
| Google Translate `ber` → ca | tifinag | 0,428 | 0,401 | 0,455 |
| NLLB-200 600M base `tzm_Tfng` → ca | tifinag | 0,330 | | |
| ayymen només-SEED → en + DeepSeek | tifinag | 0,286 | | |
| MADLAD-400 3B | tifinag / llatí | 0,179 / 0,099 | | |
| *ref.* `qwen3.8-max` / `deepseek-chat` | | 0,471 / 0,303 | | |

Contaminació comprovada: només 4 de les 60 frases són al Tatoeba de Tamazight-NLP (cap amb anglès):
l'avantatge és real. El que fa bo l'afinat són les dades (Tatoeba, diccionaris, Anki, Weblate): el
model «només SEED» del mateix autor fa 0,286.

**Endollat al backend el mateix vespre** (`tradueix` → `_amazic_a_catala`): l'amazic → català passa
ara per l'Space amb la fitxa `tzm_Tfng` demanant anglès, i DeepSeek (o Qwen) passa l'anglès al
català; si cap dels dos contesta, català directe amb `tzm_Tfng`. Comprovat en viu sobre 10 de les 60
frases pel camí sencer del backend: chrF 0,524, ~3 s per frase (`tests/test_pont_angles.py`). Segueix
sent un esborrany per a `*_suggested`, no una traducció per publicar; el pas següent és afinar aquest
NLLB amb les nostres parelles confirmades (1.456 + 341 d'MTNRA/CV) i mesurar-ho a cegues aquí mateix.
Corpus per afinar: Tatoeba shi 836 / zgh 159, OPUS shi-en (Bíblia 15.856, Tatoeba 2.171), FLORES+
(`zgh_Tfng`, `taq_*`; no hi ha `tzm_Tfng`), `Tamazight-NLP/English-Tashlhit-Dictionary` (50.204
traduccions, llicència «other»: mirar-la abans).

## El Gemini, amb 5 € de crèdit (16-11, nit; `Veus-tachelhit\_escoltats\models\compara_gemini.py`)

En Pablo hi posa 5 € i es mesura amb compte (raonament al mínim, sostre de fitxes; 150.000 fitxes en
total, uns cèntims). Les mateixes 60 frases, chrF contra el parlant:

| model | fonts del diccionari | chrF | shi | Beni Mellal | buits | temps |
|---|---|---|---|---|---|---|
| `gemini-3.1-pro-preview` (raonament baix) | amb | 0,609 (*cota inferior*: de vegades contesta amb notes i la primera línia no és la traducció) | 0,580 | 0,637 | 0 | 5,6 s |
| **`gemini-3.8-flash`** (raonament mínim) | amb | **0,602** | 0,531 | 0,673 | 0 | 6,0 s |
| `gemini-3.8-flash` | sense | 0,594 | 0,536 | 0,652 | 0 | 5,9 s |
| `gemini-2.5-flash` (sense raonar) | amb | 0,571 | 0,574 | 0,569 | 0 | 1,2 s |
| *ref.* NLLB afinat + pont per l'anglès / `qwen3.8-max` / Google `ber` | | 0,521 / 0,471 / 0,428 | | | | |

El que se'n treu: (1) **el Gemini és el millor traductor d'amazic que tenim**, 0,57-0,61 sense cap buit,
per sobre del pont (0,52) i de tots els altres; el diccionari ja no li aporta res (+0,008). (2) Les
versions 3.8 guanyen a Beni Mellal (0,65-0,67) i la 2.5 al taixelhit (0,57), curiós i a mirar.
(3) Segueix sent un esborrany: «tres fills» → «tres mosques», «cap d'any» → «Eid»; a `*_suggested` i
prou. (4) Cost: menys d'un cèntim per frase; amb 5 € hi ha uns 20.000 esborranys d'amazic.

**Endollat al backend** (`_esborrany_amb_gemini`, dins `_amazic_a_catala`): el Gemini primer (el model
de `GEMINI_MODEL`, `gemini-2.5-flash` sense raonar per defecte), el pont NLLB → anglès → DeepSeek/Qwen
si no hi és o no contesta, català directe al final. Comprovat en viu pel camí sencer del backend sobre
les 10 frases de la prova anterior: **chrF 0,705** (el pont: 0,524), 1 s per frase; 616 proves verdes.
El Gemini no s'usa per a res massiu (l'àrab de TutlAit el fa Qwen de franc): es guarda per a l'amazic,
que és on és únic, i el comptador d'`ai_budget` hi posa sostre.

## H-MT1: el NLLB afinat amb les parelles pròpies (16-11, nit; peó `nllb-afina`, nucli `nllb-afina-propi`)

4.910 parelles del catàleg amb amazic i català confirmats (fora: català de màquina no confirmat
1.807, Auto Capture 121, correccions 91, curs sintètic 81, irlandès 8, duplicats 332); 200 de test-dins
(llavor 1114), 4.609 de train net. **Fuita trobada:** excloure les 60 de la mostra per `id` no bastava,
el catàleg repeteix frases sota ids diferents (12 de les 60 i 8 de les 200 eren a train); la v1 es va
descartar i la v2 treu la fuita per text normalitzat. Fonts del train: Beni Mellal 2.158, MTNRA 619,
Common Voice 499, Mètode CD 335, IRCAM 218, Driss 205, Mètode llibre 175, Aït Mraw 96, Halima 72…
3.221 files passades del llatí al tifinag amb `to_forms`. Ritme 3e-5, 3 èpoques (1e-5 queda per sota).

| camí | grup | abans | després | Δ | IC 95 % |
|---|---|---|---|---|---|
| **català directe** (`tzm_Tfng` → `cat_Latn`) | 60 frases | 0,454 | **0,571** | **+0,117** | [+0,071, +0,169] |
| català directe | shi (30) | 0,494 | 0,554 | +0,059 | [+0,010, +0,111] |
| català directe | Beni Mellal (30) | 0,414 | 0,589 | +0,175 | [+0,097, +0,264] |
| català directe | test-dins (200) | 0,278 | 0,425 | +0,147 | [+0,118, +0,178] |
| pont (→ anglès + DeepSeek) | 60 frases | 0,527 | 0,554 | +0,027 | [−0,009, +0,067] |

El que se'n treu: (1) **viva en català directe**: el model afinat (0,571) passa el pont del matí (0,521)
i iguala `gemini-2.5-flash` sense raonar; és nostre, gratuït i corre en CPU. El pont i DeepSeek deixen
de caldre com a segona opció. (2) El pont no es mou perquè no s'ha entrenat cap a l'anglès. (3) A ull:
català més net i les fórmules de l'Anki apreses; no arregla la persona del verb (*ɣrwn* «teniu» →
«tinc»); empitjora en mots sols de l'IRCAM. (4) Després: més èpoques o 5e-5 (la pèrdua de dev encara
baixava), treure el vocabulari del train, i el 1.3B amb LoRA. Pesos afinats (fp16, 1,2 GB) a la sortida
del nucli; informe i sortides a `Veus-tachelhit\_escoltats\models\nllb_afina\`. Amb la declaració de
permisos del 16-11 es pot desplegar al Space propi com a caiguda darrere el Gemini.

**Desplegat** (16-11, 22:00; peó `nllb-desplega`): el model afinat d'H-MT1, convertit a CTranslate2
int8 (663 MB; en local 44 de 60 sortides idèntiques al nucli, chrF 0,569 contra 0,571 en fp16), és al
repositori privat `josepabloucr/nllb-600m-tamazight-catala-ct2-int8` (README en català, llicència
CC BY-NC 4.0 del NLLB) i serveix al Space `josepabloucr/Finetuned-Quantized-NLLB` (commit `ae916f0`;
només ha canviat `MODEL_ID` i el token; mateixa API i mateixos noms de llengua). Mesura en viu sobre
les 60, «Standard Moroccan Tamazight» → «Catalan»: **0,448 → 0,568** (shi 0,493 → 0,557, Beni Mellal
0,403 → 0,579), cap buit. El camí cap a l'anglès segueix viu. Per tornar enrere: `actualitza_space.py
--enrere` (còpia de l'`app.py` anterior a `Veus-tachelhit\_escoltats\models\nllb_afina\desplegament\`).
Perquè producció el faci servir cal que `HUGGINGFACE_TRANSLATION_SPACE_URL` a Render apunti a aquest
Space (ara apunta al de Tamazight-NLP, que és el model base).

**H-MT1 v3** (16-11, nit, segona tanda; peó `nllb-afina`, nucli `nllb-afina-propi` v3, guions
`tools/lm/kaggle/prepara_parelles_v3.py`, `nllb_afina_propi_v3.py`, `compara_v3_v2.py`). Tres canvis
respecte de la v2, amb el **mateix test-dins de 200** i les mateixes 60: (1) fora del train el vocabulari
sol (una paraula amaziga o catalana: 822; glosses múltiples amb «/» o «;»: 442; tot l'IRCAM tamawalt:
218); (2) dins les **302 parelles MTNRA/Common Voice confirmades pels dos auditors de màquina** del
16-11 (de les 341 de `canvis.json`: 35 eren vocabulari i 4 són a la mostra), amb el català dels
auditors; (3) ritme 5e-5, 5 èpoques i es queda el checkpoint amb millor pèrdua de dev (la 4a: 2,12 →
1,91 → 1,85 → **1,819** → 1,819). Fuita per text normalitzat treta abans de llançar (62 files; 0 fuites
comprovades). Train: 3.399 parelles (Beni Mellal 1.368, MTNRA 674, Common Voice 575, Mètode CD 303,
Driss 134…), 1.293 en tifinag d'origen i 2.106 passades del llatí. El nucli converteix el millor
checkpoint a CTranslate2 int8 i el mesura també.

| camí | grup | abans | v2 | **v3** | Δ v2 → v3 | IC 95 % | Δ abans → v3 | IC 95 % |
|---|---|---|---|---|---|---|---|---|
| **català directe** | **60 frases** | 0,454 | 0,571 | **0,618** | **+0,047** | [+0,018, +0,080] | +0,164 | [+0,113, +0,219] |
| català directe | shi (30) | 0,494 | 0,554 | 0,587 | +0,033 | [+0,003, +0,064] | +0,092 | [+0,032, +0,150] |
| català directe | Beni Mellal (30) | 0,414 | 0,589 | 0,649 | +0,061 | [+0,005, +0,125] | +0,236 | [+0,159, +0,318] |
| **català directe** | **test-dins (200)** | 0,278 | 0,425 | **0,453** | **+0,028** | [+0,009, +0,048] | +0,175 | [+0,142, +0,210] |
| pont (→ anglès + DeepSeek) | 60 frases | 0,527 | 0,554 | 0,587 | +0,034 | [−0,005, +0,075] | +0,061 | [+0,015, +0,110] |
| pont | test-dins (200) | 0,307 | 0,392 | 0,409 | +0,017 | [−0,002, +0,036] | +0,102 | [+0,076, +0,129] |
| català directe, **ct2 int8** | 60 frases / test-dins | | | 0,623 / 0,454 | int8 − fp16: +0,005 [−0,007, +0,019] / +0,000 [−0,008, +0,009] | | | |

El que se'n treu: (1) **la v3 guanya la v2 amb l'IC fora del zero** en català directe, sobre les 60
(+0,047) i sobre les 200 (+0,028), i a tots dos grups; sobre el pont la diferència no arriba a
significativa. (2) Per font al test-dins (abans → v2 → v3): Beni Mellal 0,16 → 0,30 → 0,32, MTNRA
0,52 → 0,70 → 0,73, Mètode CD 0,28 → 0,58 → 0,73, Driss 0,11 → 0,24 → 0,32; Common Voice i el Mètode
del llibre baixen una mica (0,63 → 0,62; 0,51 → 0,48). (3) La 5a època encara puja les 60 (0,626)
però no el test-dins (0,449 contra 0,453): la pèrdua de dev tria bé. (4) La conversió a int8 no
perd res (Δ dins de ±0,01). (5) A ull: guanya en fórmules i preguntes («Per què has dit així?», «Que
Déu et porti la salut») i perd en algun pronom («Vosaltres sou russos» → «Vosaltres i els russos»).
L'int8 és a punt a `Veus-tachelhit\_escoltats\models\nllb_afina\v3\ct2_int8\` (i els pesos fp16 a
`v3\model_afinat\`); comprovat en local a la CPU: chrF 0,629 sobre les 60, 43 de 60 sortides idèntiques
a les del nucli, 0,7 s per frase. **No s'ha tocat el Space**: el que serveix segueix sent la v2.

**Desplegada la v3** (17-11, 00:30; peó `nllb-desplega`): els pesos int8 de la v3 són a `main` del mateix
repositori privat `josepabloucr/nllb-600m-tamazight-catala-ct2-int8` (revisió `3dc54fb7`; la v2 queda
referenciable a la revisió `2d39082f`; el commit `f116a4a6` d'entremig només va canviar el README, els
pesos hi són encara de la v2). L'`app.py` del Space no fixa cap revisió, de manera que no s'ha tocat:
un reinici de fàbrica (5 min) li ha fet baixar la v3. Mesura en viu sobre les 60, «Standard Moroccan
Tamazight» → «Catalan», mateix guió que la v2: **0,568 → 0,623** (shi 0,557 → 0,595, Beni Mellal
0,579 → 0,650; amb els paràmetres que envia el backend, 0,621), cap buit, cap sortida en blanc; el camí
cap a l'anglès segueix viu («I do not speak Arabic.»). Per tornar a la v2:
`Veus-tachelhit\_escoltats\models\nllb_afina\desplegament\torna_a_v2.py` (torna a posar a `main` els
fitxers de la revisió v2 com a commit nou i reinicia el Space de fàbrica); les mesures en viu de cada
versió són a la mateixa carpeta (`viu_abans.json`, `viu_despres.json`, `viu_v3.json`).

## La capa gratuïta de Groq (16-11, nit; `Veus-tachelhit\_escoltats\models\compara_groq.py`)

Clau `GROQ_API_KEY` a `backend/.env` (en Pablo, 16-11). Les mateixes 60 frases, raonament baix,
temperatura 0; resultats a `compara_groq_resultat.json`:

| model | fonts del diccionari | buits | chrF (60, buit = 0) | chrF contestades | shi | Beni Mellal | latència |
|---|---|---|---|---|---|---|---|
| `openai/gpt-oss-120b` | sense | 4 | 0,138 | 0,148 | 0,124 | 0,152 | 0,9 s |
| `openai/gpt-oss-120b` | amb | 0 | 0,258 | 0,258 | 0,242 | 0,273 | 1,2 s |
| `qwen/qwen3.8-27b` | amb | **19** | 0,235 | 0,344 | 0,227 | 0,243 | 49 s |
| *ref.* Gemini 2.5 Flash / NLLB afinat / `qwen3.8-max` | | | 0,571 / 0,571 / 0,471 | | | | |

El que se'n treu: (1) **Groq no serveix per a l'amazic**: el millor, `gpt-oss-120b` amb diccionari,
fa 0,26, la meitat del Gemini i del NLLB afinat; sense diccionari no entén res (0,14). (2) El
`qwen3.8-27b` de Groq es queda en blanc 19 vegades de 60 i tarda 49 s (el raonament s'allarga i
s'esgota el sostre), com el mateix model a Model Studio (0,24) i a OVH (0,22): el model és el límit,
no el proveïdor. (3) El diccionari al prompt ajuda els models que no saben la llengua (+0,12) i no
aporta res als que la saben (Gemini +0,008): és un apòsit, no una solució. (4) On sí que pot servir
Groq: anglès → català ràpid i gratuït al pont, o com a auditor d'àrab/dàrija si Qwen i DeepSeek
s'acaben. 121.000 fitxes gastades, de franc.

## Tamazight MultiLingo App i `tamazightdev` (17-11, matí; `Veus-tachelhit\_escoltats\models\multilingo\`)

En Pablo va passar `github.com/mindful-ai-dude/v3.6-Tamazight_MultiLingo_App`: l'app d'un hackató de
Kaggle (Gemma-3n, agost 2025) per a emergències, amazic ↔ àrab/francès/anglès. El repositori no es
toca des del 6-8-2025 (1 estrella). El que importa és el que hi ha darrere a HuggingFace
(`tamazightdev`): el dataset `tamazight-ar-en-fr` («1.033.656 files», MIT) i una vintena de Gemma
afinats sense cap mètrica publicada.

Mirat sense baixar res al disc (mostres per rang del fitxer):

- **No és 1 M de parelles.** Cada frase surt en les 12 direccions entre quatre llengües: en 3.299
  files mostrejades a cinc punts del fitxer hi havia 278 textos amazics únics (~86.000 entrades
  reals), i una part són numerals generats («ⴽⴽⵓⵥⵜ ⵜⵎⴰⴹ ⴷ ⵙⵎⵎⵓⵙⵎⵔⴰⵡ...»).
- **Tres capes i cap fitxa de procedència:** terminologia de l'IRCAM (l'eval de 10.719 files és quasi
  tot termes de 2-3 mots: 505 de 595 únics), frases de Tatoeba (Tom i Mary, «All roads lead to
  Rome») i números. La llicència MIT és autodeclarada sobre dades de l'IRCAM i de Tatoeba (CC BY).
  Varietat barrejada: hi surt la negació cabilenca «ur... ara».
- **El mateix món que el nostre model.** 100 frases Tamazight→English del seu test (4-14 mots, sense
  numerals, llavor 1114) pel nostre Space (NLLB afinat v3, fitxa Standard Moroccan Tamazight) cap a
  l'anglès, chrF contra el seu anglès: **0,584 de mitjana, 58 de 100 per sobre de 0,5, cap buit**, i
  diverses frases idèntiques («I was tired, so I didn't go.»). El NLLB de base ja es va entrenar amb
  aquestes mateixes frases de Tatoeba: afegir-les no ensenya res, i el vocabulari solt ja vam veure
  que fa nosa (v3). No hi ha català.

Conclusió: font mirada i descartada, com Groq. Els Gemma afinats es podrien mesurar sobre les 60
(GGUF d'uns 2 GB a l'ECS), però tal com són les dades no hi ha motiu per esperar-ne res.
