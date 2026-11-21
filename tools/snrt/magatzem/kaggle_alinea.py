# Via 2: on cau de debo la veu de cada tall, i que es guanya retallant-la be.
#
# El diagnostic del 18-11 (#601) ho va mesurar sobre 589 talls de capitols antics:
#   * el 62 % tenen l'inici desplacat mes de mig segon (rang de -36 s a +119 s);
#   * retallant on el model sent la veu, el CER passa de 0,7370 a 0,6581 -> **-0,0789**.
# Per comparar: una ronda del cercle val -0,003 a -0,013.
#
# Aqui es fa sobre **els nostres** talls (els 27 capitols collits, sense el Rif), que son els
# que alimenten la via 3 (veu -> arab), on el tall ES l'entrada del model.
#
# Com: alineacio forcada CTC (Viterbi) del text del tall contra el seu propi audio, amb el
# MMS `shi` + l'adaptador. Es desen els limits nous perque es pugui tornar a tallar a casa.
#
# El que NO fa: no entrena res i no decideix res. Nomes mesura i escriu els limits.

MODEL = "facebook/mms-1b-all"
DADES = None   #: el busca _troba(), que el camí de Kaggle canvia
FORA = "/kaggle/working"
QUANTS = 1200          # una mostra: amb aixo ja es veu la distribucio

import os, subprocess, sys
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U",
                "transformers>=4.44,<5", "soundfile"], check=False)

import io, json, re, time, unicodedata
import numpy as np
import soundfile as sf
import torch


def _troba(nom):
    """On ha muntat Kaggle el conjunt que conte `nom`.

    El cami ha canviat (abans /kaggle/input/<conjunt>, ara
    /kaggle/input/datasets/<usuari>/<conjunt>) i un cami escrit a ma es trenca cada vegada.
    Es busca la carpeta que contingui el fitxer.
    """
    import os
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return arrel
    raise FileNotFoundError(f"no trobo cap carpeta amb {nom} sota /kaggle/input")


DADES = _troba("train.jsonl")
print("dades a", DADES)
from transformers import AutoProcessor, Wav2Vec2ForCTC


def de_kaggle(nom):
    for arrel, _, fitxers in os.walk("/kaggle/input"):
        if nom in fitxers:
            return os.path.join(arrel, nom)
    return None


ADAPT = de_kaggle("adaptador_shi_zouhir_b.pt")
print("adaptador:", ADAPT, flush=True)

proc = AutoProcessor.from_pretrained(MODEL)
proc.tokenizer.set_target_lang("shi")
model = Wav2Vec2ForCTC.from_pretrained(MODEL, ignore_mismatched_sizes=True)
model.load_adapter("shi")
if ADAPT:
    est = torch.load(ADAPT, map_location="cpu")
    model.load_state_dict(est.get("model", est), strict=False)
    print("adaptador carregat", flush=True)
model = model.cuda().eval().half()

vocab = proc.tokenizer.get_vocab()
inv = {v: k for k, v in vocab.items()}
BUIT = proc.tokenizer.pad_token_id
SEP = vocab.get(proc.tokenizer.word_delimiter_token, vocab.get("|"))


def rica(t):
    t = unicodedata.normalize("NFC", (t or "").lower())
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)).strip()


def a_ids(t):
    fora = []
    for c in rica(t):
        i = vocab.get(" " if c == " " else c)
        if c == " ":
            i = SEP
        if i is not None:
            fora.append(i)
    return fora


def so(nom):
    d, sr = sf.read(f"{DADES}/so/{nom}", dtype="float32")
    if getattr(d, "ndim", 1) > 1:
        d = d.mean(axis=1)
    return d, sr


def alinea(logp, ids):
    """Viterbi CTC forcat: torna (primer marc, ultim marc) on cau el text."""
    T, _ = logp.shape
    S = 2 * len(ids) + 1
    seq = [BUIT] * S
    for i, k in enumerate(ids):
        seq[2 * i + 1] = k
    NEG = -1e9
    dp = np.full((T, S), NEG, dtype=np.float32)
    bt = np.zeros((T, S), dtype=np.int32)
    dp[0, 0] = logp[0, BUIT]
    if S > 1:
        dp[0, 1] = logp[0, seq[1]]
    for t in range(1, T):
        for s in range(S):
            millor, dm = dp[t - 1, s], s
            if s > 0 and dp[t - 1, s - 1] > millor:
                millor, dm = dp[t - 1, s - 1], s - 1
            if s > 1 and seq[s] != BUIT and seq[s] != seq[s - 2] and dp[t - 1, s - 2] > millor:
                millor, dm = dp[t - 1, s - 2], s - 2
            dp[t, s] = millor + logp[t, seq[s]]
            bt[t, s] = dm
    s = S - 1 if dp[T - 1, S - 1] >= dp[T - 1, S - 2] else S - 2
    cami = []
    for t in range(T - 1, -1, -1):
        cami.append(s)
        s = bt[t, s]
    cami.reverse()
    marcs = [t for t, s in enumerate(cami) if seq[s] != BUIT]
    return (marcs[0], marcs[-1]) if marcs else (0, T - 1)


files = [json.loads(l) for l in io.open(f"{DADES}/train.jsonl", encoding="utf-8") if l.strip()]
files = [x for x in files if (x.get("zgh") or "").strip()][:QUANTS]
print(f"{len(files)} talls a alinear", flush=True)

sortida, t0 = [], time.time()
for i, x in enumerate(files, 1):
    try:
        d, sr = so(x["so"])
        ids = a_ids(x["zgh"])
        if not ids or len(d) < sr * 0.5:
            continue
        e = proc(d, sampling_rate=sr, return_tensors="pt").input_values.cuda().half()
        with torch.no_grad():
            lg = model(e).logits[0].float().log_softmax(-1).cpu().numpy()
        a, b = alinea(lg, ids)
        pas = len(d) / sr / lg.shape[0]
        sortida.append({"so": x["so"], "durada": len(d) / sr,
                        "veu_ini": round(a * pas, 2), "veu_fi": round(b * pas, 2),
                        "capitol": x["capitol"]})
    except Exception as e:
        print(f"   {x['so']}: {type(e).__name__}", flush=True)
    if i % 100 == 0:
        print(f"   {i}/{len(files)} · {time.time()-t0:.0f}s", flush=True)

json.dump(sortida, io.open(f"{FORA}/alineacio_nostra.json", "w", encoding="utf-8"),
          ensure_ascii=False)
ini = sorted(x["veu_ini"] for x in sortida)
fi = sorted(x["durada"] - x["veu_fi"] for x in sortida)
print(f"\n{len(sortida)} talls alineats")
print(f"silenci al davant: mediana {ini[len(ini)//2]:.2f} s · >0,3 s: "
      f"{sum(1 for v in ini if v > .3)} ({100*sum(1 for v in ini if v>.3)/len(ini):.0f} %)")
print(f"silenci al darrere: mediana {fi[len(fi)//2]:.2f} s · >0,3 s: "
      f"{sum(1 for v in fi if v > .3)} ({100*sum(1 for v in fi if v>.3)/len(fi):.0f} %)")
sob = sum(ini) + sum(fi)
tot = sum(x["durada"] for x in sortida)
print(f"part del so que no és la frase: {100*sob/tot:.0f} %")
