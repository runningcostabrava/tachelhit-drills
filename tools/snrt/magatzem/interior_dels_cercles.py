"""Què hi ha DINS de cada lletra-cercle, mesurat de les plantilles mateixes.

Sis lletres del tifinag són una anella amb una marca diferent a dins (ⴱ ⵀ ⵔ ⵕ ⵙ ⵚ: se solapen
entre 0,74 i 0,88). L'IoU global no les pot separar, perquè l'anella és la major part dels
píxels i la comparteixen totes: el que les distingeix són quatre píxels de dins.

En comptes d'endevinar quina marca porta cadascuna, es mesura de la plantilla: s'omple la
figura, se'n treu l'anella, i el que queda és la marca interior. D'ella se'n diu quants píxels
té, on és (a dalt, al mig, a baix) i quina forma (alta i estreta = barra; rodona = punt).

D'aquí ha de sortir la regla de desempat, i ha de sortir de les dades i no del meu record de com
s'escriu el tifinag.
"""
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

FAB = r"C:\Users\josep\app2\tachelhit-drills.worktrees\lector-tawnza\tools\snrt\fabrica"
sys.path.insert(0, FAB)
import tifinag_plantilles as PL  # noqa: E402

z = np.load(PL.NPZ, allow_pickle=True)
signes = [str(s) for s in z["signes"]]
masc = {s: (np.asarray(m) > 0) for s, m in zip(signes, z["mascares"])}

FAMILIA = ["ⴱ", "ⵀ", "ⵔ", "ⵕ", "ⵙ", "ⵚ", "ⵄ", "ⵠ"]
print(f"{'signe':>6}  {'mida':>8}  {'tinta':>6}  {'interior':>9}  {'on':>12}  {'forma':>14}")
for s in FAMILIA:
    m = masc.get(s)
    if m is None:
        continue
    h, w = m.shape
    #: omplir la figura i treure-li l'anella: el que queda és el que hi ha tancat a dins
    ple = ndimage.binary_fill_holes(m)
    dins = ple & ~m
    #: la marca interior és la tinta que hi ha dins del forat, no el forat mateix
    forat = dins
    marca = m & ndimage.binary_erosion(ple, iterations=2)
    n = int(marca.sum())
    if n == 0:
        on, forma = "—", "res (anella neta)"
    else:
        ys, xs = np.nonzero(marca)
        cy = (ys.mean() + .5) / h
        alt_rel = (ys.max() - ys.min() + 1) / h
        amp_rel = (xs.max() - xs.min() + 1) / w
        on = "a dalt" if cy < .38 else ("a baix" if cy > .62 else "al mig")
        if alt_rel > .55 and amp_rel < .35:
            forma = "barra vertical"
        elif amp_rel > .55 and alt_rel < .35:
            forma = "barra horitzontal"
        else:
            forma = "punt" if n <= 12 else "taca"
    print(f"{s:>6}  {h:>3}x{w:<4}  {int(m.sum()):>6}  {n:>9}  {on:>12}  {forma:>16}")

print("\nforat interior (píxels tancats per l'anella, sense tinta):")
for s in FAMILIA:
    m = masc.get(s)
    if m is None:
        continue
    ple = ndimage.binary_fill_holes(m)
    print(f"   {s}: {int((ple & ~m).sum()):4d} píxels de forat")
