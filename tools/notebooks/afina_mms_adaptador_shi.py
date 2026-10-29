"""Afinar el mms-1b-all pel seu adaptador de taixelhit

## Per què aquest i no seguir afinant el petit

La comparació sobre les mateixes frases, amb el mateix plegat del text:

                  el nostre v3   wav2vec2-berber   mms-1b-all (shi)
    test-dins        0,1883          0,3930            0,2894
    test-fora        0,3281          0,4481            0,3452
    test-mtnra       0,0841          0,2762            0,2170

Guanyem als tres. Però **a fora de casa guanyem per un 5% relatiu a un model que no ha vist mai
cap frase nostra.** Tres passades d'afinament del `wav2vec2-berber` ens han posat just per
davant d'un model sense afinar. El sostre no és el material: és la base.

El `mms-1b-all` té mil milions de paràmetres contra tres-cents del nostre, i porta un adaptador
entrenat per a taixelhit (`shi`). Afinar aquell adaptador amb el nostre corpus és canviar
**una** cosa —la base— deixant les dades i la mesura idèntiques.

## Què s'entrena i què no

Només l'adaptador i el cap de sortida: uns pocs milions de paràmetres contra mil milions. La
base es congela. Això no és per estalviar: amb 3.650 frases, moure mil milions de paràmetres
és la manera segura d'oblidar tot el que el model ja sap i quedar pitjor que al principi.

## El que es manté igual a posta

Les mateixes particions (per FONT, no per línia), el mateix plegat a 26 lletres, la mateixa
funció de distància i els mateixos tres tests. Si es canviés res d'això, el número no es podria
comparar amb la taula de dalt i la passada no serviria de res.

## I una cosa que s'ha de vigilar

L'adaptador `shi` escriu amb les lletres riques (`ɣ`, `ḍ`, `ẓ`) i el nostre text d'or està plegat
a 26. S'entrena contra el text plegat, de manera que el model aprendrà a escriure plegat. És el
que volem mentre la biblioteca escrigui així, i queda escrit que el dia que escrigui bé, això
s'ha de refer.
"""

# %%
BASE = "facebook/mms-1b-all"
LLENGUA = "shi"
EPOQUES = 6
LOT = 4
#: Més alt que el del model petit (1e-4) perquè aquí només es mouen els adaptadors: amb pocs
#: paràmetres i poques passes, un ritme baix no arriba a moure res.
RITME = 3e-4
QUANTS = 0
SEGONS_MAXIM = 14

# %%
import os
import subprocess
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44",
                "librosa", "soundfile", "accelerate"], check=False)
print("instal·lat")

# %%
import collections
import json

import numpy as np
import torch


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

train = [f for f in files if f["split"] == "train"]
dev = [f for f in files if f["split"].startswith("dev")]
proves = {s: [f for f in files if f["split"] == s]
          for s in ("test-dins", "test-fora", "test-mtnra")}
print("entrenen %d · es miren %d" % (len(train), len(dev)))
for s, g in proves.items():
    print("  %-11s %d" % (s, len(g)))

# %%
import librosa  # noqa: E402
from transformers import AutoModelForCTC, AutoProcessor  # noqa: E402

proc = AutoProcessor.from_pretrained(BASE)
#: Sense això el model llegeix amb l'alfabet d'una altra llengua i no aprèn res del nostre.
proc.tokenizer.set_target_lang(LLENGUA)
model = AutoModelForCTC.from_pretrained(BASE, ctc_loss_reduction="mean",
                                        ignore_mismatched_sizes=True)
model.load_adapter(LLENGUA)
print("base: %s amb l'adaptador %s" % (BASE, LLENGUA))

#: Es congela tot i es tornen a obrir NOMÉS els adaptadors. La comprovació del final no és
#: decorativa: si per un canvi de versió `_get_adapters` deixés de trobar-los, s'entrenaria
#: el model sencer sense avisar i el resultat seria pitjor que no fer res.
model.freeze_base_model()
adaptadors = model._get_adapters()
#: `_get_adapters()` torna els adaptadors I el `lm_head`. La primera passada el reobria i el
#: movia a 3e-4 contra 3.650 frases de text plegat: reajustar agressivament el cap de sortida
#: calibrat de `shi` mentre l'acústica no es mou és la recepta exacta per empitjorar, i és el
#: que va passar (auditoria del 29/10). El cap es queda congelat: només es mouen els adaptadors.
for nom_p, p in adaptadors.items():
    p.requires_grad = not nom_p.startswith("lm_head")
mou = sum(p.numel() for p in model.parameters() if p.requires_grad)
tot = sum(p.numel() for p in model.parameters())
print("es mouen %.1f M paràmetres de %.0f M (%.2f%%)"
      % (mou / 1e6, tot / 1e6, 100.0 * mou / tot))
