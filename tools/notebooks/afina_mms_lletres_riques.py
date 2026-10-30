# Afina el mms-1b `shi` amb les lletres riques (ɣ ɛ ḥ ḍ ṭ ṣ ẓ). Les passades anteriors plegaven
# el text a 26 lletres abans d'entrenar: el model no en podia aprendre cap. Va a *_suggested.
#: "tot": tot el corpus amb l'objectiu ric. "ric": fora les frases nostres sense cap lletra rica,
#: que ensenyen g on hi ha ɣ (només un 8% de la biblioteca les escriu).
FILTRE = "FILTRE_AQUI"
BASE = "facebook/mms-1b-all"
LLENGUA = "shi"
EPOQUES = 6
LOT = 4
#: Més alt que el del model petit (1e-4) perquè aquí només es mouen els adaptadors: amb pocs
#: paràmetres i poques passes, un ritme baix no arriba a moure res.
RITME = 3e-4
QUANTS = 0
SEGONS_MAXIM = 14


import os
import subprocess
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44",
                "librosa", "soundfile", "accelerate"], check=False)
print("instal·lat")


import collections
import difflib
import json
import re
import unicodedata

import numpy as np
import torch


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


#: El v4 (v3 + Common Voice acotat per parlant) si hi és; si no, el v3.
FITXA = de_kaggle("corpus_v4.json") or de_kaggle("corpus_v3.json")
if not FITXA:
    raise SystemExit("no trobo corpus_v4.json ni corpus_v3.json: " + str(os.listdir("/kaggle/input")))
print("corpus: %s" % os.path.basename(FITXA))
ARREL = os.path.dirname(FITXA)
files = json.load(open(FITXA, encoding="utf-8"))
for f in files:
    f["cami"] = os.path.join(ARREL, "audio", f["fitxer"])
files = [f for f in files if f["lletra"] and os.path.exists(f["cami"])]
if QUANTS:
    files = files[:QUANTS]

#: L'alfabet shi escriu ġ per ɣ i ε (grega) per ɛ; no té ṛ, c, x, o, p, v.
TIF_RIC = {
    "ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k",
    "ⵀ": "h", "ⵃ": "ḥ", "ⵄ": "ε", "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l",
    "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ", "ⵙ": "s", "ⵚ": "ṣ",
    "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w",
}
LLATI_RIC = {"ɣ": "ġ", "γ": "ġ", "ɛ": "ε", "ṛ": "r", "c": "š", "x": "ḫ", "χ": "ḫ", "ž": "j",
             "ǧ": "j", "ʷ": "w", "v": "f", "p": "b", "o": "u"}
LLETRES_RIQUES = "ġεḥḍṭṣẓ"


def rica(t):
    t = unicodedata.normalize("NFC", (t or "")).strip().lower()
    #: Alguns textos porten «llatí (tifinag)»: només es llegeix la frase.
    t = re.sub(r"\(.*?\)", " ", t) or t
    #: gh, kh, sh, ch i els números de l'arabizi són la mateixa lletra escrita d'una altra manera.
    for digraf, lletra in (("gh", "ġ"), ("kh", "ḫ"), ("sh", "š"), ("ch", "š"), ("3", "ε"), ("7", "ḥ"), ("9", "q")):
        t = t.replace(digraf, lletra)
    t = "".join(TIF_RIC.get(c, c) for c in t)
    t = "".join(LLATI_RIC.get(c, c) for c in t)
    t = re.sub(r"[^a-zġεḥḍṭṣẓḫš ]+", "", t)
    return re.sub(r" +", " ", t).strip()


for f in files:
    f["rica"] = rica(f.get("text_original")) or rica(f["lletra"])
FONTS_RIQUES = ("MTNRA", "CV-zgh", "parlant:IRCAM")
if FILTRE == "ric":
    abans = len(files)
    files = [f for f in files if f["split"] != "train" or f["font"].startswith(FONTS_RIQUES)
             or any(c in f["rica"] for c in LLETRES_RIQUES)]
    print("filtre ric: %d -> %d frases" % (abans, len(files)))

