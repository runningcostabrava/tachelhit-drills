# Entrenar amb talls SENCERS contra entrenar amb talls RETALLATS. La mateixa recepta, el
# mateix material, el mateix test: l'única cosa que canvia és el so.
#
# Per què: l'alineació forçada diu que **el 51 % del so dels nostres talls no és la frase**
# (DESXIFRAT §45). Mesurat sobre 245 talls amb un model JA ENTRENAT, retallar baixa el CER de
# 1,0818 a 0,8583 — **−0,2235**, i millora en 188 dels 245 (77 %).
#
# El que això NO diu és si **entrenar** amb talls retallats dona un model millor. És molt
# probable (si mig clip és una altra persona parlant, el model aprèn a casar so equivocat amb
# text) però no està provat, i aquest projecte ja ha tingut prou hipòtesis raonables que eren
# falses: el 1080p, els 58 capítols collibles, «almenys serveix per a la biblioteca».
#
# La recepta és la de `h4b-afina-shi-net`: MMS-1b-all amb l'adaptador `shi`, només els
# adaptadors es mouen, objectiu ric, gradient no reentrant.
#
# **Les dues cares comparteixen el test, i el test va SENCER a totes dues.** El que es compara
# és quin entrenament dona el millor model, no quin test és més fàcil. Un test retallat
# afavoriria la cara retallada i el número no voldria dir res.
#
# Material de tercers (SNRT): això només mesura. Cap adaptador que en surti es desplega.

EPOQUES = 4
LOT = 4
RITME = 1e-4          # continuem un adaptador ja afinat, com a h4b
SEGONS_MAXIM = 14
LLAVOR = 1114

import os
import subprocess
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U",
                "transformers>=4.44", "librosa", "soundfile"], check=False)

import collections
import json
import random
import time
import unicodedata

import numpy as np
import soundfile as sf
import torch

SR = 16000
BASE, LLENGUA = "facebook/mms-1b-all", "shi"


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    raise FileNotFoundError(nom)


def carpeta_de(cara):
    """La carpeta `so` de la cara demanada, dins del conjunt de dades pujat."""
    for arrel, dirs, _ in os.walk("/kaggle/input"):
        if os.path.basename(arrel) == cara and "so" in dirs:
            return os.path.join(arrel, "so")
    raise FileNotFoundError(f"no trobo la carpeta {cara}/so")


# ------------------------------------------------------------------ l'alfabet ric, com a h4b
TIF_RIC = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k",
           "ⵀ": "h", "ⵃ": "ḥ", "ⵄ": "ε", "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l",
           "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ", "ⵙ": "s", "ⵚ": "ṣ",
           "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w",
           "ⵒ": "p", "ⴶ": "g", "ⵌ": "j"}
PLEGA = {"ġ": "g", "ε": "a", "ḥ": "h", "ḫ": "x", "ḍ": "d", "ṭ": "t", "ẓ": "z", "ṣ": "s"}
LLETRES_RIQUES = "ġεḥḍṭṣẓ"


def rica(t):
    """Tifinag -> llatí ric. El mateix mapa que h4b, perquè els números siguin comparables."""
    fora = []
    for c in (t or ""):
        if c in TIF_RIC:
            fora.append(TIF_RIC[c])
        elif c.isspace():
            fora.append(" ")
        else:
            d = unicodedata.normalize("NFD", c)
            b = "".join(x for x in d if not unicodedata.combining(x))
            if b.isascii() and b.isalpha():
                fora.append(b.lower())
    return " ".join("".join(fora).split())


def plega(t):
    return "".join(PLEGA.get(c, c) for c in t)


def distancia(a, b):
    if not a:
        return len(b)
    d = list(range(len(b) + 1))
    for i, c in enumerate(a, 1):
        nd = [i]
        for j, k in enumerate(b, 1):
            nd.append(min(d[j] + 1, nd[j - 1] + 1, d[j - 1] + (c != k)))
        d = nd
    return d[-1]


