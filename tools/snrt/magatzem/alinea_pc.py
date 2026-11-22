"""Alinear els talls que la fabrica del PC acaba de fer -- els que l'ECS no te.

Germa de `ecs_alinea.py`, amb dues diferencies: mira `E:/tamazight/fabrica/td_tv` (la collita
d'aquest PC) i escriu a `alineacio_pc.jsonl`. **No es trepitgen**: son talls diferents en
fitxers diferents, aixi que les dues maquines poden anar alhora sense duplicar feina.

Per que cal: mesurat el 22-11 sobre talls de `agnkrfivlpeuwz` (MMS-1b-all + shi, la mateixa
referencia, canviant NOMES si el wav va sencer o retallat), el CER passa d'1,0401 a 0,8490 --
**-0,19**, i la distancia creix com mes talls es miren. El silenci no es silenci: es altra
gent parlant, i l'ASR la transcriu.
"""

import io
import json
import os
import re
import time
import unicodedata
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "3")

import numpy as np
import soundfile as sf
import torch

torch.set_num_threads(2)

from transformers import AutoProcessor, Wav2Vec2ForCTC

MODEL = "facebook/mms-1b-all"
ARREL = Path("E:/tamazight/fabrica/td_tv")
DESTI = Path("E:/tamazight/_magatzem/alineacio_pc.jsonl")
ADAPT = Path("/root/alta/sortida_B/adaptador_shi_snrt_B.pt")

fets = set()
if DESTI.exists():
    for l in io.open(DESTI, encoding="utf-8"):
        try:
            fets.add(json.loads(l)["so"])
        except Exception:
            pass
print(f"ja fets: {len(fets)}", flush=True)

print("carregant el model...", flush=True)
proc = AutoProcessor.from_pretrained(MODEL)
proc.tokenizer.set_target_lang("shi")
model = Wav2Vec2ForCTC.from_pretrained(MODEL, ignore_mismatched_sizes=True)
model.load_adapter("shi")
if ADAPT.exists():
    est = torch.load(str(ADAPT), map_location="cpu")
    model.load_state_dict(est.get("model", est), strict=False)
    print(f"adaptador: {ADAPT.name}", flush=True)
model = model.eval().float()

vocab = proc.tokenizer.get_vocab()
BUIT = proc.tokenizer.pad_token_id
SEP = vocab.get(proc.tokenizer.word_delimiter_token, vocab.get("|"))


def a_ids(t):
    t = unicodedata.normalize("NFC", (t or "").lower())
    t = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)).strip()
    return [SEP if c == " " else vocab[c] for c in t if c == " " or c in vocab]


def alinea(logp, ids):
    T = logp.shape[0]
    S = 2 * len(ids) + 1
    seq = [BUIT] * S
    for i, k in enumerate(ids):
        seq[2 * i + 1] = k
    dp = np.full((T, S), -1e9, dtype=np.float32)
    bt = np.zeros((T, S), dtype=np.int32)
    dp[0, 0] = logp[0, BUIT]
    if S > 1:
        dp[0, 1] = logp[0, seq[1]]
    for t in range(1, T):
        p = dp[t - 1]
        for s in range(S):
            m, d = p[s], s
            if s > 0 and p[s - 1] > m:
                m, d = p[s - 1], s - 1
            if s > 1 and seq[s] != BUIT and seq[s] != seq[s - 2] and p[s - 2] > m:
                m, d = p[s - 2], s - 2
            dp[t, s] = m + logp[t, seq[s]]
            bt[t, s] = d
    s = S - 1 if dp[T - 1, S - 1] >= dp[T - 1, S - 2] else S - 2
    cami = []
    for t in range(T - 1, -1, -1):
        cami.append(s)
        s = bt[t, s]
    cami.reverse()
    marcs = [t for t, s in enumerate(cami) if seq[s] != BUIT]
    return (marcs[0], marcs[-1]) if marcs else (0, T - 1)


#: quin text va amb cada tall
feina = []
for cap in sorted(ARREL.iterdir()):
    sub = cap / "subtitols.jsonl"
    talls = cap / "talls"
    if not (sub.exists() and talls.is_dir()):
        continue
    linies = [json.loads(l) for l in io.open(sub, encoding="utf-8") if l.strip()]
    for i, x in enumerate(linies):
        w = talls / f"{cap.name}_{i:04d}.wav"
        if w.exists() and w.name not in fets:
            t = (x.get("tifinag") or x.get("zgh") or "").strip()
            if t:
                feina.append((w, t, cap.name))
print(f"{len(feina)} talls per alinear", flush=True)

t0, n = time.time(), 0
with io.open(DESTI, "a", encoding="utf-8", newline="\n") as f:
    for w, text, cap in feina:
        try:
            d, sr = sf.read(str(w), dtype="float32")
            if getattr(d, "ndim", 1) > 1:
                d = d.mean(axis=1)
            ids = a_ids(text)
            if not ids or len(d) < sr * 0.5:
                continue
            e = proc(d, sampling_rate=sr, return_tensors="pt").input_values
            with torch.no_grad():
                lg = model(e).logits[0].float().log_softmax(-1).numpy()
            a, b = alinea(lg, ids)
            pas = len(d) / sr / lg.shape[0]
            f.write(json.dumps({"so": w.name, "capitol": cap,
                                "durada": round(len(d) / sr, 2),
                                "veu_ini": round(a * pas, 2),
                                "veu_fi": round(b * pas, 2)}, ensure_ascii=False) + "\n")
            f.flush()
            n += 1
        except Exception as ex:
            print(f"   {w.name}: {type(ex).__name__}", flush=True)
        if n and n % 50 == 0:
            v = n / (time.time() - t0)
            print(f"   {n}/{len(feina)} · {v:.2f} talls/s · queden "
                  f"{(len(feina)-n)/max(v,1e-9)/3600:.1f} h", flush=True)

print(f"fet: {n} talls en {(time.time()-t0)/3600:.1f} h", flush=True)