if mou == 0 or mou > tot * 0.2:
    raise SystemExit("els adaptadors no s'han trobat bé: s'entrenaria el que no toca")

#: El forat que l'auditoria va trobar: amb la base congelada i el punt de control del gradient
#: en mode reentrant (el defecte), cap entrada de l'encoder no demana gradient, el segment no
#: retropropaga i els adaptadors de dins NO ES MOUEN. Només es movia el `lm_head`, que és fora.
#: Es demana el mode no reentrant i que les entrades portin gradient, que és el que fa PEFT.
model.enable_input_require_grads()
model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})

vocab = set(proc.tokenizer.get_vocab())
falten = collections.Counter()
for f in files:
    for c in f["lletra"]:
        if c not in vocab and c != " ":
            falten[c] += 1
print("lletres del nostre text que l'alfabet %s no té: %s"
      % (LLENGUA, dict(falten.most_common(8)) or "cap"))


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


import re  # noqa: E402
import unicodedata  # noqa: E402

#: La MATEIXA taula que `compara_sobre_test_v3.py`, caràcter per caràcter. La primera passada
#: d'aquest quadern comparava la sortida CRUA de l'adaptador (`ɣ ḍ ẓ ġ ḫ`...) amb el text d'or
#: PLEGAT a 26 lletres, i el 0,4027 que en va sortir no era comparable amb el 0,3452 del
#: quadern de comparació, que sí que plega: eren dues regles diferents (auditoria del 29/10).
TIF_A_LLATI = {
    "ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "d", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k",
    "ⵀ": "h", "ⵃ": "h", "ⵄ": "a", "ⵅ": "x", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l",
    "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "g", "ⵙ": "s", "ⵚ": "s",
    "ⵛ": "c", "ⵜ": "t", "ⵟ": "t", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "z", "ⵯ": "w",
}
PLEGA = {"ɣ": "g", "γ": "g", "ġ": "g", "ɛ": "a", "ḥ": "h", "ḫ": "x", "ḍ": "d", "ṭ": "t",
         "ẓ": "z", "ṣ": "s", "ṛ": "r", "š": "c", "ž": "j", "ǧ": "j", "č": "c", "ʷ": "w",
         "'": "", "’": ""}


def a_llati(t):
    t = unicodedata.normalize("NFC", (t or "")).strip().lower()
    t = "".join(TIF_A_LLATI.get(c, c) for c in t)
    t = "".join(PLEGA.get(c, c) for c in t)
    return re.sub(r"[^a-z ]+", "", t).strip()


#: El test net (#482): els 256 clips de prova del Common Voice zgh, 26 parlants, disjunts per
#: font i per veu de tot l'entrenament. És l'únic número que decideix aquesta passada: el mms
#: sense afinar hi fa 0,2095 i el v3 0,2297. Els altres tres tests comparteixen font amb train.
CV = de_kaggle("cv_test.json")
if CV:
    _cv = json.load(open(CV, encoding="utf-8"))
    for c in _cv:
        c["cami"] = os.path.join(os.path.dirname(CV), "audio", c["fitxer"])
        c["lletra"] = a_llati(c["sentence"])
        c["varietat"] = "cv:" + ((c.get("variant") or "sense variant")[:14])
    proves["cv-zgh-test"] = [c for c in _cv if c["lletra"] and os.path.exists(c["cami"])]
    print("test net del Common Voice zgh: %d clips" % len(proves["cv-zgh-test"]))
else:
    print("AVÍS: sense cv_test.json no hi ha test net; els altres tres comparteixen font amb train")


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
    """També aquí es plega: el CER de dev tria el millor model, i amb la regla equivocada
    triava el que menys lletres riques escrivia, no el que millor sentia."""
    ids = np.argmax(pred.predictions, axis=-1)
    et = pred.label_ids
    et[et == -100] = proc.tokenizer.pad_token_id
    dits = [a_llati(x) for x in proc.batch_decode(ids)]
    refs = [a_llati(x) for x in proc.batch_decode(et, group_tokens=False)]
    d = sum(distancia(r, h) for r, h in zip(refs, dits))
    n = sum(len(r) for r in refs)
    return {"cer": d / max(1, n)}


# %%
from transformers import Trainer, TrainingArguments  # noqa: E402

args = TrainingArguments(
    output_dir="/kaggle/working/mms_afinat", per_device_train_batch_size=LOT,
    per_device_eval_batch_size=1, eval_accumulation_steps=1,
    num_train_epochs=EPOQUES, learning_rate=RITME, warmup_steps=100,
    fp16=torch.cuda.is_available(), logging_steps=50,
    eval_strategy="epoch", save_strategy="epoch", save_total_limit=1,
    load_best_model_at_end=True, metric_for_best_model="cer", greater_is_better=False,
    report_to=[],
)
entrenador = Trainer(model=model, args=args, train_dataset=Talls(train),
                     eval_dataset=Talls(dev), data_collator=ajunta,
                     compute_metrics=mesura, processing_class=proc.feature_extractor)

