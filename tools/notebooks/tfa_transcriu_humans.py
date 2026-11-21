"""Transcriure els vídeos de Tamazight For All que tenen subtítols humans (àrab/anglès).

El mateix lector del Space (MMS-1b-all + adaptador `shi`), per finestres de 30 s amb 28 s de pas
com a mms_shi.py, i per a cada finestra: la lectura greedy de sempre (paraules amb temps) i les
lectures amb el lèxic al feix segons `configs.json` (alpha, beta, quin ARPA), si l'H3 ho ha
guanyat sobre la veritat. Res no es puntua aquí: es desen paraules amb temps per vídeo, i a casa
s'alineen amb els subtítols humans per mesurar la canonada sencera (ASR → glossa → fets) contra
la traducció d'un parlant.
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
    if "adaptador_shi_ric.pt" in fitxers:
        DADES = arrel
        break
assert DADES, glob.glob("/kaggle/input/*")
#: la carpeta amb MÉS wavs: el dataset de la veritat també en porta 8
AUDIO = max((arrel for arrel, _, fitxers in os.walk("/kaggle/input")),
            key=lambda d: sum(f.endswith(".wav") for f in os.listdir(d)))
FORA = "/kaggle/working/transcripcions"
os.makedirs(FORA, exist_ok=True)
#: sense configs.json, només la lectura greedy
cfg = os.path.join(DADES, "configs.json")
configs = json.load(open(cfg, encoding="utf-8")) if os.path.exists(cfg) else []
wavs = sorted(glob.glob(os.path.join(AUDIO, "*.wav")))
print(len(wavs), "wavs ·", configs)

# %%
from transformers import AutoModelForCTC, AutoProcessor
BASE, LANG, SR = "facebook/mms-1b-all", "shi", 16000
WINDOW_S, STRIDE_S, FRAME_S = 30.0, 28.0, 0.02
proc = AutoProcessor.from_pretrained(BASE)
proc.tokenizer.set_target_lang(LANG)
model = AutoModelForCTC.from_pretrained(BASE)
model.load_adapter(LANG)
adapter = torch.load(os.path.join(DADES, "adaptador_shi_ric.pt"), map_location="cpu")
model.load_state_dict(adapter, strict=False)
dev = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(dev).eval()
vocab = {v: k for k, v in proc.tokenizer.get_vocab().items()}
blank, space = proc.tokenizer.pad_token_id, proc.tokenizer.word_delimiter_token


def greedy_words(ids, probs, t0):
    words, cur, start, last, prev, conf = [], [], None, None, None, []
    for k, (i, p) in enumerate(zip(ids, probs)):
        if i == prev:
            continue
        prev = i
        if i == blank:
            continue
        tok = vocab.get(int(i), "")
        t = t0 + k * FRAME_S
        if tok in (space, " "):
            if cur:
                words.append({"text": "".join(cur), "start": round(start, 2), "end": round(last + FRAME_S, 2),
                              "conf": round(float(np.exp(np.mean(np.log(np.clip(conf, 1e-6, 1))))), 3)})
            cur, start, conf = [], None, []
            continue
        if start is None:
            start = t
        last = t
        cur.append(tok)
        conf.append(float(p))
    if cur:
        words.append({"text": "".join(cur), "start": round(start, 2), "end": round(last + FRAME_S, 2),
                      "conf": round(float(np.exp(np.mean(np.log(np.clip(conf, 1e-6, 1))))), 3)})
    return words


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
decoders = {}
for c in configs:
    decoders[c["nom"]] = build_ctcdecoder(labels, kenlm_model_path=os.path.join(DADES, c["lm"] + ".arpa"),
                                          unigrams=unigrams, alpha=c["alpha"], beta=c["beta"])
print("descodificadors:", list(decoders))


def afegeix(words, ww):
    if words:
        ww = [x for x in ww if x["start"] >= words[-1]["end"] - 0.05]
    words.extend(ww)


# %%
t_tot = time.time()
for n, path in enumerate(wavs, 1):
    vid = os.path.splitext(os.path.basename(path))[0]
    fora = os.path.join(FORA, vid + ".json")
    if os.path.exists(fora):
        continue
    t0 = time.time()
    wav, _ = librosa.load(path, sr=SR, mono=True)
    out = {"video": vid, "durada": round(len(wav) / SR, 1), "greedy": []}
    for c in configs:
        out[c["nom"]] = []
    w, s, off = int(WINDOW_S * SR), int(STRIDE_S * SR), 0
    while True:
        ent = proc(wav[off:off + w], sampling_rate=SR, return_tensors="pt").to(dev)
        with torch.no_grad():
            lg = model(**ent).logits[0].float().cpu()
        best = lg.softmax(-1).max(-1)
        afegeix(out["greedy"], greedy_words(best.indices.tolist(), best.values.tolist(), off / SR))
        if decoders:
            logp = lg.log_softmax(-1).numpy()
            for nom, dec in decoders.items():
                beams = dec.decode_beams(logp, beam_width=64)
                ww = [{"text": word, "start": round(off / SR + f0 * FRAME_S, 2), "end": round(off / SR + f1 * FRAME_S, 2)}
                      for word, (f0, f1) in (beams[0][2] if beams else [])]
                afegeix(out[nom], ww)
        if off + w >= len(wav):
            break
        off += s
    json.dump(out, open(fora, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{n:2}/{len(wavs)} {vid} {out['durada']:.0f} s · {len(out['greedy'])} mots · {time.time()-t0:.0f} s", flush=True)
print(f"tot en {(time.time()-t_tot)/60:.1f} min")
