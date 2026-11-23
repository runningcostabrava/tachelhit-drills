"""Alinear els 18.506 talls que viuen a l'ECS. A poc a poc, sense GPU, i reprenible.

Per que: el 21-11 vam mesurar, sobre 1.187 talls NOSTRES, que **el 40 % del so no es la
frase** (silenci al davant 0,74 s de mediana, al darrere 0,85 s). Els talls que hi ha a
l'ECS son dels 29 capitols VELLS, els que alimenten la biblioteca i el cercle. Si tenen el
mateix problema, tornar-los a tallar val mes que qualsevol ronda del cercle.

Per que aqui i no a la GPU: aquesta maquina esta pagada fins al 02-2027 i **no fa res**
(carrega 0,00). La GPU es un recurs escas i la volem per entrenar; aixo es una mesura que pot
trigar hores i no li fa res.

Com es comporta:
  * **reprenible**: escriu cada tall a mesura que l'alinea, i al tornar a arrencar salta els
    que ja hi son. Es pot matar i reprendre sense perdre res.
  * **educat amb la fabrica**: 3 fils de 4, i `nice`. Si la fabrica arrenca, te un nucli lliure.
  * no toca cap tall ni cap cataleg: nomes escriu `alineacio_ecs.jsonl`.

    nohup nice -n 10 /opt/venv/bin/python -X utf8 /root/ecs_alinea.py >> /root/alinea.log 2>&1 &
"""
import io
import json
import os
import re
import time
import unicodedata
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "3")
os.environ.setdefault("MKL_NUM_THREADS", "3")

import numpy as np
import soundfile as sf
import torch

torch.set_num_threads(3)

from transformers import AutoProcessor, Wav2Vec2ForCTC

MODEL = "facebook/mms-1b-all"
ARREL = Path("/root/tamazight_tv")
DESTI = Path("/root/alineacio_ecs.jsonl")
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


#: El vocabulari `shi` del MMS es LLATI. El nostre text es tifinag, i sense transliterar no hi
#: entra cap lletra: nomes els espais. El 23-11 aixo va fer que 9.295 talls s'alineessin contra
#: una sequencia de separadors de paraula -- no contra la frase, i tallant veu de debo. Les
#: taules son les de `tools/lm/kaggle/alineacio_forcada_snrt.py`, que ja ho feia be.
TIF_RIC = {"\u2d30": "a", "\u2d31": "b", "\u2d33": "g", "\u2d37": "d", "\u2d39": "\u1e0d",
           "\u2d3b": "e", "\u2d3c": "f", "\u2d3d": "k", "\u2d40": "h", "\u2d43": "\u1e25",
           "\u2d44": "\u03b5", "\u2d45": "\u1e2b", "\u2d47": "q", "\u2d49": "i", "\u2d4a": "j",
           "\u2d4d": "l", "\u2d4e": "m", "\u2d4f": "n", "\u2d53": "u", "\u2d54": "r",
           "\u2d55": "r", "\u2d56": "\u0121", "\u2d59": "s", "\u2d5a": "\u1e63",
           "\u2d5b": "\u0161", "\u2d5c": "t", "\u2d5f": "\u1e6d", "\u2d61": "w",
           "\u2d62": "y", "\u2d63": "z", "\u2d65": "\u1e93", "\u2d6f": "w"}
LLATI_RIC = {"\u0263": "\u0121", "\u03b3": "\u0121", "\u025b": "\u03b5", "\u1e5b": "r",
             "c": "\u0161", "x": "\u1e2b", "\u03c7": "\u1e2b", "\u017e": "j", "\u01e7": "j",
             "\u02b7": "w", "v": "f", "p": "b", "o": "u"}
NOMES_RIC = re.compile(r"[^a-z\u0121\u03b5\u1e25\u1e0d\u1e6d\u1e63\u1e93\u1e2b\u0161 ]+")


def rica(t):
    t = unicodedata.normalize("NFC", (t or "")).strip().lower()
    t = "".join(TIF_RIC.get(c, c) for c in t)
    t = "".join(LLATI_RIC.get(c, c) for c in t)
    return re.sub(r" +", " ", NOMES_RIC.sub("", t)).strip()


def a_ids(t):
    return [SEP if c == " " else vocab[c] for c in rica(t) if c == " " or c in vocab]


#: Que no torni a passar en silenci: "azul tamazi\u0121t" en tifinag ha de donar 13 simbols i 12
#: que no siguin el separador. Si no, para aqui i no gastis 22 h alineant buits.
_p = a_ids("\u2d30\u2d63\u2d53\u2d4d \u2d5c\u2d30\u2d4e\u2d30\u2d63\u2d49\u2d56\u2d5c")
assert len(_p) >= 12 and sum(1 for i in _p if i != SEP) >= 10, (
    f"el tifinag no arriba al vocabulari: {_p}")


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
