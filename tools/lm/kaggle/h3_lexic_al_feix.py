"""H3: descodificar el MMS `shi` amb el lèxic a dins, mesurat contra la veritat humana.

226 versos narrats + 15 cantats de Tamazight For All amb subtítols humans en amazic (8 vídeos).
El mateix model de sempre (facebook/mms-1b-all + el nostre adaptador `shi`), descodificat de
quatre maneres sobre cada vers:
  greedy        — el de sempre (ha de reproduir CER ~0,21 sobre els narrats; si no, res més val)
  beam          — feix sense cap model de llengua (control: el feix sol no hauria de canviar res)
  beam+lexic    — feix amb un ARPA d'unigrames: totes les formes del lèxic (la restricció pura)
  beam+corpus   — feix amb bigrames de la biblioteca (7.000 frases de parlants) + lèxic

per diversos pesos alpha (pes del LM) i beta (bonificació per paraula). Es desen els TEXTOS,
no les mètriques: el CER i el WER es calculen a casa amb el mateix codi que va donar el 0,21.
"""

# %%
import subprocess, sys
# Només pyctcdecode (Python pur). KenLM no compila al Python 3.13 de Kaggle: el model ARPA el
# llegeix `arpa_lm.py` (al dataset) amb la mateixa interfície. transformers, el que porti Kaggle.
# --no-deps: pyctcdecode arrossegava un numpy 1.x per sobre del numpy 2 de Kaggle i torch
# queia amb «numpy.dtype size changed». Les seves dependències pures s'instal·len a part.
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-deps", "pyctcdecode==0.5.0"], check=False)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pygtrie", "hypothesis"], check=False)
import numpy; print("numpy", numpy.__version__)

# %%
import glob, json, os, time
import numpy as np, torch, librosa

DADES = None
for arrel, carpetes, fitxers in os.walk("/kaggle/input"):
    if "adaptador_shi_ric.pt" in fitxers:
        DADES = arrel
        break
assert DADES, glob.glob("/kaggle/input/*")
print("dades:", DADES, sorted(os.listdir(DADES)))
FORA = "/kaggle/working"
versos = json.load(open(os.path.join(DADES, "veritat_parlat.json"), encoding="utf-8"))
for v in versos:
    v["mena"] = "parlat"
for v in json.load(open(os.path.join(DADES, "veritat_cancons.json"), encoding="utf-8")):
    if os.path.exists(os.path.join(DADES, v["video"] + ".wav")):
        v["mena"] = "cantat"
        versos.append(v)
print(len(versos), "versos")

# %%
from transformers import AutoModelForCTC, AutoProcessor
BASE, LANG, SR = "facebook/mms-1b-all", "shi", 16000
proc = AutoProcessor.from_pretrained(BASE)
proc.tokenizer.set_target_lang(LANG)
model = AutoModelForCTC.from_pretrained(BASE)
model.load_adapter(LANG)
adapter = torch.load(os.path.join(DADES, "adaptador_shi_ric.pt"), map_location="cpu")
known = dict(model.named_parameters())
unknown = [k for k in adapter if k not in known]
assert not unknown, unknown[:5]
model.load_state_dict(adapter, strict=False)
dev = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(dev).eval()
vocab = {v: k for k, v in proc.tokenizer.get_vocab().items()}
blank, space = proc.tokenizer.pad_token_id, proc.tokenizer.word_delimiter_token
print("model carregat a", dev, "· vocab", len(vocab))


def greedy(ids):
    out, prev = [], None
    for i in ids:
        if i == prev:
            continue
        prev = i
        if i == blank:
            continue
        tok = vocab.get(int(i), "")
        out.append(" " if tok in (space, " ") else tok)
    return " ".join("".join(out).split())


# %%
# els logits de cada vers, un sol cop
wavs = {}
logps = []
t0 = time.time()
for v in versos:
    if v["video"] not in wavs:
        wavs[v["video"]], _ = librosa.load(os.path.join(DADES, v["video"] + ".wav"), sr=SR, mono=True)
    w = wavs[v["video"]]
    a, b = max(0, int((v["de"] - 0.1) * SR)), min(len(w), int((v["a"] + 0.1) * SR))
    ent = proc(w[a:b], sampling_rate=SR, return_tensors="pt").to(dev)
    with torch.no_grad():
        lg = model(**ent).logits[0].float().cpu()
    v["greedy"] = greedy(lg.argmax(-1).tolist())
    logps.append(lg.log_softmax(-1).numpy())
print(f"logits de {len(versos)} versos en {time.time()-t0:.0f} s")
print(versos[0]["veritat"], "||", versos[0]["greedy"])

# %%
sys.path.insert(0, DADES)
#: `arpa_lm.py` es al repositori (tools/lm/), no nomes al dataset: sense ell
#: pyctcdecode ignora el lexic i el feix no te cap model de llengua (#715).
import arpa_lm
import pyctcdecode.language_model as plm
import pyctcdecode.decoder as pdec
plm.kenlm = arpa_lm
pdec.kenlm = arpa_lm
from pyctcdecode import build_ctcdecoder


def labels_from_vocab(vocab_by_id, blank, space_token):
    n = max(vocab_by_id) + 1
    labels = [""] * n
    privat = 0xE000
    for i, tok in vocab_by_id.items():
        if i == blank:
            labels[i] = ""
        elif tok == space_token:
            labels[i] = " "
        elif tok in ("<s>", "</s>", "<unk>", "<pad>") or len(tok) != 1:
            labels[i] = chr(privat)
            privat += 1
        else:
            labels[i] = tok
    return labels


labels = labels_from_vocab(vocab, blank, space)
unigrams = [l.strip() for l in open(os.path.join(DADES, "unigrams_shi.txt"), encoding="utf-8") if l.strip()]
#: (nom, arpa, alpha, beta, unk_score_offset). En una prova sintètica alpha 0,6 ja esborrava
#: lletres d'una paraula fora del lèxic: la reixa comença baixa, i una variant castiga menys
#: les paraules desconegudes (-5 en comptes de -10).
#: v2 (15-11, tarda): el mateix ARPA de la biblioteca contra el que hi afegeix el text del
#: Viccionari zgh (990 frases, CC BY-SA). Només els pesos que van guanyar.
CONFIGS = [("beam", None, 0.0, 0.0, -10.0)]
for lm in ("corpus_bi", "corpus_bi_wm"):
    for alpha, beta in ((0.15, 1.0), (0.15, 1.5), (0.1, 1.0), (0.2, 1.0)):
        CONFIGS.append((f"{lm}_a{alpha}_b{beta}", lm, alpha, beta, -10.0))
for nom, lm, alpha, beta, unk in CONFIGS:
    t0 = time.time()
    try:
        dec = build_ctcdecoder(labels, kenlm_model_path=os.path.join(DADES, lm + ".arpa") if lm else None,
                               unigrams=unigrams if lm else None, alpha=alpha, beta=beta, unk_score_offset=unk)
        for v, lp in zip(versos, logps):
            v[nom] = dec.decode(lp, beam_width=64).strip()
        print(f"{nom:22} fet en {time.time()-t0:.0f} s · ex: {versos[0][nom]}")
    except Exception as e:
        print(f"{nom:22} ERROR {e}")
        for v in versos:
            v[nom] = None
    json.dump({"configs": [c[0] for c in CONFIGS], "versos": versos},
              open(os.path.join(FORA, "h3_resultats.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("desat h3_resultats.json")
