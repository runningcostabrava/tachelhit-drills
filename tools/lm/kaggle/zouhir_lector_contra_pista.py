"""Zouhir Amazigh + BerberFreeQuranEducation: el lector `shi` contra ~1.000 rètols amb pista amaziga HUMANA (#620).

El mateix model de sempre (facebook/mms-1b-all + adaptador `shi`), cada rètol tallat del so (±0,1 s), descodificat
de quatre maneres: greedy, feix sol, feix + bigrames de la biblioteca a α 0,1 i α 0,15 (β 1,0). Es desen els TEXTOS;
el CER/WER es calcula a casa amb el mateix codi que H3 (`h3_puntua`, `zouhir_resum`).
"""

# %%
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-deps", "pyctcdecode==0.5.0"], check=False)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pygtrie", "hypothesis"], check=False)

# %%
import glob, json, os, time
import numpy as np, torch, librosa

DADES = None
for arrel, carpetes, fitxers in os.walk("/kaggle/input"):
    if "cues.json" in fitxers:
        DADES = arrel
        break
assert DADES, glob.glob("/kaggle/input/*")
FORA = "/kaggle/working"
cues = json.load(open(os.path.join(DADES, "cues.json"), encoding="utf-8"))
print(len(cues), "rètols ·", len({c["video"] for c in cues}), "vídeos")

# %%
from transformers import AutoModelForCTC, AutoProcessor
BASE, LANG, SR = "facebook/mms-1b-all", "shi", 16000
proc = AutoProcessor.from_pretrained(BASE)
proc.tokenizer.set_target_lang(LANG)
model = AutoModelForCTC.from_pretrained(BASE)
model.load_adapter(LANG)
adapter = torch.load(os.path.join(DADES, "adaptador_shi_ric.pt"), map_location="cpu")
model.load_state_dict(adapter, strict=False)
dev = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(dev).eval()
torch.set_num_threads(os.cpu_count() or 4)
vocab = {v: k for k, v in proc.tokenizer.get_vocab().items()}
blank, space = proc.tokenizer.pad_token_id, proc.tokenizer.word_delimiter_token
print("model a", dev)


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
wavs, logps = {}, []
t0 = time.time()
for k, c in enumerate(cues):
    if c["video"] not in wavs:
        wavs.clear()
        wavs[c["video"]], _ = librosa.load(os.path.join(DADES, c["video"] + ".wav"), sr=SR, mono=True)
    w = wavs[c["video"]]
    a, b = max(0, int((c["de"] - 0.1) * SR)), min(len(w), int((c["a"] + 0.1) * SR))
    if b - a < SR // 4:
        c["greedy"] = ""
        logps.append(None)
        continue
    ent = proc(w[a:b], sampling_rate=SR, return_tensors="pt").to(dev)
    with torch.no_grad():
        lg = model(**ent).logits[0].float().cpu()
    c["greedy"] = greedy(lg.argmax(-1).tolist())
    logps.append(lg.log_softmax(-1).numpy())
    if k % 100 == 99:
        print(k + 1, f"{time.time()-t0:.0f} s", flush=True)
        json.dump({"cues": cues}, open(os.path.join(FORA, "zouhir_resultats.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(f"logits de {len(cues)} rètols en {time.time()-t0:.0f} s")

# %%
sys.path.insert(0, DADES)
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
CONFIGS = [("beam", None, 0.0, 0.0), ("lm_a0.1", "corpus_bi", 0.1, 1.0), ("lm_a0.15", "corpus_bi", 0.15, 1.0)]
for nom, lm, alpha, beta in CONFIGS:
    t0 = time.time()
    dec = build_ctcdecoder(labels, kenlm_model_path=os.path.join(DADES, lm + ".arpa") if lm else None,
                           unigrams=unigrams if lm else None, alpha=alpha, beta=beta, unk_score_offset=-10.0)
    for c, lp in zip(cues, logps):
        c[nom] = dec.decode(lp, beam_width=64).strip() if lp is not None else ""
    print(f"{nom:10} fet en {time.time()-t0:.0f} s")
    json.dump({"configs": ["greedy"] + [x[0] for x in CONFIGS], "cues": cues},
              open(os.path.join(FORA, "zouhir_resultats.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("desat zouhir_resultats.json")
