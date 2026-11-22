"""Es pot alinear amb un model tres vegades mes petit i tenir les mateixes fronteres?

L'alineacio actual fa servir **MMS-1b-all** (mil milions de parametres, 4 GB) i triga ~26 h
per als 20.547 talls. `torchaudio.pipelines.MMS_FA` es un model **fet expressament per
alinear**, entrenat sobre 1.100 llengues, de ~300 M.

Si dona les mateixes fronteres, la feina passa de 26 h a potser 9, i el retall -- que val
-0,2235 de CER (DESXIFRAT §45) -- es te avui.

**Com es comprova sense creure-se'l:** hi ha 6.500 talls amb la frontera del model gran ja
calculada. Es calcula la del petit sobre els mateixos i es comparen. El 22-11 el metode per
energia va fallar aixi (error medias de 0,6-0,8 s, §46); aquest te molt millor pronostic
perque fa la MATEIXA feina -- Viterbi sobre probabilitats de CTC amb el text conegut -- pero
aixo s'ha de veure, no suposar.

No toca res: mesura i escriu.
"""
import io
import json
import statistics as s
import time
import unicodedata
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchaudio
from torchaudio.pipelines import MMS_FA

#: el fitxer es pot passar per la linia d ordres: la primera mesura (22-11) es va fer contra
#: fronteres que nomes alineaven els separadors de paraula, i cal poder-la refer.
import sys
ALI = Path(sys.argv[1] if len(sys.argv) > 1
           else r"E:/tamazight/_magatzem/alineacio_ecs_v2.jsonl")
ARREL = Path(r"E:/tamazight/talls_ecs")
QUANTS = 60

torch.set_num_threads(4)

TIFI = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "d", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k",
        "ⵀ": "h", "ⵃ": "h", "ⵄ": "a", "ⵅ": "x", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l",
        "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "g", "ⵙ": "s", "ⵚ": "s",
        "ⵛ": "c", "ⵜ": "t", "ⵟ": "t", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "z", "ⵯ": "w",
        "ⵒ": "p", "ⴶ": "g", "ⵌ": "j"}


def roman(t):
    """MMS_FA vol lletres llatines basiques: el tifinag s'hi transliterin."""
    fora = []
    for c in t:
        if c in TIFI:
            fora.append(TIFI[c])
        elif c.isspace():
            fora.append(" ")
        elif c.isascii() and c.isalpha():
            fora.append(c.lower())
        else:
            d = unicodedata.normalize("NFD", c)
            b = "".join(x for x in d if not unicodedata.combining(x))
            if b.isascii() and b.isalpha():
                fora.append(b.lower())
    return " ".join("".join(fora).split())


ali = {}
for l in io.open(ALI, encoding="utf-8"):
    if not l.strip():
        continue
    try:
        x = json.loads(l)
    except Exception:
        continue
    if x.get("veu_ini") is not None:
        ali[x["so"]] = x

#: el text de cada tall
text = {}
for p in ARREL.glob("*/subtitols.jsonl"):
    for l in io.open(p, encoding="utf-8"):
        if not l.strip():
            continue
        f = json.loads(l)
        if f.get("tall"):
            text[Path(f["tall"]).name] = f.get("tifinag") or ""

print(f"{len(ali)} talls alineats · {len(text)} amb text")
print("carregant MMS_FA…", flush=True)
t0 = time.time()
mod = MMS_FA.get_model()
tok = MMS_FA.get_tokenizer()
alinea = MMS_FA.get_aligner()
print(f"   carregat en {time.time()-t0:.0f} s", flush=True)

dini, dfi, fallats, temps = [], [], 0, []
mirats = 0
for nom, a in ali.items():
    t = roman(text.get(nom, ""))
    if len(t) < 3:
        continue
    w = ARREL / a["capitol"] / "talls" / nom
    if not w.exists():
        continue
    #: torchaudio.load demana torchcodec: soundfile fa la mateixa feina i ja hi es
    xs, sr = sf.read(str(w), dtype="float32")
    if xs.ndim > 1:
        xs = xs.mean(axis=1)
    x = torch.from_numpy(np.ascontiguousarray(xs)).unsqueeze(0)
    if sr != 16000:
        x = torchaudio.functional.resample(x, sr, 16000)
    t1 = time.time()
    try:
        with torch.inference_mode():
            em, _ = mod(x)
            sp = alinea(em[0], tok(t.split()))
        rao = x.shape[1] / em.shape[1] / 16000
        ini = sp[0][0].start * rao
        fi = sp[-1][-1].end * rao
    except Exception:
        fallats += 1
        continue
    temps.append(time.time() - t1)
    dini.append(ini - a["veu_ini"])
    dfi.append(fi - a["veu_fi"])
    mirats += 1
    if mirats >= QUANTS:
        break

if not dini:
    print("   cap tall comparable")
    raise SystemExit(1)

print(f"\n   {mirats} talls · {fallats} fallats · {s.mean(temps):.2f} s per tall")
print(f"\n   {'':<10}{'mediana':>9}{'|error| mitjà':>15}{'dins 0,2 s':>12}{'dins 0,1 s':>12}")
for nom, d in (("inici", dini), ("final", dfi)):
    print(f"   {nom:<10}{s.median(d):>9.3f}{s.mean([abs(v) for v in d]):>15.3f}"
          f"{100*sum(1 for v in d if abs(v)<=0.2)/len(d):>11.0f} %"
          f"{100*sum(1 for v in d if abs(v)<=0.1)/len(d):>11.0f} %")
totes = sum(1 for i in range(len(dini)) if abs(dini[i]) <= 0.2 and abs(dfi[i]) <= 0.2)
print(f"\n   les dues dins de 0,2 s: {100*totes/len(dini):.0f} %")
