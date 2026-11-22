"""Què perd la binarització a les franges amb fons carregat.

Sis capítols perden text (fins al 40 % del que l'àrab fa esperar, i una de cada cinc rèpliques
muda). Mirant la franja d'un d'ells es veu que el subtítol va sobre un fons fosc, vermell i ple
de branques. Aquí es mira QUÈ passa, pas a pas, en comptes de suposar-ho:

  `blanc`  els píxels prou clars i poc saturats
  `fosc`   els prou foscos (la vora del text)
  final    els blancs que tenen vora fosca a banda i banda

Es desa una imatge amb els quatre nivells, un sota l'altre, per veure en quin es perd el text.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

FAB = r"C:\Users\josep\app2\tachelhit-drills.worktrees\topologia\tools\snrt\fabrica"
sys.path.insert(0, FAB)
import tifinag_segmenta as SEG  # noqa: E402

SORTIDA = Path(r"C:\Users\josep\AppData\Local\Temp\claude\b9bc3d8a9f758b87"
               r"\104dfaed-6dfd-4f67-bac4-fece7f991424\scratchpad")
CASOS = [
    ("caxyzjdttlgivxihlcntrzxbtrrfvwhnmhphrvtx", 62, 863, 51),   # fons vermell: perd text
    ("bueyrhjvjyaleocffcrxdtmeqfpfgqqwauwesbrw", 220, 861, 51),  # va bé: per comparar
]

trossos = []
for slug, t, y0, alt in CASOS:
    p = SORTIDA / f"bin_{slug[:8]}_{t}.png"
    subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i",
                    str(Path(r"E:\tamazight\_videos") / f"{slug}.mp4"),
                    "-frames:v", "1", "-vf", f"crop=iw:{alt}:0:{y0}", "-y", str(p)], check=False)
    if not p.exists():
        print(f"{slug[:12]}: sense fotograma")
        continue
    a = np.asarray(Image.open(p).convert("RGB"))
    mask, blanc, fosc = SEG.mascara_lletra(a)
    print(f"{slug[:12]} t={t}:  blanc {blanc.mean()*100:5.1f}%   fosc {fosc.mean()*100:5.1f}%   "
          f"final {mask.mean()*100:5.1f}%")
    gris = np.asarray(Image.open(p).convert("L"))
    trossos += [gris,
                (blanc * 255).astype(np.uint8),
                (fosc * 255).astype(np.uint8),
                (mask * 255).astype(np.uint8)]

if trossos:
    w = max(t.shape[1] for t in trossos)
    h = sum(t.shape[0] + 6 for t in trossos)
    out = Image.new("L", (w, h), 40)
    y = 0
    for t in trossos:
        out.paste(Image.fromarray(t), (0, y))
        y += t.shape[0] + 6
    out.save(SORTIDA / "binaritzacio.png")
    print(f"\ndesat a {SORTIDA / 'binaritzacio.png'}")
    print("ordre per cas: original, blanc, fosc, final")