#: La comprovació que l'auditoria del 29/10 va demanar i que no es podia fer sense executar:
#: una passada enrere sobre un lot, i la norma del gradient dels adaptadors SEPARADA de la del
#: cap. Si la dels adaptadors és zero, el punt de control del gradient els ha deixat fora i
#: només es mouria el cap: exactament la recepta que va empitjorar la primera passada.
_ap = "cuda" if torch.cuda.is_available() else "cpu"
model.to(_ap).train()
_lot = ajunta([Talls(train)[i] for i in range(2)])
_s = model(input_values=_lot["input_values"].to(_ap), labels=_lot["labels"].to(_ap))
_s.loss.backward()
_n_ad = sum(float(p.grad.norm()) ** 2 for n, p in model.named_parameters()
            if p.grad is not None and not n.startswith("lm_head")) ** 0.5
_n_cap = sum(float(p.grad.norm()) ** 2 for n, p in model.named_parameters()
             if p.grad is not None and n.startswith("lm_head")) ** 0.5
print("norma del gradient — adaptadors %.3e · cap %.3e" % (_n_ad, _n_cap))
model.zero_grad()
if _n_ad == 0.0:
    raise SystemExit("els adaptadors NO reben gradient: no val la pena entrenar")

entrenador.train()

#: Es desa NOMÉS l'adaptador: són pocs megabytes contra els 3,9 GB del model sencer, i el
#: model base es torna a baixar sempre igual.
os.makedirs("/kaggle/working/mms_afinat", exist_ok=True)
torch.save({k: v.cpu() for k, v in model._get_adapters().items()},
           "/kaggle/working/mms_afinat/adaptador_%s.pt" % LLENGUA)
proc.save_pretrained("/kaggle/working/mms_afinat")
print("adaptador desat")


# %%
def llegeix(f):
    ona, _ = librosa.load(f["cami"], sr=16000, mono=True)
    ent = proc(ona, sampling_rate=16000, return_tensors="pt")
    if torch.cuda.is_available():
        ent = {k: v.cuda() for k, v in ent.items()}
    with torch.no_grad():
        ids = model(**ent).logits.argmax(-1)
    return proc.batch_decode(ids)[0].strip()


model.eval()
sortida, taula = [], {}
#: A partir d'aquí tot es compara PLEGAT, amb la sortida crua desada al costat.
print("\n=== CER per banda ===")
for nom, g in proves.items():
    if not g:
        continue
    d, n = 0, 0
    for f in g:
        try:
            cru = llegeix(f)
            dit = a_llati(cru)
        except Exception as e:
            print("  %s ha fallat: %s" % (f["fitxer"], str(e)[:60]), flush=True)
            continue
        d += distancia(f["lletra"], dit)
        n += len(f["lletra"])
        sortida.append({"fitxer": f["fitxer"], "split": nom, "varietat": f["varietat"],
                        "or": f["lletra"], "dit": dit, "dit_cru": cru})
    taula[nom] = d / max(1, n)
    print("  %-11s CER %.4f  (%d frases)" % (nom, taula[nom], len(g)), flush=True)

json.dump(sortida, open("/kaggle/working/prova_mms.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# %%
#: La taula sencera. Els tres números de dalt venen de la mateixa mesura sobre les mateixes
#: frases: es poden comparar directament.
VELLS = {
    "el nostre v3 (wav2vec2-berber afinat)": {"test-dins": 0.1883, "test-fora": 0.3281,
                                              "test-mtnra": 0.0841},
    "wav2vec2-berber sense afinar": {"test-dins": 0.3930, "test-fora": 0.4481,
                                     "test-mtnra": 0.2762},
    "mms-1b-all sense afinar": {"test-dins": 0.2894, "test-fora": 0.3452,
                                "test-mtnra": 0.2170},
}
print("\n=== on quedem ===")
print("  %-38s %-11s %-11s %-11s" % ("", "test-dins", "test-fora", "test-mtnra"))
for nom, v in VELLS.items():
    print("  %-38s %-11.4f %-11.4f %-11.4f" % (nom, v["test-dins"], v["test-fora"],
                                               v["test-mtnra"]))
print("  %-38s %-11.4f %-11.4f %-11.4f" % ("mms-1b-all AFINAT (aquesta passada)",
                                           taula.get("test-dins", float("nan")),
                                           taula.get("test-fora", float("nan")),
                                           taula.get("test-mtnra", float("nan"))))
print("\nel que decideix si ha valgut la pena és test-fora: cap d'aquelles fonts no ha entrenat.")
print("test-mtnra no serveix per decidir: el MTNRA no diu qui parla i les veus poden ser les")
print("mateixes de l'entrenament.")
