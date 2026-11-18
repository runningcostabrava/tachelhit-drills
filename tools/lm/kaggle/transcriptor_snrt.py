# Transcriptor SNRT (#601, §6.5): afinar l'adaptador MMS `shi` (H4b, el que serveix al Space) amb parelles so <-> tifinag
# de Tamazight TV (SNRT), llegides per la fàbrica de l'ECS. Material de RECERCA: el model que en surti no es publica
# ni es desplega (docs/PERMISOS.md, 17-11-2026).
#
# El llança `tools/lm/transcriptor_bucle.py`, que posa la recepta a la línia de sota abans de pujar el nucli:
#   RECEPTA = "A"  -> train = només SNRT (rèpliques aptes amb CER <= 0,4 de l'adaptador actual)
#   RECEPTA = "B"  -> train = SNRT + les dades d'H4b (rètols nets de Zouhir i l'Alcorà)
#   RECEPTA = "C"  -> train = només les rèpliques SNRT més netes: confiança >= 0,95, durada 2-6 s, <= 18 lletres/s, les 200 de més
#                     confiança (desempat a l'atzar, llavor 1114); mateix ritme que A per aïllar l'efecte de la neteja de les dades
# Mateixa recepta que H4b: només els adaptadors, cap congelat, gradient no reentrant, objectiu ric (sense plegar).
# Mesura «abans -> després», mateixos talls i mateixa regla, sobre cinc proves:
#   cv-zgh-test (256 clips nets), test-fora (la nostra parla mai sentida), tfa-226, zouhir-fora, snrt-retingut
#   (capítols SENCERS que no entrenen; sense el filtre de CER, perquè el filtre és de l'ASR actual i afavoriria el test).
# FILTRE_CER (§5, CER <= 0,4 de l'adaptador actual contra el tifinag): None = apagat. El 17-11 es va mesurar que a Tadfi n Tskla només
# passa el 0,9 % dels talls (4 de 466; CER mediana 0,83 perquè el tifinag de la SNRT no escriu els vocals neutres i l'ASR en
# posa), de manera que el filtre buida el train. Canviar un llindar de §5 és decisió del director: de moment va apagat i
# l'informe diu què passaria amb ell.
# La fuita es tanca per text: tot el que a train coincideix (text ric) amb qualsevol prova se'n treu.
RECEPTA = "A"
FILTRE_CER = None
EPOQUES = 4
LOT = 4
RITME = 1e-4
SEGONS_MAXIM = 14
FORA_ZOUHIR = ["RzG-vYOY2L8", "24EkU437k1s", "srnE-hORsio", "ENmpd74ODGo"]
FORA_QURAN = ["ROl7INibBdg", "f3bUnaPrGYY", "4YoU1icL8zY"]
DESPLAÇATS = {"DPJrHx2meXE", "QiR0qrnYV0g", "stQPF2-LrB4"}
CANTATS = {"AxhxhfJeG60"}

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
ROWS = de_kaggle("rows.json")
CORPUS = de_kaggle("corpus_v4.json") or de_kaggle("corpus_v3.json")
CV = de_kaggle("cv_test.json")
CUES = de_kaggle("cues.json")
TFA = de_kaggle("veritat_parlat.json")
ADAPT = de_kaggle("adaptador_shi_zouhir_b.pt")
assert ROWS and CORPUS and CV and CUES and TFA and ADAPT, (ROWS, CORPUS, CV, CUES, TFA, ADAPT)
D_S, D_C, D_CV, D_Z, D_T = (os.path.dirname(x) for x in (ROWS, CORPUS, CV, CUES, TFA))


def snrt(split):
    fora = []
    for r in json.load(open(ROWS, encoding="utf-8")):
        if r["split"] != split:
            continue
        cami = os.path.join(D_S, r["fitxer"])
        t = rica(r["tifinag"])
        if t and os.path.exists(cami):
            fora.append({"rica": t, "cami": cami, "meta": {"video": r["slug"], "de": r["id"]}, "conf": r.get("conf") or 0, "durada": r["durada"]})
    return fora


