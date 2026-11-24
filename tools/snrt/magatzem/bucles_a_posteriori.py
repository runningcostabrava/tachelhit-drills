"""Quant pesen els bucles al chrF d'una tirada ja feta, sense tornar a descodificar.

Es plega tota repeticio seguida d'un n-grama de paraules (n = 1..4) a una sola aparicio i es
recalcula el chrF sobre les mateixes files. No es el mateix que `no_repeat_ngram_size=3` (que
canvia el que el model tria despres), pero en dona una fita barata.

    python bucles_a_posteriori.py E:/tamazight/_magatzem/tirades/veu_ar_2/resultat.json
"""
import io
import json
import sys
from collections import Counter


def chrf(hip, ref, n=6, beta=2.0):
    def grams(t, k):
        t = " ".join(t.split())
        return [t[i:i + k] for i in range(max(0, len(t) - k + 1))]
    ps, rs = [], []
    for k in range(1, n + 1):
        h, r = grams(hip, k), grams(ref, k)
        if not h or not r:
            continue
        ch, cr = Counter(h), Counter(r)
        com = sum((ch & cr).values())
        ps.append(com / len(h))
        rs.append(com / len(r))
    if not ps:
        return 0.0
    p, r = sum(ps) / len(ps), sum(rs) / len(rs)
    if p + r == 0:
        return 0.0
    b2 = beta * beta
    return (1 + b2) * p * r / (b2 * p + r)


def plega(t):
    w = t.split()
    canvia = True
    while canvia:
        canvia = False
        for n in range(1, 5):
            i = 0
            while i + 2 * n <= len(w):
                if w[i:i + n] == w[i + n:i + 2 * n]:
                    del w[i + n:i + 2 * n]
                    canvia = True
                else:
                    i += 1
    return " ".join(w)


r = json.load(io.open(sys.argv[1], encoding="utf-8"))
for k, v in r["tests"].items():
    f = v["files"]
    abans = sum(chrf(x["model"].strip(), x["ar"]) for x in f) / len(f)
    despres = sum(chrf(plega(x["model"].strip()), x["ar"]) for x in f) / len(f)
    amb = sum(1 for x in f if plega(x["model"].strip()) != " ".join(x["model"].split()))
    print(f"{k}: chrF {abans:.4f} -> plegant bucles {despres:.4f} · files amb repeticio {amb}/{len(f)}")
