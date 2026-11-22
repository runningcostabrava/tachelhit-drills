"""Quines plantilles són un cercle amb una marca a dins, i quant s'assemblen entre elles.

La confusió ⵙ/ⵀ no és un cas aïllat: l'anella és la major part dels píxels i la comparteixen
totes dues, i el que de debò les distingeix —un punt o una barra— són quatre píxels que amb
prou feines mouen l'IoU. Si hi ha més lletres fetes així, totes han de tenir el mateix problema,
i val més saber-ho abans de posar un pegat per a una sola parella.

Es mesura, per a cada parella de plantilles, quant se solapen. Les que passin d'un llindar alt
són les que el lector no pot distingir per forma global.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

FAB = r"C:\Users\josep\app2\tachelhit-drills.worktrees\lector-tawnza\tools\snrt\fabrica"
sys.path.insert(0, FAB)
import tifinag_plantilles as PL  # noqa: E402

SORTIDA = Path(r"C:\Users\josep\AppData\Local\Temp\claude\b9bc3d8a9f758b87"
               r"\104dfaed-6dfd-4f67-bac4-fece7f991424\scratchpad")

z = np.load(PL.NPZ, allow_pickle=True)
signes = [str(s) for s in z["signes"]]
masc = [np.asarray(m) > 0 for m in z["mascares"]]
print(f"plantilles: {len(signes)}")


def iou(a, b):
    h = max(a.shape[0], b.shape[0]); w = max(a.shape[1], b.shape[1])
    A = np.zeros((h, w), bool); B = np.zeros((h, w), bool)
    A[:a.shape[0], :a.shape[1]] = a
    B[:b.shape[0], :b.shape[1]] = b
    u = (A | B).sum()
    return (A & B).sum() / u if u else 0.0


parelles = []
for i in range(len(signes)):
    for j in range(i + 1, len(signes)):
        v = iou(masc[i], masc[j])
        parelles.append((v, signes[i], signes[j]))
parelles.sort(reverse=True)

print("\nles plantilles que més s'assemblen entre elles:")
for v, a, b in parelles[:12]:
    print(f"   {a} / {b}   solapament {v:.3f}")

#: una imatge amb totes, per veure-les
alt = max(m.shape[0] for m in masc)
amp = sum(m.shape[1] + 8 for m in masc)
out = Image.new("L", (amp, alt + 2), 0)
x = 0
for m in masc:
    out.paste(Image.fromarray((m * 255).astype(np.uint8)), (x, 0))
    x += m.shape[1] + 8
out = out.resize((out.width * 3, out.height * 3), Image.NEAREST)
out.save(SORTIDA / "plantilles_totes.png")
print(f"\nl'ordre de la imatge: {' '.join(signes)}")
print(f"desades a {SORTIDA / 'plantilles_totes.png'}")
