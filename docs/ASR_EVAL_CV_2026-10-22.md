# Què val el nostre transcriptor, mesurat amb Common Voice (2026-10-22)

Space `Tamazight-NLP/ASR` · font: **Common Voice (Mozilla Data Collective)** · 60 gravacions
(20 per varietat, triades a l'atzar amb llavor fixa d'entre les 1.474 validades).

| origen | gravacions | CER mitjà | WER mitjà |
|---|---|---|---|
| Atles central | 20 | 0.36 | 0.87 |
| Tachelhit | 20 | 0.19 | 0.62 |
| sense varietat | 20 | 0.24 | 0.79 |
| **tot** | **60** | **0.26** | **0.76** |

CER 0 vol dir clavat; 1 vol dir que no n'ha encertat res. Per decidir si una veu diu el que diu un
text caldria estar clarament per sota de 0,5.

## Què vol dir, comparat amb les nostres gravacions

El mateix Space, el mateix dia, amb les mateixes mesures ([informe
d'ahir](ASR_EVAL_2026-10-22.md)):

| font | gravacions | CER mitjà |
|---|---|---|
| Common Voice, tot | 60 | **0.26** |
| Common Voice, només Tachelhit | 20 | **0.19** |
| nostra, Beni Mellal | 15 | 0.39 |
| nostra, Aït Mraw | 15 | 0.86 |
| nostra, altres | 15 | 1.33 |
| **nostra, tot** | **45** | **0.86** |

**El model no està trencat: el nostre material és més difícil.** Transcriu Common Voice tres
vegades millor que la nostra biblioteca. Això descarta la lectura fàcil («el transcriptor no val
res») i deixa tres explicacions, que no s'exclouen:

1. **Com es parla.** Common Voice és text llegit en veu alta, en un registre estàndard i amb bon
   so. Els nostres parlants diuen frases seves, de pressa, amb el so d'una gravació de mòbil.
2. **La referència.** A Common Voice la frase ja ve en tifinag i surt tal com es va llegir. A casa
   nostra el text del parlant és en llatí i l'ha de passar a tifinag el transliterador de l'app:
   cada tria seva que no casa amb la del model compta com a error del model.
3. **La varietat.** El model s'ha entrenat amb amazic estàndard marroquí. Dins de Common Voice ja
   es veu l'efecte en petit: Tachelhit 0,19 contra Atles central 0,36.

El 0,86 de la nostra biblioteca, doncs, és un **sostre**, no la qualitat del model: mesura el
transliterador i el model junts.

### El que aquesta xifra no diu

Els 2.229 clips del corpus són de 51 persones, i dels 1.474 validats **1.324 són d'home i 24 de
dona**. També és text llegit. Un 0,26 aquí pot voler dir «llegeix bé la lectura clara d'un home»
tant com «sent les varietats»: no es pot llegir com que el transcriptor ja serveix per a qualsevol
veu.

## Què en fem

- **No** fer servir el transcriptor per decidir sol si una veu diu el que diu un text: ni 0,26 és
  prou baix per això, i amb el nostre material és 0,86.
- Per saber quant hi pesa el transliterador, caldria mesurar les nostres gravacions amb una
  referència escrita en tifinag a mà. Això és feina de persona, i és el que faria falta abans de
  confiar en qualsevol xifra nostra.
- Mentre el model sigui aquest, l'Atles central (que és el que parlem al projecte) va pitjor que
  el taixelhit: val la pena comptar-hi.

## D'on surten les gravacions

Mozilla Common Voice, *Scripted Speech* 27.0 — Tamazight (`zgh`), `cv-corpus-27.0-2026-09-11`,
baixat del Mozilla Data Collective. Llicència **CC0**: no exigeix atribució, però els clips els van
gravar i validar persones de la comunitat amaziga i és just dir-ho. En baixar-los es va acceptar no
intentar esbrinar qui parla. Els clips no entren al repositori.

El transcriptor que es mesura és `ayymen/stt_zgh_fastconformer_ctc_small` (NeMo FastConformer CTC,
**CC BY 4.0**).

Totes les fonts del projecte: [docs/CREDITS.md](CREDITS.md).

Com s'ha fet: `python tools/asr_eval.py --cv <carpeta amb validated.tsv> --sample 60`.
Dades crues: [`ASR_EVAL_CV_2026-10-22.json`](ASR_EVAL_CV_2026-10-22.json).
