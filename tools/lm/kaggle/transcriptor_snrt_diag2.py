# Diagnòstic 2 del transcriptor SNRT (#601). La recepta A (afinar amb 782 rèpliques de la SNRT, 1,05 h) va ensorrar totes les
# proves i la pèrdua CTC no va baixar de 2,9 en 4 èpoques: el tifinag no descriu el que se sent al tall, o descriu una cosa que
# l'adaptador no pot aprendre. Aquí es mesura quina de les dues, amb la pèrdua CTC per lletra del text de referència:
#   (a) parella tal com la dona la fàbrica; (b) el text d'una altra fila del mateix capítol (control negatiu: l'àudio no el diu);
#   (c) el mateix text amb la finestra d'àudio desplaçada ±1 s; (d) el text amb els «vocals neutres» que el tifinag no escriu
#   afegits en pla (no es pot): no es fa; (e) calibratge: els mateixos números a Common Voice zgh (parella bona coneguda).
# Si (a) ≈ (b): l'àudio i el text NO són parella (dades dolentes). Si (a) << (b) però alta respecte de CV: la parella és real i el
# text és difícil d'aprendre (ortografia sense vocals, parla de conversa), i el problema és de l'objectiu, no de les dades.
import os, subprocess, sys
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.44", "librosa", "soundfile", "accelerate"], check=False)
import collections, json, random, re, unicodedata
import numpy as np, torch, librosa

SR = 16000
N = 120


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


TIF_RIC = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k", "ⵀ": "h", "ⵃ": "ḥ", "ⵄ": "ε",
           "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l", "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ",
           "ⵙ": "s", "ⵚ": "ṣ", "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w"}
LLATI_RIC = {"ɣ": "ġ", "γ": "ġ", "ɛ": "ε", "ṛ": "r", "c": "š", "x": "ḫ", "χ": "ḫ", "ž": "j", "ǧ": "j", "ʷ": "w", "v": "f", "p": "b", "o": "u"}


def rica(t):
    t = unicodedata.normalize("NFC", (t or "")).strip().lower()
    t = "".join(TIF_RIC.get(c, c) for c in t)
    t = "".join(LLATI_RIC.get(c, c) for c in t)
    t = re.sub(r"[^a-zġεḥḍṭṣẓḫš ]+", "", t)
    return re.sub(r" +", " ", t).strip()


ROWS, CV, ADAPT = de_kaggle("rows.json"), de_kaggle("cv_test.json"), de_kaggle("adaptador_shi_zouhir_b.pt")
D_S, D_CV = os.path.dirname(ROWS), os.path.dirname(CV)
rows = json.load(open(ROWS, encoding="utf-8"))
for r in rows:
    r["k"] = int(r["id"].rsplit("_", 1)[1])
per = collections.defaultdict(dict)
for r in rows:
    per[r["slug"]][r["k"]] = r
cv = [c for c in json.load(open(CV, encoding="utf-8")) if rica(c["sentence"])]

from transformers import AutoModelForCTC, AutoProcessor
proc = AutoProcessor.from_pretrained("facebook/mms-1b-all")
proc.tokenizer.set_target_lang("shi")
model = AutoModelForCTC.from_pretrained("facebook/mms-1b-all", ignore_mismatched_sizes=True)
model.load_adapter("shi")
model.load_state_dict(torch.load(ADAPT, map_location="cpu"), strict=False)
dev = "cuda" if torch.cuda.is_available() else "cpu"
model.to(dev).eval()
BLANK = proc.tokenizer.pad_token_id


def perlletra(w, text):
    ids = proc.tokenizer(text).input_ids
    if not ids or len(w) < SR // 4:
        return None
    ent = proc(w[: 20 * SR], sampling_rate=SR, return_tensors="pt").to(dev)
    with torch.no_grad():
        lp = model(**ent).logits.log_softmax(-1).transpose(0, 1)
    t = torch.tensor([ids], device=dev)
    l = torch.nn.functional.ctc_loss(lp, t, torch.tensor([lp.shape[0]]), torch.tensor([len(ids)]), blank=BLANK, reduction="sum", zero_infinity=True)
    return float(l) / len(ids)


def carrega(r):
    w, _ = librosa.load(os.path.join(D_S, r["fitxer"]), sr=SR, mono=True)
    return w


rnd = random.Random(1114)
res = {}
for slug, d in sorted(per.items()):
    ks = [k for k in sorted(d) if (k - 1) in d and (k + 1) in d]
    triats = rnd.sample(ks, min(N, len(ks)))
    out = collections.defaultdict(list)
    for k in triats:
        w = carrega(d[k])
        ref = rica(d[k]["tifinag"])
        a = perlletra(w, ref)
        altre = rnd.choice([x for x in sorted(d) if x != k])
        b = perlletra(w, rica(d[altre]["tifinag"]))
        if a is None or b is None:
            continue
        out["parella"].append(a)
        out["altra_fila"].append(b)
        out["fila_anterior"].append(perlletra(w, rica(d[k - 1]["tifinag"])) or b)
        out["fila_seguent"].append(perlletra(w, rica(d[k + 1]["tifinag"])) or b)
        cont = np.concatenate([carrega(d[k - 1]), w, carrega(d[k + 1])])
        ini = len(carrega(d[k - 1]))
        for dl in (-1.0, 1.0):
            x = perlletra(cont[ini + int(dl * SR): ini + int(dl * SR) + len(w)], ref)
            if x is not None:
                out[f"temps{dl:+.0f}"].append(x)
    res[slug] = {"split": d[min(d)]["split"], **{k: (float(np.mean(v)), len(v)) for k, v in out.items()}}
    print(slug[:8], json.dumps(res[slug]), flush=True)
out = collections.defaultdict(list)
for c in rnd.sample(cv, min(N, len(cv))):
    w, _ = librosa.load(os.path.join(D_CV, "audio", c["fitxer"]), sr=SR, mono=True)
    a = perlletra(w, rica(c["sentence"]))
    b = perlletra(w, rica(rnd.choice(cv)["sentence"]))
    if a is not None and b is not None:
        out["parella"].append(a)
        out["altra_fila"].append(b)
res["cv-zgh"] = {k: (float(np.mean(v)), len(v)) for k, v in out.items()}
print("cv-zgh", json.dumps(res["cv-zgh"]), flush=True)
json.dump(res, open("/kaggle/working/diag2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("fet")
