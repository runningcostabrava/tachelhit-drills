"""Segona volta d'afinament: el doble de material, i un test que no menteix

## Què canvia respecte de la primera

**1. El doble de material.** 3.650 frases per entrenar, contra 2.550. El gros del que s'hi
afegeix són **1.501 frases del MTNRA**, i això importa més del que diu el número: el 90% del que
el model havia sentit fins ara és Central Atlas, i amb taixelhit del Souss **empatava amb un
model sense afinar**. Ara en sent mil cinc-centes.

**2. Fora 96 parelles mal aparellades**, i no pel desacord amb el model —que seria circular—
sinó per raons que es veuen soles: 83 són taules de conjugació (el text són vuit formes i la veu
en diu una), 10 són gravacions que **diuen més** del que hi ha escrit (el text és només el
principi, i això ensenya el model a callar a mitja frase) i 3 no tenen veu.

**3. La partició és per font, no per línia.** Aquest és l'error que inflava el 0,2025: de les 37
línies de «el llop i el xai» —una sola gravació llegida seguida— 33 van anar a entrenar i 4 a
provar. El model havia sentit les veïnes de les frases que després li preguntàvem.

**4. I es mesura per varietat.** Un sol número amaga justament el que volem saber: si fem el
model millor en taixelhit i pitjor a Beni Mellal, una mitjana no ho ensenyarà.

## Correcció de l'auditoria del 29 d'octubre — llegir ABANS de fiar-se dels números

El punt 3 és veritat per a les històries, però **no per als tests**. Comprovat contra
`corpus_v3.json`, camp `font`:

    recull:benimellal-anki   train 1680 · test-dins 150 · dev-dins 130
    MTNRA                    train 1501 · test-mtnra 300

`test-dins` i `test-mtnra` comparteixen FONT amb l'entrenament: és partició per línia amb un
altre nom. Mots del test ja vistos a l'entrenament: dins 57%, fora 69%, **MTNRA 82%**. El
0,0841 del MTNRA no mesura generalització; el 0,1883 de dins tampoc. **L'únic test net és
`test-fora`** (ILoveLanguages, Tamazight For All, Nomatrails: cap a train), amb 101 frases, i
allà el v3 i el `mms-1b-all` sense afinar són indistingibles (IC 95% de la diferència
[-0,045, +0,011]; per frase 44 guanya, 41 perd, 16 empat).

I `speaker` és buit o val «MTNRA» a tot el corpus: la separació per parlant **no es pot
comprovar enlloc**. Mentre això sigui així, «fuita de veu» no es pot ni confirmar ni refutar.

## El que s'ha de llegir del resultat

**El CER sortirà pitjor que 0,2025, i no voldrà dir que el model hagi empitjorat.** Voldrà dir
que per fi el test no conté els germans de les frases d'entrenament. Els números comparables
entre ells són els d'aquesta passada, no els d'ahir.

I una pèrdua que queda escrita: tot el text es plega a 26 lletres (`ɣ→g`, `ɛ→a`, `ḍ→d`…) perquè
és el que fa el model base i és el que fèiem. El MTNRA escriu aquestes lletres de debò al 63% de
les frases, i les hi estem llençant. El dia que la biblioteca escrigui bé, això s'ha de refer.
"""

# %%
BASE = "TutlaytAI/wav2vec2-berber"
EPOQUES = 8
LOT = 8
RITME = 1e-4
#: Amb 0 es fan totes. Serveix per a una passada curta de prova.
QUANTS = 0
#: Més llarg que això i la GPU peta. Va ser una de les quatre caigudes de la primera volta.
SEGONS_MAXIM = 14

# %%
import os
import subprocess
import sys

#: Una sola GPU: amb dues, el Trainer reparteix i el lot efectiu es dobla sense avisar.
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44",
                "librosa", "soundfile", "accelerate"], check=False)
print("instal·lat")

# %%
import json

import numpy as np


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


FITXA = de_kaggle("corpus_v3.json")
if not FITXA:
    raise SystemExit("no trobo corpus_v3.json: " + str(os.listdir("/kaggle/input")))
ARREL = os.path.dirname(FITXA)
files = json.load(open(FITXA, encoding="utf-8"))
for f in files:
    f["cami"] = os.path.join(ARREL, "audio", f["fitxer"])
files = [f for f in files if f["lletra"] and os.path.exists(f["cami"])]
if QUANTS:
    files = files[:QUANTS]

import collections  # noqa: E402

print("files: %d" % len(files))
print("\nper banda i varietat:")
for s, n in collections.Counter(f["split"] for f in files).most_common():
    g = [f for f in files if f["split"] == s]
    vs = collections.Counter(f["varietat"] for f in g)
    print("  %-11s %5d  %s" % (s, n, ", ".join("%s(%d)" % (a, b) for a, b in vs.most_common())))

train = [f for f in files if f["split"] == "train"]
dev = [f for f in files if f["split"].startswith("dev")]
proves = {s: [f for f in files if f["split"] == s]
          for s in ("test-dins", "test-fora", "test-mtnra")}

# %%
import librosa
import torch
from transformers import AutoModelForCTC, AutoProcessor

proc = AutoProcessor.from_pretrained(BASE)
model = AutoModelForCTC.from_pretrained(BASE, ctc_loss_reduction="mean",
                                        pad_token_id=proc.tokenizer.pad_token_id)
model.freeze_feature_encoder()
#: Canvia memòria per temps. Sense això la primera volta queia per OOM.
model.gradient_checkpointing_enable()
print("base carregada: %s" % BASE)
print("alfabet del model: %d símbols" % len(proc.tokenizer.get_vocab()))

