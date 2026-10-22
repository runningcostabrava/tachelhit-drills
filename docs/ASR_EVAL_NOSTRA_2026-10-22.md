# Què val el nostre transcriptor, amb les nostres gravacions (2026-10-22)

> **Correcció.** La primera versió d'aquest informe mesurava `Tamazight-NLP/ASR` — un Space
> d'altri, de Gradio, tocat per últim cop l'agost del 2024. **No és el que fa servir l'app.**
> `tools/asr_eval.py` el duia escrit per defecte. Les xifres d'aquí són del Space que l'app crida
> de debò: `josepabloucr/huggingface-asr-space` (Docker, NeMo FastConformer, amb `/transcribe` i
> `/align`).

Space `https://josepabloucr-huggingface-asr-space.hf.space` · font: **la nostra biblioteca** ·
45 gravacions.

| origen | gravacions | CER mitjà | WER mitjà |
|---|---|---|---|
| Aït Mraw | 15 | 0.87 | 1.57 |
| Beni Mellal | 15 | 0.39 | 1.46 |
| altres | 15 | 1.09 | 2.00 |
| **tot** | **45** | **0.78** | **1.68** |

CER 0 vol dir clavat; 1 vol dir que no n'ha encertat res. Per decidir si una veu diu el que diu un
text caldria estar clarament per sota de 0,5.

## Quant es mou aquesta xifra

Dues passades el mateix dia, amb la mateixa eina i el mateix Space, han donat **0,70** i **0,78**.
La mostra són 45 gravacions triades a l'atzar d'entre més de dues mil, i entremig se'n van esborrar
35 de la biblioteca, així que les frases no eren les mateixes.

**Per tant, aquestes xifres porten un marge d'uns ±0,1.** Només s'hi poden recolzar diferències
grosses — «0,39 contra 1,09» vol dir alguna cosa; «0,70 contra 0,78» no en vol dir cap.

## Què es pot fer amb això

| racó de la biblioteca | CER | es pot fer servir el transcriptor per comprovar una veu? |
|---|---|---|
| Beni Mellal | 0.39 | **a la vora**: és l'únic que s'acosta al 0,5 |
| Aït Mraw | 0.87 | no |
| altres (vídeos, cançons, altres reculls) | 1.09 | no |

I compte: el 0,78 mesura **dues coses alhora**, el transliterador i el model. El text del parlant
és en llatí i l'ha de passar a tifinag el transliterador de l'app; cada tria seva que no casa amb
la del model compta aquí com a error del model. Per saber quant hi pesa cadascun caldria escriure
a mà en tifinag un grapat de les nostres frases i tornar a mesurar. Això és feina de persona.

## Comparat amb material d'altri

| font | CER | què és |
|---|---|---|
| [Tamazight Open Speech](ASR_EVAL_TOSD_2026-10-22.md) | 0.20 | amazic estàndard, llegit, so net |
| [Common Voice](ASR_EVAL_CV_2026-10-22.md) | 0.27 | text llegit, 9 de cada 10 veus d'home |
| **la nostra biblioteca** | **0.78** | veu espontània, dialectal, gravada amb un mòbil |

**El model no està trencat: el nostre material és més difícil.** Sent bé l'amazic estàndard llegit,
i el que no sent és com parla la nostra gent.

## D'on surten les gravacions

De la nostra biblioteca: Halima i Driss (Aït Mraw) i els reculls de Beni Mellal, que han dit
aquestes frases per al projecte. El text de referència és el seu, passat a tifinag amb el
transliterador de l'app.

Totes les fonts del projecte: [docs/CREDITS.md](CREDITS.md).

Com s'ha fet: `python tools/asr_eval.py --sample 45`.
Dades crues: [`ASR_EVAL_NOSTRA_2026-10-22.json`](ASR_EVAL_NOSTRA_2026-10-22.json).