train_s, dev_s, test_s = snrt("train"), snrt("dev"), snrt("test")
if RECEPTA == "C":
    _net = [x for x in train_s if x["conf"] >= 0.95 and 2 <= x["durada"] <= 6 and len(x["rica"]) / x["durada"] <= 18]
    random.Random(1114).shuffle(_net)
    train_s = sorted(_net, key=lambda x: -x["conf"])[:200]
    print(f"recepta C: {len(train_s)} rèpliques netes", flush=True)
corpus = json.load(open(CORPUS, encoding="utf-8"))
proves = {"snrt-retingut": test_s}
fora_c = []
for f in corpus:
    cami = os.path.join(D_C, "audio", f["fitxer"])
    t = rica(f.get("text_original")) or rica(f.get("lletra"))
    if f["split"] == "test-fora" and t and os.path.exists(cami) and f.get("lletra"):
        fora_c.append({"rica": t, "cami": cami, "meta": {"video": f.get("font", ""), "de": f["fitxer"]}})
proves["test-fora"] = fora_c
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
        if t:
            fora.append({"rica": t, "ona": w[a:b].copy(), "meta": {"video": it["video"], "de": it["de"]}})
    return fora


cues = [c for c in json.load(open(CUES, encoding="utf-8")) if neta(c) and not es_retol(c)]
FORA = set(FORA_ZOUHIR) | set(FORA_QURAN)
t0 = time.time()
proves["zouhir-tests"] = talla(D_Z, [c for c in cues if c["video"] in FORA_ZOUHIR])
proves["tfa-226"] = talla(D_T, json.load(open(TFA, encoding="utf-8")))
z_train = talla(D_Z, [c for c in cues if c["video"] not in FORA and c["video"] not in CANTATS]) if RECEPTA == "B" else []
print(f"recepta {RECEPTA} · snrt train {len(train_s)} dev {len(dev_s)} test {len(test_s)} · zouhir train {len(z_train)} · "
      + " · ".join(f"{k} {len(v)}" for k, v in proves.items()) + f" · talls en {time.time() - t0:.0f} s", flush=True)

# fuita: res del train no pot coincidir (text ric) amb cap prova
texts_prova = {x["rica"] for g in proves.values() for x in g}
n0 = len(train_s) + len(z_train)
train_s = [x for x in train_s if x["rica"] not in texts_prova]
z_train = [x for x in z_train if x["rica"] not in texts_prova]
dev_s = [x for x in dev_s if x["rica"] not in texts_prova]
fuita = n0 - len(train_s) - len(z_train)
print(f"fuita treta del train per text: {fuita}", flush=True)

# ---------------------------------------------------------------- el model, partint d'H4b
from transformers import AutoModelForCTC, AutoProcessor, Trainer, TrainingArguments
BASE, LLENGUA = "facebook/mms-1b-all", "shi"
proc = AutoProcessor.from_pretrained(BASE)
proc.tokenizer.set_target_lang(LLENGUA)
model = AutoModelForCTC.from_pretrained(BASE, ctc_loss_reduction="mean", ignore_mismatched_sizes=True)
model.load_adapter(LLENGUA)
ad = torch.load(ADAPT, map_location="cpu")
assert not model.load_state_dict(ad, strict=False).unexpected_keys
dev_gpu = "cuda" if torch.cuda.is_available() else "cpu"


def ona_de(x):
    if "ona" in x:
        return x["ona"]
    w, _ = librosa.load(x["cami"], sr=SR, mono=True)
    return w[:int(SEGONS_MAXIM * SR)]


def transcriu(m, g):
    m.eval()
    m.to(dev_gpu)
    sortida = []
    for x in g:
        ent = proc(ona_de(x), sampling_rate=SR, return_tensors="pt").to(dev_gpu)
        with torch.no_grad():
            ids = m(**ent).logits.argmax(-1)
        sortida.append(rica(proc.batch_decode(ids)[0]))
    return sortida


def avalua(m, etiqueta):
    res, sortida = {}, []
    for nom, g in proves.items():
        dits = transcriu(m, g)
        dr = nr = dp = np_ = 0
        or_, dit_, be = collections.Counter(), collections.Counter(), collections.Counter()
        for x, dit in zip(g, dits):
            t = x["rica"]
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
tot_res["abans"], s_abans = avalua(model, "abans")      # l'adaptador que serveix avui

