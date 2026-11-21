# H4b (#620, 16-11): H4 amb la veritat NETA. La mesura completa del canal de l'Alcorà va mostrar que la seva
# pista barreja amazic en lletres àrabs, grafia cabilenca (ⵝ ⴺ ⵒ) i tres vídeos amb els temps desplaçats; `rica()`
# buidava l'àrab però deixava passar la grafia cabilenca (lletres esborrades) i els desplaçats. Aquí: fora tot això,
# i l'Alcorà fora són tres vídeos nets. La resta és H4 tal qual.
# H4 (#601 punt 3, #620): afinar l'adaptador `shi` amb la primera transcripció HUMANA de volum que tenim,
# els rètols de Zouhir Amazigh i BerberFreeQuranEducation (pista en tifinag a mà de l'autor, alineada
# al so). És la mateixa recepta que `afina-mms-ric-tot` (30-10: només els adaptadors, cap congelat,
# gradient no reentrant, objectiu ric), amb tres diferències:
#   1. es parteix de l'adaptador que serveix avui (`adaptador_shi_ric.pt`), no del de fàbrica;
#   2. el test que mana és el de SEMPRE: els 226 versos de Tamazight For All (taixelhit dels contes),
#      perquè l'amazic estàndard narrat de Zouhir no ens empitjori el que ja llegíem; a més, vídeos
#      sencers de Zouhir i de l'Alcorà fora de l'entrenament;
#   3. els rètols de pantalla (1-2 mots i ≥ 2,5 s, ningú no els diu) i el vídeo cantat no entrenen.
# Material de tercers: l'adaptador que en surti NO es desplega sense permís; aquí només es mesura.

EPOQUES = 4
LOT = 4
RITME = 1e-4          # continuem un adaptador ja afinat: la meitat del ritme de la primera passada
SEGONS_MAXIM = 14
FORA_ZOUHIR = ["RzG-vYOY2L8", "24EkU437k1s", "srnE-hORsio", "ENmpd74ODGo"]   # test, fora de train
FORA_QURAN = ["ROl7INibBdg", "f3bUnaPrGYY", "4YoU1icL8zY"]                  # Alcorà fora: tres vídeos NETS i alineats
DESPLAÇATS = {"DPJrHx2meXE", "QiR0qrnYV0g", "stQPF2-LrB4"}                   # temps de la pista desplaçats: fora de tot
CANTATS = {"AxhxhfJeG60"}                                                    # anaixid: fora de tot

import os, subprocess, sys
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44", "librosa", "soundfile", "accelerate"], check=False)

import collections, difflib, json, re, unicodedata, time
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


# ---------------------------------------------------------------- les dades, tallades a memòria
SR = 16000
CUES = de_kaggle("cues.json")
TFA = de_kaggle("veritat_parlat.json")
ADAPT = de_kaggle("adaptador_shi_ric.pt")
assert CUES and TFA and ADAPT, (CUES, TFA, ADAPT)
D_Z, D_T = os.path.dirname(CUES), os.path.dirname(TFA)
cues = json.load(open(CUES, encoding="utf-8"))
FORA = set(FORA_ZOUHIR) | set(FORA_QURAN)
ARAB, TIFINAG = re.compile("[\u0600-\u06ff]"), re.compile("[\u2d30-\u2d7f]")


def neta(c):
    """Veritat en llatí estàndard: ni lletres àrabs ni tifinag que el transliterador no ha sabut llegir."""
    return not ARAB.search(c["veritat"]) and not TIFINAG.search(c["veritat"]) and c["video"] not in DESPLAÇATS


n_abans = len(cues)
cues = [c for c in cues if neta(c)]
print(f"rètols nets {len(cues)} de {n_abans} (fora: àrab, altra grafia, {len(DESPLAÇATS)} vídeos desplaçats)")


def es_retol(c):
    return len(c["veritat"].split()) <= 2 and (c["a"] - c["de"]) >= 2.5


def talla(carpeta, items):
    """[(ona, text ric, meta)] — es carrega cada wav un sol cop."""
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
        fora.append((w[a:b].copy(), t, it))
    return fora