# ------------------------------------------------------------------------------ el material
def llegeix(cara, part):
    """[(ona, text ric, meta)] d'una cara i una partició."""
    so = carpeta_de(cara)
    fitxa = de_kaggle(f"{part}.jsonl") if cara == "sencer" else None
    #: cada cara porta els seus jsonl al costat de `so`
    p = os.path.join(os.path.dirname(so), f"{part}.jsonl")
    if not os.path.exists(p):
        p = fitxa
    fora = []
    for l in open(p, encoding="utf-8"):
        if not l.strip():
            continue
        r = json.loads(l)
        w = os.path.join(so, r["so"])
        if not os.path.exists(w):
            continue
        x, sr = sf.read(w, dtype="float32")
        if x.ndim > 1:
            x = x.mean(axis=1)
        if len(x) < SR // 4 or len(x) > SEGONS_MAXIM * SR:
            continue
        t = rica(r["zgh"])
        if not t:
            continue
        fora.append((x, t, r))
    return fora


print("carregant el material…", flush=True)
t0 = time.time()
material = {}
for cara in ("sencer", "retallat"):
    material[cara] = {p: llegeix(cara, p) for p in ("train", "dev", "test")}
    d = {p: len(v) for p, v in material[cara].items()}
    h = sum(len(x[0]) for v in material[cara].values() for x in v) / SR / 3600
    print(f"   {cara}: {d} · {h:.2f} h", flush=True)

#: El filtre de durada de `llegeix()` (mínim 0,25 s, màxim SEGONS_MAXIM) s'aplica a cada cara
#: per separat, i un tall de 14,2 s sencer en fa 13,8 retallat: la cara retallada se'l queda i
#: la sencera no. Provat en local el 22-11, les dues cares es diferenciaven en una fila.
#:
#: Per tant es QUEDEN NOMÉS els talls que han passat el filtre a les DUES cares. Si no,
#: l'experiment no compararia el retall: compararia dos corpus que no són el mateix.
for p in ("train", "dev", "test"):
    comuns = {x[2]["so"] for x in material["sencer"][p]} & {x[2]["so"] for x in material["retallat"][p]}
    fora = sum(len(material[c][p]) for c in ("sencer", "retallat")) - 2 * len(comuns)
    for c in ("sencer", "retallat"):
        material[c][p] = [x for x in material[c][p] if x[2]["so"] in comuns]
    if fora:
        print(f"   {p}: {fora} talls fora, que no passaven el filtre a totes dues cares")

for p in ("train", "dev", "test"):
    a = [x[2]["so"] for x in material["sencer"][p]]
    b = [x[2]["so"] for x in material["retallat"][p]]
    assert a == b, f"les dues cares no tenen les mateixes files a {p}: {len(a)} contra {len(b)}"
print("   les dues cares tenen les mateixes files: es compara NOMÉS el retall")

#: El test va SENCER a totes dues cares. Si es retallés, la cara retallada hi jugaria a casa.
TEST = material["sencer"]["test"]
print(f"   test (sencer per a totes dues): {len(TEST)} talls", flush=True)
print(f"   carregat en {time.time()-t0:.0f} s")

# ---------------------------------------------------------------------------------- el model
from transformers import AutoModelForCTC, AutoProcessor, Trainer, TrainingArguments  # noqa: E402

proc = AutoProcessor.from_pretrained(BASE)
proc.tokenizer.set_target_lang(LLENGUA)
DISP = "cuda" if torch.cuda.is_available() else "cpu"


def carrega():
    m = AutoModelForCTC.from_pretrained(BASE, ctc_loss_reduction="mean",
                                        ignore_mismatched_sizes=True)
    m.load_adapter(LLENGUA)
    m.freeze_base_model()
    for nom_p, p in m._get_adapters().items():
        p.requires_grad = not nom_p.startswith("lm_head")
    mou = sum(p.numel() for p in m.parameters() if p.requires_grad)
    tot = sum(p.numel() for p in m.parameters())
    assert 0 < mou < tot * 0.2, (mou, tot)
    m.enable_input_require_grads()
    m.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    return m


class Talls(torch.utils.data.Dataset):
    def __init__(self, xs):
        self.xs = xs

    def __len__(self):
        return len(self.xs)

    def __getitem__(self, i):
        ona, t, _ = self.xs[i]
        return {"input_values": proc(ona, sampling_rate=SR).input_values[0],
                "labels": proc.tokenizer(t).input_ids}


