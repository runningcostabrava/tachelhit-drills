# omniASR (CTC 1B i 300M, via sherpa-onnx, només CPU) sobre els conjunts de prova congelats (#601, 18-11-2026). RECERCA: no entrena res.
# Les mateixes dades i la mateixa normalització `rica` que transcriptor_snrt.py; el model actual es compara amb les sortides «abans» ja desades.
SEGONS_MAXIM = 14
FORA_ZOUHIR = ["RzG-vYOY2L8", "24EkU437k1s", "srnE-hORsio", "ENmpd74ODGo"]
FORA_QURAN = ["ROl7INibBdg", "f3bUnaPrGYY", "4YoU1icL8zY"]
DESPLAÇATS = {"DPJrHx2meXE", "QiR0qrnYV0g", "stQPF2-LrB4"}
CANTATS = {"AxhxhfJeG60"}

import os, subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "sherpa-onnx", "huggingface_hub", "librosa", "soundfile"], check=False)

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
assert CORPUS and CV and CUES and TFA, (CORPUS, CV, CUES, TFA)
D_C, D_CV, D_Z, D_T = (os.path.dirname(x) for x in (CORPUS, CV, CUES, TFA))


corpus = json.load(open(CORPUS, encoding="utf-8"))
proves = {}
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
# ---------------------------------------------------------------- omniASR (CTC) amb sherpa-onnx, només CPU
import sherpa_onnx
from huggingface_hub import snapshot_download
MODELS = {"omniASR-CTC-1B": "csukuangfj/sherpa-onnx-omnilingual-asr-1600-languages-1B-ctc-2025-11-12",
          "omniASR-CTC-300M": "csukuangfj/sherpa-onnx-omnilingual-asr-1600-languages-300M-ctc-2025-11-12"}
SORTIDA = []
for nom, repo in MODELS.items():
    try:
        d = snapshot_download(repo, allow_patterns=["model.onnx", "model.weights", "model.int8.onnx", "tokens.txt"])
        print(nom, "baixat", os.listdir(d), flush=True)
        mod = os.path.join(d, "model.onnx")
        rec = sherpa_onnx.OfflineRecognizer.from_omnilingual_asr_ctc(model=mod, tokens=os.path.join(d, "tokens.txt"), num_threads=4)
    except Exception as e:  # noqa: BLE001
        print(nom, "NO CARREGA:", repr(e)[:400], flush=True)
        SORTIDA.append({"model": nom, "error": repr(e)[:400]})
        continue
    t1 = time.time()
    for prova, g in proves.items():
        for k, x in enumerate(g):
            w = x["ona"] if "ona" in x else librosa.load(x["cami"], sr=SR, mono=True)[0][:int(SEGONS_MAXIM * SR)]
            s = rec.create_stream()
            s.accept_waveform(SR, w.astype("float32"))
            rec.decode_stream(s)
            brut = s.result.text
            SORTIDA.append({"model": nom, "prova": prova, "video": x["meta"]["video"], "de": x["meta"]["de"], "or": x["rica"], "brut": brut, "dit": rica(brut)})
            if k % 50 == 0:
                print(nom, prova, k, "/", len(g), f"{time.time() - t1:.0f}s", repr(brut)[:80], flush=True)
        json.dump(SORTIDA, open("/kaggle/working/omniasr_sortides.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump(SORTIDA, open("/kaggle/working/omniasr_sortides.json", "w", encoding="utf-8"), ensure_ascii=False)
print("FI", len(SORTIDA))
