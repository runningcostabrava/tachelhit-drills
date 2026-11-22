# ADR 0006: El MMS afinat, al costat del NeMo i no en el seu lloc

- **Estat:** acceptada (el desplegament); pendent (quines crides del backend hi passen)
- **Data:** 2026-10-29
- **Decideix:** Pablo (propietari): «desplega el model nou si es que ja s'ha aconseguit»
- **Issue:** #491

## El problema

El primer test net del projecte (Common Voice zgh, 256 clips, 26 parlants, cap font ni veu de
l'entrenament) diu, en CER plegat i amb bootstrap aparellat:

| model | CER |
|---|---|
| el nostre v3 (wav2vec2-berber afinat) | 0,230 |
| mms-1b-all sense afinar | 0,210 |
| **mms-1b-all + adaptador `shi` afinat (corpus v3, c→š, x→ḫ)** | **0,154** |

El Space de producció transcriu amb un altre model, el NeMo `stt_zgh_fastconformer_ctc_small`, que
escriu en tifinag; `/align` hi està construït, i parts del backend (la lectura de pàgines narrades,
entre d'altres) en fan servir la sortida en tifinag. El MMS escriu en llatí.

## Les opcions

| opció | a favor | en contra |
|---|---|---|
| No fer res | cap risc | el millor lector que tenim no el fa servir ningú |
| Substituir el NeMo | un sol model | trenca `/align` i el que espera tifinag |
| Un Space nou només per al MMS | separat | HuggingFace ja no ho permet sense PRO (402 el 29/10) |
| **El MMS al Space actual, com a ruta nova** | additiu i reversible; cap ruta existent no canvia | el Space carrega 3,9 GB més; la ruta respon 503 fins que ha carregat |

## La decisió

`POST /transcribe_mms` al Space actual (`huggingface-asr-space/mms_shi.py`), amb la mateixa forma de
resposta que `/transcribe`. El model es carrega en un fil de fons, de manera que el NeMo continua
responent mentre arrenca. L'adaptador (8,9 MB) no és a git: viu al repo privat
`josepabloucr/mms-1b-shi-tachelhit` i `tools/deploy_asr_space.py` el copia al Space en desplegar.

## Què en ve al darrere

- Cap crida del backend no canvia amb aquesta ADR. Quines passen al MMS (p. ex. la transcripció de
  les gravacions noves cap a `text_tachelhit_suggested`) es decideix en un issue propi, mirant qui
  espera tifinag.
- El Space gasta més memòria (NeMo petit + MMS 1B en CPU); si no hi cap, la ruta ho dirà a `/health`
  i el NeMo no se'n ressent.
- La sortida és llatí de l'alfabet `shi` del MMS (š, ḫ, ɣ, ḥ…); el tifinag surt del transliterador.