def ajunta(lot):
    x = proc.pad([{"input_values": b["input_values"]} for b in lot], padding=True,
                 return_tensors="pt")
    y = proc.tokenizer.pad([{"input_ids": b["labels"]} for b in lot], padding=True,
                           return_tensors="pt")
    x["labels"] = y["input_ids"].masked_fill(y.attention_mask.ne(1), -100)
    return x


def mesura(pred):
    ids = np.argmax(pred.predictions, axis=-1)
    et = pred.label_ids
    et[et == -100] = proc.tokenizer.pad_token_id
    dits = [rica(x) for x in proc.batch_decode(ids)]
    refs = [rica(x) for x in proc.batch_decode(et, group_tokens=False)]
    return {"cer": sum(distancia(r, h) for r, h in zip(refs, dits))
            / max(1, sum(len(r) for r in refs))}


def avalua(m, etiqueta):
    """Sempre sobre TEST, que va sencer: el mateix jutge per a les dues cares."""
    m.eval().to(DISP)
    dr = nr = dp = np_ = 0
    sortida = []
    for ona, t, meta in TEST:
        ent = proc(ona, sampling_rate=SR, return_tensors="pt").to(DISP)
        with torch.no_grad():
            ids = m(**ent).logits.argmax(-1)
        dit = rica(proc.batch_decode(ids)[0])
        dr += distancia(t, dit)
        nr += len(t)
        dp += distancia(plega(t), plega(dit))
        np_ += len(t)
        sortida.append({"so": meta["so"], "capitol": meta["capitol"], "or": t, "dit": dit})
    r = {"n": len(TEST), "cer_ric": dr / max(1, nr), "cer_plegat": dp / max(1, np_)}
    print(f"   {etiqueta}: {json.dumps(r)}", flush=True)
    return r, sortida


def entrena(cara):
    print(f"\n===== {cara.upper()} =====", flush=True)
    m = carrega()
    random.Random(LLAVOR).seed(LLAVOR)
    args = TrainingArguments(
        output_dir=f"/kaggle/working/{cara}", per_device_train_batch_size=LOT,
        per_device_eval_batch_size=LOT, eval_accumulation_steps=1,
        num_train_epochs=EPOQUES, learning_rate=RITME, warmup_ratio=0.1,
        fp16=torch.cuda.is_available(), logging_steps=50, eval_strategy="epoch",
        save_strategy="epoch", save_total_limit=1, load_best_model_at_end=True,
        metric_for_best_model="cer", greater_is_better=False, seed=LLAVOR,
        gradient_checkpointing=True, report_to=[])
    ent = Trainer(model=m, args=args, train_dataset=Talls(material[cara]["train"]),
                  eval_dataset=Talls(material[cara]["dev"]), data_collator=ajunta,
                  compute_metrics=mesura, processing_class=proc.feature_extractor)
    ent.train()
    return avalua(m, f"{cara} (entrenat)")


resultats = {}
print("\n--- el punt de partida: l'adaptador de fàbrica, sense entrenar", flush=True)
resultats["abans"], _ = avalua(carrega(), "abans")

for cara in ("sencer", "retallat"):
    resultats[cara], sortida = entrena(cara)
    json.dump(sortida, open(f"/kaggle/working/sortida_{cara}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

a = resultats["sencer"]["cer_ric"]
b = resultats["retallat"]["cer_ric"]
print("\n================ EL RESULTAT ================")
print(f"   sense entrenar      CER {resultats['abans']['cer_ric']:.4f}")
print(f"   entrenat amb SENCERS   CER {a:.4f}")
print(f"   entrenat amb RETALLATS CER {b:.4f}")
print(f"   diferència             {b-a:+.4f}  ({100*(b-a)/max(a,1e-9):+.1f} %)")
print("   (el test va sencer a totes dues: es compara l'entrenament, no el test)")
json.dump(resultats, open("/kaggle/working/resultats.json", "w", encoding="utf-8"), indent=1)
