# -*- coding: utf-8 -*-
"""Diferència de CER ric abans → després per prova, amb IC 95 % per bootstrap (llavor 1114), a partir
de h4*_sortides.json (una entrada per tall i model: prova, video, de, or, dit, model).
ÚS: bootstrap_h4.py <sortides.json> [<altres_sortides.json> ...]  (si n'hi ha dos, compara també
el «després» del primer amb el «després» del segon sobre els talls comuns)"""
import io, json, random, sys


def dist(a, b):
    if a == b:
        return 0
    ant = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        act = [i]
        for j, cb in enumerate(b, 1):
            act.append(min(ant[j] + 1, act[j - 1] + 1, ant[j - 1] + (ca != cb)))
        ant = act
    return ant[-1]


def carrega(p):
    per = {}
    for x in json.load(io.open(p, encoding="utf-8")):
        de = round(x["de"], 2) if isinstance(x["de"], (int, float)) else str(x["de"])
        per.setdefault((x["prova"], x["video"], de), {})[x["model"]] = x
    return per


def ic(parells, n=2000):
    """parells: [(or, dit_a, dit_b)] → CER agregat a, b, Δ i IC."""
    random.seed(1114)
    da = [dist(o, a) for o, a, _ in parells]
    db = [dist(o, b) for o, _, b in parells]
    ln = [len(o) for o, _, _ in parells]
    N = len(parells)
    ca, cb = sum(da) / sum(ln), sum(db) / sum(ln)
    boots = []
    for _ in range(n):
        idx = [random.randrange(N) for _ in range(N)]
        boots.append((sum(db[i] for i in idx) - sum(da[i] for i in idx)) / sum(ln[i] for i in idx))
    boots.sort()
    mill = sum(1 for x, y in zip(da, db) if y < x)
    pitj = sum(1 for x, y in zip(da, db) if y > x)
    return ca, cb, cb - ca, boots[int(0.025 * n)], boots[int(0.975 * n)], mill, pitj


fitxers = sys.argv[1:]
A = carrega(fitxers[0])
proves = sorted({k[0] for k in A})
for prova in proves:
    parells = [(v["abans"]["or"], v["abans"]["dit"], v["després"]["dit"]) for k, v in A.items()
               if k[0] == prova and "abans" in v and "després" in v]
    ca, cb, d, lo, hi, mill, pitj = ic(parells)
    print(f"{fitxers[0].split('/')[-1][:14]:14} {prova:12} n={len(parells):4} {ca:.3f} → {cb:.3f}  Δ={d:+.3f} [{lo:+.3f}, {hi:+.3f}]  milloren {mill} / empitjoren {pitj}")
if len(fitxers) > 1:
    B = carrega(fitxers[1])
    for prova in proves:
        parells = [(A[k]["després"]["or"], A[k]["després"]["dit"], B[k]["després"]["dit"]) for k in A
                   if k[0] == prova and k in B and "després" in A[k] and "després" in B[k]]
        if not parells:
            continue
        ca, cb, d, lo, hi, mill, pitj = ic(parells)
        print(f"després 1 → després 2 {prova:12} n={len(parells):4} {ca:.3f} → {cb:.3f}  Δ={d:+.3f} [{lo:+.3f}, {hi:+.3f}]  milloren {mill} / empitjoren {pitj}")
