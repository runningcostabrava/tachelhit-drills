# Què val el nostre transcriptor (2026-10-22)

> **Correcció.** La primera versió d'aquest informe mesurava `Tamazight-NLP/ASR`, un Space d'altri
> que l'app no fa servir; `tools/asr_eval.py` el duia escrit per defecte. Les xifres d'aquí són del
> Space que l'app crida de debò: `josepabloucr/huggingface-asr-space`. Les xifres es mouen uns
> ±0,1 segons la mostra — vegeu [l'informe de la nostra biblioteca](ASR_EVAL_NOSTRA_2026-10-22.md).

Space `https://josepabloucr-huggingface-asr-space.hf.space` · font: **Common Voice (Mozilla Data Collective)** · 60 gravacions.

| origen | gravacions | CER mitjà | WER mitjà |
|---|---|---|---|
| Atles central | 20 | 0.36 | 0.88 |
| Tachelhit | 20 | 0.18 | 0.62 |
| sense varietat | 20 | 0.25 | 0.88 |
| tot | 60 | 0.27 | 0.79 |

CER 0 vol dir clavat; 1 vol dir que no n'ha encertat res. Per decidir si una veu diu el que diu un text caldria estar clarament per sota de 0,5.

## Què vol dir

Text llegit, en amazic estàndard, amb bon so: 0,27. Les nostres gravacions, al mateix transcriptor, donen 0,78. La diferència no és el model, és el material.

Dels 1.474 clips validats, **1.324 són d'home i 24 de dona**, i tot és llegit en veu alta. Un 0,27 aquí no vol dir que serveixi per a qualsevol veu.

## D'on surten les gravacions

Mozilla Common Voice, *Scripted Speech* 27.0 — Tamazight (`zgh`), `cv-corpus-27.0-2026-09-11`, baixat del Mozilla Data Collective. Llicència **CC0**: no exigeix atribució, però els clips els van gravar i validar persones de la comunitat amaziga i és just dir-ho. En baixar-los es va acceptar no intentar esbrinar qui parla.

Totes les fonts del projecte: [docs/CREDITS.md](CREDITS.md).
