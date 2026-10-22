# Què val el nostre transcriptor (2026-10-22)

> **Correcció.** La primera versió d'aquest informe mesurava `Tamazight-NLP/ASR`, un Space d'altri
> que l'app no fa servir; `tools/asr_eval.py` el duia escrit per defecte. Les xifres d'aquí són del
> Space que l'app crida de debò: `josepabloucr/huggingface-asr-space`. Les xifres es mouen uns
> ±0,1 segons la mostra — vegeu [l'informe de la nostra biblioteca](ASR_EVAL_NOSTRA_2026-10-22.md).

Space `https://josepabloucr-huggingface-asr-space.hf.space` · font: **Tamazight Open Speech Dataset** · 60 gravacions.

| origen | gravacions | CER mitjà | WER mitjà |
|---|---|---|---|
| subset_1 | 30 | 0.15 | 0.49 |
| subset_2 | 30 | 0.25 | 0.72 |
| tot | 60 | 0.20 | 0.60 |

CER 0 vol dir clavat; 1 vol dir que no n'ha encertat res. Per decidir si una veu diu el que diu un text caldria estar clarament per sota de 0,5.

## Què vol dir

**La millor xifra de totes: 0,20.** És material llegit, en amazic estàndard i amb so net (48 kHz), que és justament el que el model va aprendre.

Serveix de referència: diu fins on arriba aquest transcriptor quan tot va a favor. Tot el que les nostres gravacions pugen per sobre d'aquest 0,20 és el preu de la veu espontània, del dialecte i del micròfon del mòbil.

Aquestes 1.801 gravacions **no entren a la biblioteca** (no diuen qui parla ni d'on és, i no porten significat en català), però sí que en pot sortir una altra cosa: amb `/align` se'n treuen els temps paraula per paraula, i 521 de les seves formes surten també als nostres drills.

## D'on surten les gravacions

**Tamazight Open Speech Dataset**, publicat per **Tamazight NLP** al Mozilla Data Collective, llicència **Apache-2.0**. 1.801 gravacions, 1,44 h, amb la frase en tifinag. No entren a la biblioteca: no diuen qui parla ni d'on és, i no porten cap significat en català. Aquí només fan de jutge.

Totes les fonts del projecte: [docs/CREDITS.md](CREDITS.md).