train = [f for f in files if f["split"] == "train"]
dev = [f for f in files if f["split"].startswith("dev")]
proves = {s: [f for f in files if f["split"] == s]
          for s in ("test-dins", "test-fora", "test-mtnra")}
print("entrenen %d · es miren %d" % (len(train), len(dev)))
for s, g in proves.items():
    print("  %-11s %d" % (s, len(g)))


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
    for c in f["rica"]:
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
        y = proc.tokenizer(f["rica"]).input_ids
        return {"input_values": x, "labels": y}


def ajunta(lot):
    x = proc.pad([{"input_values": b["input_values"]} for b in lot], padding=True,
                 return_tensors="pt")
    y = proc.tokenizer.pad([{"input_ids": b["labels"]} for b in lot], padding=True,
                           return_tensors="pt")
    x["labels"] = y["input_ids"].masked_fill(y.attention_mask.ne(1), -100)
    return x



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
         "ʃ": "c", "χ": "x", "ẋ": "x", "'": "", "’": "", "ε": "a"}


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
        c["rica"] = rica(c["sentence"])
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
    #: Sense plegar: ara el millor model és el que escriu bé les lletres riques.
    dits = [rica(x) for x in proc.batch_decode(ids)]
    refs = [rica(x) for x in proc.batch_decode(et, group_tokens=False)]
    d = sum(distancia(r, h) for r, h in zip(refs, dits))
    n = sum(len(r) for r in refs)
    return {"cer": d / max(1, n)}


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


def llegeix(f, m):
    ona, _ = librosa.load(f["cami"], sr=16000, mono=True)
    ent = proc(ona, sampling_rate=16000, return_tensors="pt")
    if torch.cuda.is_available():
        ent = {k: v.cuda() for k, v in ent.items()}
    with torch.no_grad():
        ids = m(**ent).logits.argmax(-1)
    return proc.batch_decode(ids)[0].strip()


def avalua(m, etiqueta):
    """CER plegat (comparable amb les taules antigues), CER ric, i encert per lletra."""
    m.eval()
    res, sortida = {}, []
    for nom, g in proves.items():
        if not g:
            continue
        dp, np_, dr, nr = 0, 0, 0, 0
        or_ = collections.Counter(); dit_ = collections.Counter(); be = collections.Counter()
        for f in g:
            ric_or = f.get("rica") or rica(f.get("text_original")) or rica(f["lletra"])
            cru = llegeix(f, m)
            ric = rica(cru)
            dp += distancia(f["lletra"], a_llati(cru)); np_ += len(f["lletra"])
            dr += distancia(ric_or, ric); nr += len(ric_or)
            or_.update(c for c in ric_or if c in LLETRES_RIQUES)
            dit_.update(c for c in ric if c in LLETRES_RIQUES)
            sm = difflib.SequenceMatcher(None, ric_or, ric, autojunk=False)
            for bl in sm.get_matching_blocks():
                be.update(c for c in ric_or[bl.a:bl.a + bl.size] if c in LLETRES_RIQUES)
            sortida.append({"split": nom, "fitxer": f["fitxer"], "or": ric_or, "dit": ric})
        lletres = {c: {"or": or_[c], "dit": dit_[c], "be": be[c]} for c in LLETRES_RIQUES}
        res[nom] = {"cer_plegat": dp / max(1, np_), "cer_ric": dr / max(1, nr), "lletres": lletres}
        print(etiqueta, nom, json.dumps(res[nom], ensure_ascii=False), flush=True)
    return res, sortida


tot, sortida = {}, []
tot["afinat"], sortida = avalua(model, "afinat")
del entrenador, model
torch.cuda.empty_cache()
base = AutoModelForCTC.from_pretrained(BASE, ignore_mismatched_sizes=True)
base.load_adapter(LLENGUA)
if torch.cuda.is_available():
    base = base.cuda()
tot["base"], _ = avalua(base, "base")
json.dump(tot, open("/kaggle/working/resultat_ric_%s.json" % FILTRE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(sortida, open("/kaggle/working/prova_ric_%s.json" % FILTRE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
