"""Torna a llegir el tifinag dels capítols a partir del vídeo, amb el lector d'avui.

Per què. El text que la fàbrica va deixar el va escriure `plantilles-segmentador-v1`. Al capítol
del Goughelt, rellegir les mateixes franges amb el lector d'ara va pujar la taxa d'acord amb el
so de 10,7 % a 17,1 % sense cap dada nova. Els 26 capítols encara porten el text vell, i la
dispersió entre ells (del 37,9 % al no-res, amb el mateix model escoltant) diu que el problema
és l'ull, no l'orella.

Com. Una sola passada d'ffmpeg per capítol, un fotograma per segon, retallat a la franja del
tifinag (y 870-921 de 1080p, la geometria estàndard de `comu.TIFINAG_720` × 1,5). Després, per a
cada rèplica es tria el fotograma del seu punt mitjà. És el que fa la fàbrica; aquí es repeteix
perquè les imatges no es van guardar a la còpia d'HF, només el text.

Surt `rellegit_bo/<slug>.json` amb el text nou per rèplica. No toca el visor ni producció: la
comparació la fa `acord_26.py` després, i només s'adoptarà si el número puja.

    rellegeix_els_26.py [--nomes N] [slug ...]
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image

FAB = r"C:\Users\josep\app2\tachelhit-drills.worktrees\lector-tawnza\tools\snrt\fabrica"
sys.path.insert(0, FAB)
import lector_tifinag as L  # noqa: E402

sys.path.insert(0, r"E:/tamazight/_magatzem")
import desempat_topologic as DT  # noqa: E402

#: el desempat per topologia: +5,3 punts al capítol on hi havia confusions de la família dels
#: cercles, 0,00 on no n'hi havia. Conservador: només actua quan els dos primers empaten.
DT.posa_el_desempat()

VIDEOS = Path(r"E:\tamazight\_videos")
VISOR = Path(r"E:\tamazight\_visor")
DESTI = Path(r"E:\tamazight/_magatzem\rellegit_bo")
#: la franja NO és al mateix lloc a tots els capítols: 20 de 25 la tenen fora de l'estàndard i
#: n'hi ha set posicions diferents. Retallar sempre a y 870 escapçava els signes i la relectura
#: donava zero al millor capítol de tots. La mesura la fa la fàbrica (`geometria.json`).
GEO = json.load(io.open(Path(r"E:/tamazight/_magatzem\geometries.json"), encoding="utf-8"))


def franja_de(slug):
    g = (GEO.get(slug) or {}).get("TIFINAG_720") or [580, 614]
    return int(round(g[0] * 1.5)), int(round((g[1] - g[0]) * 1.5)), bool((GEO.get(slug) or {}).get("estandard"))

DESTI.mkdir(parents=True, exist_ok=True)
#: `--nomes N` es menja el seu valor: si no, el numero es colaria com si fos un capitol
nomes = 0
resta = sys.argv[1:]
if "--nomes" in resta:
    i = resta.index("--nomes")
    nomes = int(resta[i + 1])
    resta = resta[:i] + resta[i + 2:]
args = [a for a in resta if not a.startswith("--")]

slugs = args or sorted(d.name for d in VISOR.iterdir()
                       if (d / "subtitols.jsonl").exists() and (VIDEOS / f"{d.name}.mp4").exists())
if nomes:
    slugs = slugs[:nomes]
print(f"capítols amb vídeo i text: {len(slugs)}")

for n, slug in enumerate(slugs, 1):
    desti = DESTI / f"{slug}.json"
    if desti.exists():
        print(f"[{n}/{len(slugs)}] {slug[:14]}… ja rellegit")
        continue
    video = VIDEOS / f"{slug}.mp4"
    y0_f, alt_f, estandard = franja_de(slug)
    files = [json.loads(l) for l in io.open(VISOR / slug / "subtitols.jsonl", encoding="utf-8")
             if l.strip()]
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        #: una passada sola: un fotograma per segon, ja retallat a la franja. Fer un «seek» per
        #: rèplica serien centenars de crides a ffmpeg i trigaria desenes de minuts per capítol.
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video),
                            "-vf", f"fps=1,crop=iw:{alt_f}:0:{y0_f}",
                            os.path.join(tmp, "%06d.png")], capture_output=True)
        franges = sorted(Path(tmp).glob("*.png"))
        if not franges:
            print(f"[{n}/{len(slugs)}] {slug[:14]}… ffmpeg no ha tret cap franja "
                  f"({r.stderr.decode('utf-8','replace')[:90]})")
            continue
        #: l'escala es mesura una sola vegada per capítol, d'una mostra, com fa la fàbrica
        mostra = [np.asarray(Image.open(f).convert("RGB"))
                  for f in franges[::max(1, len(franges) // 40)][:40]]
        esc = L.estima_escala(mostra)

        llegit, errors = {}, 0
        for x in files:
            mig = int(round((float(x["t_ini"]) + float(x["t_fi"])) / 2))
            #: les franges comencen a 1 i van d'un en un segon
            i = min(max(mig, 1), len(franges)) - 1
            try:
                a = np.asarray(Image.open(franges[i]).convert("RGB"))
                llegit[str(x["k"])] = (L.llegeix_banda(a, esc).get("tifinag") or "").strip()
            except Exception:
                llegit[str(x["k"])] = ""
                errors += 1
    json.dump({"slug": slug, "franja": [y0_f, alt_f], "estandard": estandard,
               "desempat": "topologic", "escala": list(esc) if esc else None, "franges": len(franges),
               "linies": len(files), "errors": errors, "llegit": llegit,
               "lector": "lector_tifinag lector-tawnza (19-11-2026)"},
              io.open(desti, "w", encoding="utf-8"), ensure_ascii=False)
    amb = sum(1 for v in llegit.values() if v)
    print(f"[{n}/{len(slugs)}] {slug[:14]}… {len(files)} rèpliques, {amb} amb text, "
          f"escala {esc}  [{time.time()-t0:.0f}s]", flush=True)

print(f"\nfet. a {DESTI}")
