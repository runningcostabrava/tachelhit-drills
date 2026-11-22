# H5 (#452, #620; 16-11-2026): afinar l'adaptador `shi` amb LES NOSTRES VEUS i la veritat humana de Zouhir alhora.
# Es parteix de l'adaptador H4b (el que serveix al Space des del 16-11), i s'hi afegeix el corpus propi
# (`corpus_v4.json`: la biblioteca rescatada, 4.016 parelles de train amb el text tal com el va escriure
# qui parla; Beni Mellal, MTNRA, el CD del Mètode, Halima i Driss) més els rètols nets de Zouhir i l'Alcorà.
# Mateixa recepta que H4/H4b (només adaptadors, cap congelat, gradient no reentrant, objectiu ric).
# Mesura abans → després, mateixos talls i mateixa regla, sobre SIS tests:
#   test-fora (fonts senceres mai sentides, la nostra parla), test-dins (targetes de Beni Mellal noves),
#   cv-zgh-test (256 clips nets del Common Voice), tfa-226 (taixelhit dels contes), zouhir-fora, quran-fora.
# Permís dels autors de Zouhir, l'Alcorà, aslmdtv i TFA: docs/PERMISOS.md (16-11-2026). El corpus propi no es publica.

EPOQUES = 3
LOT = 4
RITME = 1e-4
SEGONS_MAXIM = 14
FORA_ZOUHIR = ["RzG-vYOY2L8", "24EkU437k1s", "srnE-hORsio", "ENmpd74ODGo"]
FORA_QURAN = ["ROl7INibBdg", "f3bUnaPrGYY", "4YoU1icL8zY"]
DESPLAÇATS = {"DPJrHx2meXE", "QiR0qrnYV0g", "stQPF2-LrB4"}
CANTATS = {"AxhxhfJeG60"}
DEV_MAXIM = 240

import os, subprocess, sys
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44", "librosa", "soundfile", "accelerate"], check=False)

import collections, difflib, json, random, re, time, unicodedata
import numpy as np, torch, librosa


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


TIF_RIC = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k", "ⵀ": "h", "ⵃ": "ḥ", "ⵄ": "ε",
           "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l", "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ",
           "ⵙ": "s", "ⵚ": "ṣ", "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w"}
LLATI_RIC = {"ɣ": "ġ", "γ": "ġ", "ɛ": "ε", "ṛ": "r", "c": "š", "x": "ḫ", "χ": "ḫ", "ž": "j", "ǧ": "j", "ʷ": "w", "v": "f", "p": "b", "o": "u"}
PLEGA = {"ġ": "g", "ε": "a", "ḥ": "h", "ḫ": "x", "ḍ": "d", "ṭ": "t", "ẓ": "z", "ṣ": "s", "š": "c"}
LLETRES_RIQUES = "ġεḥḍṭṣẓ"
ARAB, TIFINAG = re.compile("[؀-ۿ]"), re.compile("[ⴰ-⵿]")


def rica(t):
    t = unicodedata.normalize("NFC", (t or "")).strip().lower()
    t = "".join(TIF_RIC.get(c, c) for c in t)
    t = "".join(LLATI_RIC.get(c, c) for c in t)
    t = re.sub(r"[^a-zġεḥḍṭṣẓḫš ]+", "", t)
    return re.sub(r" +", " ", t).strip()


def plega(t):
    return "".join(PLEGA.get(c, c) for c in t)


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


# ---------------------------------------------------------------- les dades
SR = 16000
CORPUS = de_kaggle("corpus_v4.json") or de_kaggle("corpus_v3.json")
CV = de_kaggle("cv_test.json")
CUES = de_kaggle("cues.json")
TFA = de_kaggle("veritat_parlat.json")
ADAPT = de_kaggle("adaptador_shi_zouhir_b.pt")
assert CORPUS and CV and CUES and TFA and ADAPT, (CORPUS, CV, CUES, TFA, ADAPT)
D_C, D_CV, D_Z, D_T = (os.path.dirname(x) for x in (CORPUS, CV, CUES, TFA))

#: Un ítem és {"rica": text, "cami": fitxer sencer} o {"rica": text, "ona": tall en memòria}; `meta` per a la sortida.
def del_corpus():
    files = json.load(open(CORPUS, encoding="utf-8"))
    fora = []
    for f in files:
        cami = os.path.join(D_C, "audio", f["fitxer"])
        t = rica(f.get("text_original")) or rica(f.get("lletra"))
        if not t or not os.path.exists(cami) or not f.get("lletra"):
            continue
        fora.append({"rica": t, "cami": cami, "split": f["split"], "meta": {"video": f.get("font", ""), "de": f["fitxer"]}})
    return fora