#: Les lletres del nostre text que el model base no sap escriure. Si n'hi ha, el model no pot
#: encertar-les MAI i el CER porta un terra que no és culpa seva. Val més saber-ho abans.
vocab = set(proc.tokenizer.get_vocab())
falten = collections.Counter()
for f in files:
    for c in f["lletra"]:
        if c not in vocab and c != " ":
            falten[c] += 1
print("lletres del nostre text que el model base no té: %s"
      % (dict(falten.most_common(8)) or "cap"))


class Talls(torch.utils.data.Dataset):
    def __init__(self, files):
        self.files = files

    def __len__(self):
        return len(self.files)

    def __getitem__(self, i):
        f = self.files[i]
        ona, _ = librosa.load(f["cami"], sr=16000, mono=True)
        ona = ona[:int(SEGONS_MAXIM * 16000)]
        x = proc(ona, sampling_rate=16000).input_values[0]
        y = proc.tokenizer(f["lletra"]).input_ids
        return {"input_values": x, "labels": y}


def ajunta(lot):
    x = proc.pad([{"input_values": b["input_values"]} for b in lot], padding=True,
                 return_tensors="pt")
    y = proc.tokenizer.pad([{"input_ids": b["labels"]} for b in lot], padding=True,
                           return_tensors="pt")
    x["labels"] = y["input_ids"].masked_fill(y.attention_mask.ne(1), -100)
    return x


def distancia(a, b):
    if a == b:
        return 0
    if not a or not b:
        return max(len(a), len(b))
    ant = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        act = [i]
        for j, cb in enumerate(b, 1):
            act.append(min(ant[j] + 1, act[j - 1] + 1, ant[j - 1] + (ca != cb)))
        ant = act
    return ant[-1]


def mesura(pred):
    ids = np.argmax(pred.predictions, axis=-1)
    et = pred.label_ids
    et[et == -100] = proc.tokenizer.pad_token_id
    dits = proc.batch_decode(ids)
    refs = proc.batch_decode(et, group_tokens=False)
    d = sum(distancia(r.strip(), h.strip()) for r, h in zip(refs, dits))
    n = sum(len(r.strip()) for r in refs)
    return {"cer": d / max(1, n)}


# %%
from transformers import Trainer, TrainingArguments  # noqa: E402

args = TrainingArguments(
    output_dir="/kaggle/working/afinat", per_device_train_batch_size=LOT,
    #: D'un en un per avaluar, i sense acumular a la GPU: la primera volta va caure aquí.
    per_device_eval_batch_size=1, eval_accumulation_steps=1,
    num_train_epochs=EPOQUES, learning_rate=RITME, warmup_steps=200,
    fp16=torch.cuda.is_available(), logging_steps=50,
    eval_strategy="epoch", save_strategy="epoch", save_total_limit=1,
    load_best_model_at_end=True, metric_for_best_model="cer", greater_is_better=False,
    report_to=[],
)
entrenador = Trainer(model=model, args=args, train_dataset=Talls(train),
                     eval_dataset=Talls(dev), data_collator=ajunta,
                     compute_metrics=mesura, processing_class=proc.feature_extractor)
print("entrenant amb %d, mirant amb %d" % (len(train), len(dev)))
entrenador.train()
entrenador.save_model("/kaggle/working/afinat")
proc.save_pretrained("/kaggle/working/afinat")
print("desat a /kaggle/working/afinat")


# %%
#: La mesura final, una per varietat i una per banda. Un sol número amagaria si hem guanyat
#: en taixelhit perdent a Beni Mellal.
def llegeix(f):
    ona, _ = librosa.load(f["cami"], sr=16000, mono=True)
    ent = proc(ona, sampling_rate=16000, return_tensors="pt")
    if torch.cuda.is_available():
        ent = {k: v.cuda() for k, v in ent.items()}
    with torch.no_grad():
        ids = model(**ent).logits.argmax(-1)
    return proc.batch_decode(ids)[0].strip()


model.eval()
sortida = []
print("\n=== CER per banda i per varietat ===")
for nom, g in proves.items():
    if not g:
        continue
    per_var = collections.defaultdict(lambda: [0, 0])
    for f in g:
        try:
            dit = llegeix(f)
        except Exception as e:
            print("  %s ha fallat: %s" % (f["fitxer"], str(e)[:60]), flush=True)
            continue
        d = distancia(f["lletra"], dit)
        per_var[f["varietat"]][0] += d
        per_var[f["varietat"]][1] += len(f["lletra"])
        sortida.append({"fitxer": f["fitxer"], "split": nom, "varietat": f["varietat"],
                        "or": f["lletra"], "dit": dit,
                        "cer": round(d / max(1, len(f["lletra"])), 3)})
    print("\n  %s" % nom)
    for v, (d, n) in sorted(per_var.items()):
        print("    %-12s CER %.4f  (%d frases)" % (v, d / max(1, n),
                                                   sum(1 for f in g if f["varietat"] == v)))

json.dump(sortida, open("/kaggle/working/prova_v3.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nper comparar, el que sabem d'abans:")
print("  el nostre model v1: CER 0,2025 sobre un test partit per LÍNIA (inflat)")
print("  wav2vec2-berber sense afinar: 0,4889 sobre aquell mateix test")
print("  NeMo zgh: 0,38 sobre gravacions nostres · mms-1b-all: 0,43")
print("\nel número d'aquesta passada NO es compara amb el 0,2025: aquell test era un altre.")
print("desat a prova_v3.json")
