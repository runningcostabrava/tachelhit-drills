# -*- coding: utf-8 -*-
"""Reprodueix la mesura del lector de tifinag (#601) sobre les 52 línies de «Illy» transcrites a mà.

  python -X utf8 tools/snrt/fabrica/prova_lector_tifinag.py <carpeta_tipografia>

`<carpeta_tipografia>` té `veritat_tifinag.json` (52 línies) i `fotogrames/NNN_banda.png` (franja de 1920×160 des de y=840 del fotograma de 1080p).
Cada banda es retalla com ho fa l'etapa 02 (TIFINAG_720 × 1,5: y 870–921) i es llegeix amb `lector_tifinag.llegeix_bandes`.
Surt el CER (ha de ser ≈ 0,005) i els errors; el codi de sortida és 1 si el CER passa de 0,01. Els fotogrames no són al repositori."""
import json
import os
import sys

import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import lector_tifinag as LT  # noqa: E402


def dist(a, b):
    ant = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        act = [i]
        for j, cb in enumerate(b, 1):
            act.append(min(ant[j] + 1, act[j - 1] + 1, ant[j - 1] + (ca != cb)))
        ant = act
    return ant[-1]


def main(carpeta):
    veritat = json.load(open(os.path.join(carpeta, "veritat_tifinag.json"), encoding="utf-8"))
    bandes = []
    for v in veritat:
        im = Image.open(os.path.join(carpeta, "fotogrames", f"{v['i']:03d}_banda.png")).convert("RGB")
        bandes.append(np.asarray(im.crop((0, 30, im.width, 81))))      # y 870..921 del fotograma (la banda comença a 840)
    lect = LT.llegeix_bandes(bandes)
    d = n = perfectes = 0
    for v, x in zip(veritat, lect):
        e = dist(v["tif"], x["tifinag"])
        d += e; n += len(v["tif"]); perfectes += (e == 0)
        if e:
            print(f" [{v['i']}] {e} errors\n   veritat: {v['tif']}\n   lector:  {x['tifinag']}")
    cer = d / n
    confs = [g["conf"] for x in lect for g in x["glifs"]]
    print(f"CER {cer:.4f} ({d} errors / {n} car.) · línies perfectes {perfectes}/{len(veritat)} · "
          f"glifs amb conf ≥ {LT.LLINDAR}: {100 * np.mean(np.array(confs) >= LT.LLINDAR):.1f} % de {len(confs)}")
    return 0 if cer <= 0.01 else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