corpus = del_corpus()
train = [x for x in corpus if x["split"] == "train"]
dev = [x for x in corpus if x["split"].startswith("dev")]
proves = {s: [x for x in corpus if x["split"] == s] for s in ("test-dins", "test-fora")}
cv = json.load(open(CV, encoding="utf-8"))
proves["cv-zgh-test"] = [{"rica": rica(c["sentence"]), "cami": os.path.join(D_CV, "audio", c["fitxer"]), "meta": {"video": "cv", "de": c["fitxer"]}}
                         for c in cv if rica(c["sentence"]) and os.path.exists(os.path.join(D_CV, "audio", c["fitxer"]))]


def es_retol(c):
    return len(c["veritat"].split()) <= 2 and (c["a"] - c["de"]) >= 2.5


def neta(c):
    return not ARAB.search(c["veritat"]) and not TIFINAG.search(c["veritat"]) and c["video"] not in DESPLAÇATS


def talla(carpeta, items):
    fora, cau = [], {}
    for it in sorted(items, key=lambda x: x["video"]):
        if it["video"] not in cau:
            cau.clear()
            cau[it["video"]], _ = librosa.load(os.path.join(carpeta, it["video"] + ".wav"), sr=SR, mono=True)
        w = cau[it["video"]]
        a, b = max(0, int((it["de"] - 0.1) * SR)), min(len(w), int((it["a"] + 0.1) * SR))
        if b - a < SR // 4 or (b - a) > SEGONS_MAXIM * SR:
            continue
        t = rica(it["veritat"])
        if not t:
            continue
        fora.append({"rica": t, "ona": w[a:b].copy(), "meta": {"video": it["video"], "de": it["de"]}})
    return fora


cues = [c for c in json.load(open(CUES, encoding="utf-8")) if neta(c) and not es_retol(c)]
FORA = set(FORA_ZOUHIR) | set(FORA_QURAN)
t0 = time.time()
z_train = talla(D_Z, [c for c in cues if c["video"] not in FORA and c["video"] not in CANTATS])
proves["zouhir-fora"] = talla(D_Z, [c for c in cues if c["video"] in FORA_ZOUHIR])
proves["quran-fora"] = talla(D_Z, [c for c in cues if c["video"] in FORA_QURAN])
proves["tfa-226"] = talla(D_T, json.load(open(TFA, encoding="utf-8")))
random.Random(1114).shuffle(z_train)
dev += z_train[:60]
train += z_train[60:]
random.Random(1114).shuffle(train)
random.Random(1114).shuffle(dev)
dev = dev[:DEV_MAXIM]
print(f"entrenen {len(train)} ({len(train) - len(z_train) + 60} propis + {len(z_train) - 60} de Zouhir/Alcorà) · dev {len(dev)} · "
      + " · ".join(f"{k} {len(v)}" for k, v in proves.items()) + f" · talls en {time.time() - t0:.0f} s", flush=True)

# ---------------------------------------------------------------- el model, partint de l'H4b
from transformers import AutoModelForCTC, AutoProcessor, Trainer, TrainingArguments
BASE, LLENGUA = "facebook/mms-1b-all", "shi"
proc = AutoProcessor.from_pretrained(BASE)
proc.tokenizer.set_target_lang(LLENGUA)
model = AutoModelForCTC.from_pretrained(BASE, ctc_loss_reduction="mean", ignore_mismatched_sizes=True)
model.load_adapter(LLENGUA)
ad = torch.load(ADAPT, map_location="cpu")
assert not model.load_state_dict(ad, strict=False).unexpected_keys
model.freeze_base_model()
for nom_p, p in model._get_adapters().items():
    p.requires_grad = not nom_p.startswith("lm_head")
mou = sum(p.numel() for p in model.parameters() if p.requires_grad)
tot = sum(p.numel() for p in model.parameters())
print("es mouen %.1f M de %.0f M (%.2f%%)" % (mou / 1e6, tot / 1e6, 100.0 * mou / tot))
assert 0 < mou < tot * 0.2
model.enable_input_require_grads()
model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
vocab = set(proc.tokenizer.get_vocab())
print("lletres que l'alfabet shi no té:", dict(collections.Counter(c for x in train for c in x["rica"] if c not in vocab and c != " ").most_common(8)) or "cap")


def ona_de(x):
    if "ona" in x:
        return x["ona"]
    w, _ = librosa.load(x["cami"], sr=SR, mono=True)
    return w[:int(SEGONS_MAXIM * SR)]


class Talls(torch.utils.data.Dataset):
    def __init__(self, xs):
        self.xs = xs

    def __len__(self):
        return len(self.xs)

    def __getitem__(self, i):
        x = self.xs[i]
        return {"input_values": proc(ona_de(x), sampling_rate=SR).input_values[0], "labels": proc.tokenizer(x["rica"]).input_ids}