train_items = [c for c in cues if c["video"] not in FORA and c["video"] not in CANTATS and not es_retol(c)]
test_z = [c for c in cues if c["video"] in FORA_ZOUHIR and not es_retol(c)]
test_q = [c for c in cues if c["video"] in set(FORA_QURAN) and not es_retol(c)]
tfa = json.load(open(TFA, encoding="utf-8"))
t0 = time.time()
train = talla(D_Z, train_items)
proves = {"tfa-226": talla(D_T, tfa), "zouhir-fora": talla(D_Z, test_z), "quran-fora": talla(D_Z, test_q)}
#: dev: un tros de train, per triar l'època (no és cap test)
import random
random.Random(1114).shuffle(train)
dev, train = train[:120], train[120:]
print(f"entrenen {len(train)} rètols ({sum(len(x[0]) for x in train) / SR / 60:.1f} min) · dev {len(dev)} · "
      + " · ".join(f"{k} {len(v)}" for k, v in proves.items()) + f" · tallat en {time.time() - t0:.0f} s", flush=True)

# ---------------------------------------------------------------- el model, partint de l'adaptador que serveix
from transformers import AutoModelForCTC, AutoProcessor, Trainer, TrainingArguments
BASE, LLENGUA = "facebook/mms-1b-all", "shi"
proc = AutoProcessor.from_pretrained(BASE)
proc.tokenizer.set_target_lang(LLENGUA)


def carrega(amb_adaptador_nostre):
    m = AutoModelForCTC.from_pretrained(BASE, ctc_loss_reduction="mean", ignore_mismatched_sizes=True)
    m.load_adapter(LLENGUA)
    if amb_adaptador_nostre:
        ad = torch.load(ADAPT, map_location="cpu")
        falten = m.load_state_dict(ad, strict=False).unexpected_keys
        assert not falten, falten[:5]
    return m


model = carrega(True)
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
falten = collections.Counter(c for _, t, _ in train for c in t if c not in vocab and c != " ")
print("lletres que l'alfabet shi no té:", dict(falten.most_common(8)) or "cap")


class Talls(torch.utils.data.Dataset):
    def __init__(self, xs):
        self.xs = xs

    def __len__(self):
        return len(self.xs)

    def __getitem__(self, i):
        ona, t, _ = self.xs[i]
        return {"input_values": proc(ona, sampling_rate=SR).input_values[0], "labels": proc.tokenizer(t).input_ids}


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
        for ona, t, meta in g:
            ent = proc(ona, sampling_rate=SR, return_tensors="pt").to(dev_)
            with torch.no_grad():
                ids = m(**ent).logits.argmax(-1)
            dit = rica(proc.batch_decode(ids)[0])
            dr += distancia(t, dit); nr += len(t)
            dp += distancia(plega(t), plega(dit)); np_ += len(t)
            or_.update(c for c in t if c in LLETRES_RIQUES); dit_.update(c for c in dit if c in LLETRES_RIQUES)
            for bl in difflib.SequenceMatcher(None, t, dit, autojunk=False).get_matching_blocks():
                be.update(c for c in t[bl.a:bl.a + bl.size] if c in LLETRES_RIQUES)
            sortida.append({"prova": nom, "video": meta["video"], "de": meta["de"], "or": t, "dit": dit, "model": etiqueta})
        res[nom] = {"n": len(g), "cer_ric": dr / max(1, nr), "cer_plegat": dp / max(1, np_),
                    "lletres": {c: {"or": or_[c], "dit": dit_[c], "be": be[c]} for c in LLETRES_RIQUES}}
        print(etiqueta, nom, json.dumps({k: v for k, v in res[nom].items() if k != "lletres"}), flush=True)
    return res, sortida


tot_res = {}
tot_res["abans"], s_abans = avalua(model, "abans")     # l'adaptador que serveix avui, mateixos talls, mateixa regla

args = TrainingArguments(output_dir="/kaggle/working/afinat", per_device_train_batch_size=LOT, per_device_eval_batch_size=1,
                         eval_accumulation_steps=1, num_train_epochs=EPOQUES, learning_rate=RITME, warmup_steps=60,
                         fp16=torch.cuda.is_available(), logging_steps=50, eval_strategy="epoch", save_strategy="epoch",
                         save_total_limit=1, load_best_model_at_end=True, metric_for_best_model="cer", greater_is_better=False,
                         report_to=[])
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
torch.save({k: v.cpu() for k, v in model._get_adapters().items()}, "/kaggle/working/adaptador_shi_zouhir_b.pt")
tot_res["despres"], s_despres = avalua(model, "després")
json.dump({"config": {"epoques": EPOQUES, "ritme": RITME, "train": len(train), "fora": sorted(FORA)}, "resultats": tot_res},
          open("/kaggle/working/h4b_resultat.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(s_abans + s_despres, open("/kaggle/working/h4b_sortides.json", "w", encoding="utf-8"), ensure_ascii=False)
print("fet")
