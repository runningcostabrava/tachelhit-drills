"""Alinear amb `torchaudio MMS_FA` i **desar** les fronteres, per poder-les jutjar pel resultat.

**Per que.** El 22-11 vaig descartar el MMS_FA perque nomes el 5 % de les seves fronteres queien
a 0,2 s de les del model gran. Aquella comparacio era contra fronteres dolentes: l'alineador
gran rebia nomes els separadors de paraula (quadern, §48). Refeta contra les bones, el MMS_FA
passa al **62 %**, amb mediana d'error -0,016 s a l'inici i +0,036 s al final -- sense biaix.

Pero l'acord de fronteres no es el que volem saber. El que volem saber es si **retallar amb les
seves fronteres baixa el CER igual**. Per aixo cal desar-les i passar-les a `prova_retall/mesura.py`,
que es la mateixa mesura i el mateix model als dos costats.

Si surt igual: 1,31 s per tall contra ~7, i el corpus sencer s'alinea en unes 7 h en lloc de 34.

No toca res: llegeix els wav i escriu `alineacio_mms_fa.jsonl`.

    python alinea_mms_fa.py [--so CARPETA] [--subtitols FITXER] [--desti FITXER]
"""
import argparse
import io
import json
import time
import unicodedata
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchaudio
from torchaudio.pipelines import MMS_FA

torch.set_num_threads(4)

#: la mateixa taula que `prova_mms_fa.py`: el MMS_FA vol lletres llatines basiques, i les
#: distincions que el nostre transliterador guarda (d/ḍ, g/ġ) el seu vocabulari no les te.
TIFI = {"\u2d30": "a", "\u2d31": "b", "\u2d33": "g", "\u2d37": "d", "\u2d39": "d", "\u2d3b": "e",
        "\u2d3c": "f", "\u2d3d": "k", "\u2d40": "h", "\u2d43": "h", "\u2d44": "a", "\u2d45": "x",
        "\u2d47": "q", "\u2d49": "i", "\u2d4a": "j", "\u2d4d": "l", "\u2d4e": "m", "\u2d4f": "n",
        "\u2d53": "u", "\u2d54": "r", "\u2d55": "r", "\u2d56": "g", "\u2d59": "s", "\u2d5a": "s",
        "\u2d5b": "c", "\u2d5c": "t", "\u2d5f": "t", "\u2d61": "w", "\u2d62": "y", "\u2d63": "z",
        "\u2d65": "z", "\u2d6f": "w", "\u2d52": "p", "\u2d36": "g", "\u2d4c": "j"}


def roman(t):
    fora = []
    for c in t or "":
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--so", default=r"E:/tamazight/_magatzem/prova_retall/so")
    ap.add_argument("--subtitols", default=r"E:/tamazight/_magatzem/prova_retall/subtitols.jsonl")
    ap.add_argument("--desti", default=r"E:/tamazight/_magatzem/alineacio_mms_fa.jsonl")
    a = ap.parse_args()

    text = {}
    for l in io.open(a.subtitols, encoding="utf-8"):
        if not l.strip():
            continue
        x = json.loads(l)
        if x.get("tall"):
            text[Path(x["tall"]).name] = x.get("tifinag") or ""

    wavs = sorted(Path(a.so).glob("*.wav"))
    print(f"{len(wavs)} wav · {len(text)} amb text")

    #: reprenible: si es mata, continua
    fets = set()
    desti = Path(a.desti)
    if desti.exists():
        for l in io.open(desti, encoding="utf-8"):
            try:
                fets.add(json.loads(l)["so"])
            except Exception:
                pass
    print(f"ja fets: {len(fets)}")

    mod = MMS_FA.get_model()
    tok = MMS_FA.get_tokenizer()
    alinea = MMS_FA.get_aligner()

    t0, n, sense, fallats = time.time(), 0, 0, 0
    with io.open(desti, "a", encoding="utf-8", newline="\n") as f:
        for w in wavs:
            if w.name in fets:
                continue
            t = roman(text.get(w.name, ""))
            if len(t) < 3:
                sense += 1
                continue
            xs, sr = sf.read(str(w), dtype="float32")
            if xs.ndim > 1:
                xs = xs.mean(axis=1)
            x = torch.from_numpy(np.ascontiguousarray(xs)).unsqueeze(0)
            if sr != 16000:
                x = torchaudio.functional.resample(x, sr, 16000)
            try:
                with torch.inference_mode():
                    em, _ = mod(x)
                    sp = alinea(em[0], tok(t.split()))
                rao = x.shape[1] / em.shape[1] / 16000
                ini, fi = sp[0][0].start * rao, sp[-1][-1].end * rao
            except Exception as ex:
                fallats += 1
                print(f"   {w.name}: {type(ex).__name__}", flush=True)
                continue
            f.write(json.dumps({"so": w.name, "capitol": w.name.rsplit("_", 1)[0],
                                "durada": round(x.shape[1] / 16000, 2),
                                "veu_ini": round(ini, 2), "veu_fi": round(fi, 2)},
                               ensure_ascii=False) + "\n")
            f.flush()
            n += 1
            if n % 50 == 0:
                print(f"   {n} · {n/(time.time()-t0):.2f} talls/s", flush=True)

    print(f"\n{n} alineats · {sense} sense text prou llarg · {fallats} fallats"
          f" · {(time.time()-t0)/max(n,1):.2f} s per tall")


if __name__ == "__main__":
    main()