def ajunta(lot):
    x = proc.pad([{"input_values": b["input_values"]} for b in lot], padding=True, return_tensors="pt")
    y = proc.tokenizer.pad([{"input_ids": b["labels"]} for b in lot], padding=True, return_tensors="pt")
    x["labels"] = y["input_ids"].masked_fill(y.attention_mask.ne(1), -100)
    return x


def mesura(pred):
    ids = np.argmax(pred.predictions, axis=-1)
    et = pred.label_ids
    et[et == -100] = proc.tokenizer.pad_token_id
    dits = [rica(x) for x in proc.batch_decode(ids)]
    refs = [rica(x) for x in proc.batch_decode(et, group_tokens=False)]
    return {"cer": sum(distancia(r, h) for r, h in zip(refs, dits)) / max(1, sum(len(r) for r in refs))}


def avalua(m, etiqueta):
    m.eval()
    dev_ = "cuda" if torch.cuda.is_available() else "cpu"
    m.to(dev_)
    res, sortida = {}, []
    for nom, g in proves.items():
        dr = nr = dp = np_ = 0
        or_, dit_, be = collections.Counter(), collections.Counter(), collections.Counter()
        for x in g:
            t = x["rica"]
            ent = proc(ona_de(x), sampling_rate=SR, return_tensors="pt").to(dev_)
            with torch.no_grad():
                ids = m(**ent).logits.argmax(-1)
            dit = rica(proc.batch_decode(ids)[0])
            dr += distancia(t, dit); nr += len(t)
            dp += distancia(plega(t), plega(dit)); np_ += len(t)
            or_.update(c for c in t if c in LLETRES_RIQUES); dit_.update(c for c in dit if c in LLETRES_RIQUES)
            for bl in difflib.SequenceMatcher(None, t, dit, autojunk=False).get_matching_blocks():
                be.update(c for c in t[bl.a:bl.a + bl.size] if c in LLETRES_RIQUES)
            sortida.append({"prova": nom, "video": x["meta"]["video"], "de": x["meta"]["de"], "or": t, "dit": dit, "model": etiqueta})
        res[nom] = {"n": len(g), "cer_ric": dr / max(1, nr), "cer_plegat": dp / max(1, np_),
                    "lletres": {c: {"or": or_[c], "dit": dit_[c], "be": be[c]} for c in LLETRES_RIQUES}}
        print(etiqueta, nom, json.dumps({k: v for k, v in res[nom].items() if k != "lletres"}), flush=True)
    return res, sortida


tot_res = {}
tot_res["abans"], s_abans = avalua(model, "abans")     # = H4b, el que serveix avui
args = TrainingArguments(output_dir="/kaggle/working/afinat", per_device_train_batch_size=LOT, per_device_eval_batch_size=1,
                         eval_accumulation_steps=1, num_train_epochs=EPOQUES, learning_rate=RITME, warmup_steps=100,
                         fp16=torch.cuda.is_available(), logging_steps=50, eval_strategy="epoch", save_strategy="epoch",
                         save_total_limit=1, load_best_model_at_end=True, metric_for_best_model="cer", greater_is_better=False,
                         report_to=[], dataloader_num_workers=2)
ent = Trainer(model=model, args=args, train_dataset=Talls(train), eval_dataset=Talls(dev), data_collator=ajunta,
              compute_metrics=mesura, processing_class=proc.feature_extractor)
_ap = "cuda" if torch.cuda.is_available() else "cpu"
model.to(_ap).train()
_lot = ajunta([Talls(train)[i] for i in range(2)])
_s = model(input_values=_lot["input_values"].to(_ap), labels=_lot["labels"].to(_ap))
_s.loss.backward()
_n_ad = sum(float(p.grad.norm()) ** 2 for n, p in model.named_parameters() if p.grad is not None and not n.startswith("lm_head")) ** 0.5
print("norma del gradient dels adaptadors %.3e" % _n_ad)
model.zero_grad()
assert _n_ad > 0, "els adaptadors no reben gradient"
ent.train()
torch.save({k: v.cpu() for k, v in model._get_adapters().items()}, "/kaggle/working/adaptador_shi_h5.pt")
tot_res["despres"], s_despres = avalua(model, "després")
json.dump({"config": {"epoques": EPOQUES, "ritme": RITME, "train": len(train), "zouhir_train": len(z_train) - 60, "fora": sorted(FORA)},
           "resultats": tot_res}, open("/kaggle/working/h5_resultat.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(s_abans + s_despres, open("/kaggle/working/h5_sortides.json", "w", encoding="utf-8"), ensure_ascii=False)
print("fet")
