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

Pendent: la mateixa taula amb Qwen (Model Studio nou) i, si en Pablo obre un projecte gratuït a
AI Studio, amb Gemini; i la prova de 10 dibuixos de targeta amb Qwen-Image contra els de Gemini.
Resultats sencers: `Veus-tachelhit\_escoltats\models\compara_resultat.json`.
