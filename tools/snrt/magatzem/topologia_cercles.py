"""Què distingeix les lletres-cercle: la TOPOLOGIA, no la forma.

L'intent anterior (erosionar i mirar què queda) donava «taca» per a totes: l'erosió treu
l'anella i deixa el cos, que és igual a totes. El que de debò les separa es veu comptant:

  - quants FORATS tanca la figura (una barra vertical parteix l'interior en dos);
  - quants TROSSOS de tinta té (un punt al mig és un tros a part; una barra enganxada, no).

Això és el que l'IoU no pot veure —hi pesa l'anella, que és comuna— i és barat de mesurar.
D'aquí surt la regla de desempat, treta de les plantilles i no del meu record.
"""
import sys

import numpy as np
from scipy import ndimage

FAB = r"C:\Users\josep\app2\tachelhit-drills.worktrees\lector-tawnza\tools\snrt\fabrica"
sys.path.insert(0, FAB)
import tifinag_plantilles as PL  # noqa: E402

z = np.load(PL.NPZ, allow_pickle=True)
signes = [str(s) for s in z["signes"]]
masc = {s: (np.asarray(m) > 0) for s, m in zip(signes, z["mascares"])}

VUIT = np.ones((3, 3), bool)


def descriu(m):
    #: els trossos de tinta, amb veïnatge de vuit (una diagonal encara és el mateix traç)
    _, n_tinta = ndimage.label(m, structure=VUIT)
    #: els forats: el fons que NO toca la vora de la imatge
    fons = ~m
    lab, n = ndimage.label(fons, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool))
    vora = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    forats = [i for i in range(1, n + 1) if i not in vora]
    mides = sorted((int((lab == i).sum()) for i in forats), reverse=True)
    return n_tinta, len(forats), mides


print(f"{'signe':>6}  {'trossos':>8}  {'forats':>7}  mides dels forats")
fam = {}
for s in signes:
    if s in ",?:.":
        continue
    t, f, mides = descriu(masc[s])
    fam[s] = (t, f)
    print(f"{s:>6}  {t:>8}  {f:>7}  {mides[:4]}")

print("\nagrupats per (trossos, forats) — els que comparteixen grup són els que es confonen:")
per = {}
for s, k in fam.items():
    per.setdefault(k, []).append(s)
for k, v in sorted(per.items()):
    if len(v) > 1:
        print(f"   trossos {k[0]}, forats {k[1]}:  {' '.join(v)}")
print("\nels que tenen grup propi (no es poden confondre per topologia):")
print("   " + " ".join(s for s, v in ((s, per[k]) for s, k in fam.items()) if len(v) == 1))
