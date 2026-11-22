"""El CER premia encertar la frontera, o premia escurcar el so?

**Per que cal preguntar-ho.** El 22-11 vaig mesurar que retallar amb l'alineacio baixa el CER
0,2235. El 23-11 va sortir que aquella alineacio no rebia la frase, nomes els separadors de
paraula (quadern, §48): retallava massa i es quedava el 59 % del so. Amb les fronteres bones es
queda el 82 % i el guany baixa a 0,0741.

Aixo fa sospitar del jutge. El CER del so sencer es **1,05**: per sobre d'1 vol dir que l'ASR
transcriu mes del que diu la frase, i aleshores **qualsevol cosa que escurci el so treu
insercions i baixa el CER**, encerti la frontera o no.

**La prova.** El mateix model, la mateixa referencia i les MATEIXES fronteres bones, canviant
nomes el marge. Un marge negatiu retalla **endins**, cap a veu que sabem que hi es:

    marge +0,30  es queda mes que la frase
    marge +0,15  el que fem servir
    marge  0,00  la frontera justa
    marge -0,30  es menja 0,3 s de veu de cada banda
    marge -0,60  es menja 0,6 s de cada banda

Si el CER **segueix baixant** cap a l'esquerra de la taula, el CER no mesura si encertem la
frase: mesura quant de so hem tret, i el -0,2235 d'ahir era aixo.

Si el CER fa **vall** al voltant de 0, el jutge es bo i la frontera importa.

Carrega el model **un sol cop** per a tots els marges: la mesura d'abans el carregava cada
vegada i cada marge costava 20 minuts.

    python prova_el_jutge.py [FITXER_ALINEACIO]
"""
import io
import json
import sys
from pathlib import Path

AQUI = Path(r"E:/tamazight/_magatzem/prova_retall")
BACK = Path(r"C:/Users/josep/app2/tachelhit-drills/backend")
sys.path.insert(0, str(BACK))
MARGES = (0.30, 0.15, 0.00, -0.30, -0.60)
QUANTS = 250

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
import torch  # noqa: E402
from transformers import AutoProcessor, Wav2Vec2ForCTC  # noqa: E402

torch.set_num_threads(4)
ALI = sys.argv[1] if len(sys.argv) > 1 else r"E:/tamazight/_magatzem/alineacio_ecs_v2.jsonl"


def cer(ref, hip):
    if not ref:
        return 1.0
    d = range(len(hip) + 1)
    for i, c in enumerate(ref, 1):
        nd = [i]
        for j, k in enumerate(hip, 1):
            nd.append(min(d[j] + 1, nd[j - 1] + 1, d[j - 1] + (c != k)))
        d = nd
    return d[-1] / len(ref)


sub = {}
for l in io.open(AQUI / "subtitols.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        if x.get("tall"):
            sub[Path(x["tall"]).name] = x

ali = {}
for l in io.open(ALI, encoding="utf-8"):
    if not l.strip():
        continue
    try:
        x = json.loads(l)
    except Exception:
        continue
    ali[x["so"]] = x

wavs = [w for w in sorted(AQUI.glob("so/*.wav"))[:QUANTS] if w.name in ali]
print(f"{len(wavs)} talls amb alineació · {ALI}")

sys.path.insert(0, str(Path(r"E:/tamazight/fabrica/tools/snrt/fabrica")))
try:
    import transliterador as TR
    tifi = TR.tifinag_a_llati
except Exception:
    import re
    TAULA = {"\u2d30": "a", "\u2d31": "b", "\u2d33": "g", "\u2d37": "d", "\u2d39": "\u1e0d",
             "\u2d3b": "e", "\u2d3c": "f", "\u2d3d": "k", "\u2d40": "h", "\u2d43": "\u1e25",
             "\u2d44": "\u025b", "\u2d45": "x", "\u2d47": "q", "\u2d49": "i", "\u2d4a": "j",
             "\u2d4d": "l", "\u2d4e": "m", "\u2d4f": "n", "\u2d53": "u", "\u2d54": "r",
             "\u2d55": "\u1e5b", "\u2d56": "\u0263", "\u2d59": "s", "\u2d5a": "\u1e63",
             "\u2d5b": "\u0161", "\u2d5c": "t", "\u2d5f": "\u1e6d", "\u2d61": "w",
             "\u2d62": "y", "\u2d63": "z", "\u2d65": "\u1e93", "\u2d6f": "\u02b7",
             "\u2d52": "p"}

    def tifi(s):
        return re.sub(r"\s+", " ",
                      "".join(TAULA.get(c, c if c == " " else "") for c in s)).strip()


print("carregant el model…", flush=True)
proc = AutoProcessor.from_pretrained("facebook/mms-1b-all", target_lang="shi")
mod = Wav2Vec2ForCTC.from_pretrained("facebook/mms-1b-all", target_lang="shi",
                                     ignore_mismatched_sizes=True).eval()


def digues(x, sr=16000):
    iv = proc(x, sampling_rate=sr, return_tensors="pt")
    with torch.no_grad():
        lo = mod(**iv).logits
    return proc.batch_decode(torch.argmax(lo, dim=-1))[0]


#: una fila per tall: el CER a cada marge, i quant so queda
files = []
for i, w in enumerate(wavs):
    s = sub.get(w.name)
    if not s or not (s.get("tifinag") or "").strip():
        continue
    ref = tifi(s["tifinag"]).lower().strip()
    if len(ref) < 4:
        continue
    x, sr = sf.read(str(w))
    if x.ndim > 1:
        x = x.mean(axis=1)
    a = ali[w.name]
    f = {"so": w.name, "durada": len(x) / sr}
    f["sencer"] = cer(ref, digues(x.astype(np.float32), sr).lower().strip())
    be = True
    for m in MARGES:
        i0 = max(0, int((a["veu_ini"] - m) * sr))
        i1 = min(len(x), int((a["veu_fi"] + m) * sr))
        if i1 - i0 < sr * 0.3:
            be = False
            break
        f[f"m{m:+.2f}"] = cer(ref, digues(x[i0:i1].astype(np.float32), sr).lower().strip())
        f[f"q{m:+.2f}"] = (i1 - i0) / len(x)
    if be:
        files.append(f)
    if len(files) and len(files) % 20 == 0:
        print(f"   {len(files)} talls", flush=True)

json.dump(files, io.open(AQUI / "jutge.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

sencer = float(np.mean([f["sencer"] for f in files]))
print(f"\n   {len(files)} talls · CER del so sencer {sencer:.4f}\n")
print(f"   {'marge':>7}{'so que queda':>14}{'CER':>9}{'contra sencer':>15}{'millora':>9}")
for m in MARGES:
    c = float(np.mean([f[f"m{m:+.2f}"] for f in files]))
    q = float(np.mean([f[f"q{m:+.2f}"] for f in files]))
    mi = sum(1 for f in files if f[f"m{m:+.2f}"] < f["sencer"])
    print(f"   {m:>+7.2f}{100*q:>13.0f}%{c:>9.4f}{c-sencer:>+15.4f}"
          f"{100*mi/len(files):>8.0f}%")
print("\n   si el CER baixa sense parar cap avall, el jutge premia escurçar, no encertar")