# filtre §5: CER <= 0,4 de l'ASR actual contra el tifinag llegit (treu els subtítols que resumeixen)
def filtra(g, nom, llindar):
    dits = transcriu(model, g)
    cers = [distancia(x["rica"], d) / max(1, len(x["rica"])) for x, d in zip(g, dits)]
    bons = [x for x, c in zip(g, cers) if c <= llindar]
    cers_s = sorted(cers)
    med = cers_s[len(cers_s) // 2] if cers_s else None
    print(f"filtre CER<={llindar} {nom}: {len(bons)} de {len(g)} · CER mitjana per tall mediana {med}", flush=True)
    return bons, {"abans": len(g), "despres": len(bons), "mediana_cer": med}


if FILTRE_CER is None:
    # sense filtre: només es mesura quants passarien, per a l'informe
    _, f_train = filtra(train_s, "train (només comptar)", 0.4)
    _, f_dev = filtra(dev_s, "dev (només comptar)", 0.4)
else:
    train_s, f_train = filtra(train_s, "train", FILTRE_CER)
    dev_s, f_dev = filtra(dev_s, "dev", FILTRE_CER)
segons = lambda g: sum(len(ona_de(x)) for x in g) / SR
h_train = (sum(len(ona_de(x)) for x in train_s) / SR + sum(len(x["ona"]) for x in z_train) / SR) / 3600
train = train_s + z_train
random.Random(1114).shuffle(train)
dev = dev_s[:240]
print(f"entrenen {len(train)} ({len(train_s)} SNRT + {len(z_train)} Zouhir/Alcorà; {h_train:.2f} h) · dev {len(dev)}", flush=True)
assert len(train) >= 100 and len(dev) >= 20, "massa poques dades"

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


args = TrainingArguments(output_dir="/kaggle/working/afinat", per_device_train_batch_size=LOT, per_device_eval_batch_size=1,
                         eval_accumulation_steps=1, num_train_epochs=EPOQUES, learning_rate=RITME, warmup_steps=60,
                         fp16=torch.cuda.is_available(), logging_steps=50, eval_strategy="epoch", save_strategy="epoch",
                         save_total_limit=1, load_best_model_at_end=True, metric_for_best_model="cer", greater_is_better=False,
                         report_to=[], dataloader_num_workers=2)
ent = Trainer(model=model, args=args, train_dataset=Talls(train), eval_dataset=Talls(dev), data_collator=ajunta,
              compute_metrics=mesura, processing_class=proc.feature_extractor)
model.to(dev_gpu).train()
_lot = ajunta([Talls(train)[i] for i in range(2)])
_s = model(input_values=_lot["input_values"].to(dev_gpu), labels=_lot["labels"].to(dev_gpu))
_s.loss.backward()
_n_ad = sum(float(p.grad.norm()) ** 2 for n, p in model.named_parameters() if p.grad is not None and not n.startswith("lm_head")) ** 0.5
print("norma del gradient dels adaptadors %.3e" % _n_ad)
model.zero_grad()
assert _n_ad > 0, "els adaptadors no reben gradient"
t1 = time.time()
ent.train()
print(f"entrenat en {time.time() - t1:.0f} s", flush=True)
torch.save({k: v.cpu() for k, v in model._get_adapters().items()}, f"/kaggle/working/adaptador_shi_snrt_{RECEPTA}.pt")
tot_res["despres"], s_despres = avalua(model, "després")
json.dump({"config": {"recepta": RECEPTA, "epoques": EPOQUES, "ritme": RITME, "filtre_cer": FILTRE_CER, "train": len(train),
                      "train_snrt": len(train_s), "train_zouhir": len(z_train), "hores_train": h_train, "dev": len(dev),
                      "fuita_treta": fuita, "filtre_train": f_train, "filtre_dev": f_dev},
           "resultats": tot_res}, open(f"/kaggle/working/snrt_{RECEPTA}_resultat.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(s_abans + s_despres, open(f"/kaggle/working/snrt_{RECEPTA}_sortides.json", "w", encoding="utf-8"), ensure_ascii=False)
print("fet")
