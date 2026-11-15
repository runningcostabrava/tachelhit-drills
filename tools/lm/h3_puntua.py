# -*- coding: utf-8 -*-
"""Puntua els resultats del kernel H3 contra la veritat humana, amb el MATEIX codi que va donar
el CER 0,210 (net + dist de veritat_cancons.py), i a més amb l'alfabet plegat (la veritat escriu
x, ɣ, c, ° i el model ḫ, ġ, š, w: una lletra diferent per convenció no és un error de l'oïda).

WER partit com al registre: «frontera» (els mateixos caràcters amb els espais en un altre lloc)
contra «de debò».

ÚS: h3_puntua.py <h3_resultats.json> [sortida.md]
"""
import io
import json
import re
import sys

PLEC = (("ɣ", "ġ"), ("x", "ḫ"), ("c", "š"), ("ɛ", "ε"), ("ṛ", "r"), ("°", "w"), ("ʷ", "w"))


def net(s):
    s = (s or "").lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())


def plega(s):
    for a, b in PLEC:
        s = s.replace(a, b)
    return s


def dist(a, b):
    if len(a) < len(b):
        a, b = b, a
    fila = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        nova = [i]
        for j, cb in enumerate(b, 1):
            nova.append(min(fila[j] + 1, nova[j - 1] + 1, fila[j - 1] + (ca != cb)))
        fila = nova
    return fila[-1]


def cer(h, v):
    return dist(h, v) / max(1, len(v))


def wer(h, v):
    return dist(h.split(), v.split()) / max(1, len(v.split()))


def puntua(versos, clau, mena, plegat):
    sel = [x for x in versos if x["mena"] == mena and x.get(clau) is not None]
    if not sel:
        return None
    c = w = wf = n = 0
    for x in sel:
        v, h = net(x["veritat"]), net(x[clau])
        if plegat:
            v, h = plega(v), plega(h)
        c += cer(h, v)
        w += wer(h, v)
        #: frontera: mateixes lletres sense espais → l'error és només de tall
        wf += wer(h, v) if h.replace(" ", "") == v.replace(" ", "") else 0
        n += 1
    return {"n": n, "cer": c / n, "wer": w / n, "wer_frontera": wf / n}


if __name__ == "__main__":
    d = json.load(io.open(sys.argv[1], encoding="utf-8"))
    versos = d["versos"]
    claus = ["shi", "greedy"] + d["configs"]
    linies = ["| descodificació | n | CER | CER plegat | WER | WER plegat | de la qual, frontera |", "|---|---|---|---|---|---|---|"]
    for mena in ("parlat", "cantat"):
        linies.append(f"| **{mena}** | | | | | | |")
        for k in claus:
            a, b = puntua(versos, k, mena, False), puntua(versos, k, mena, True)
            if a:
                linies.append(f"| {k} | {a['n']} | {a['cer']:.3f} | {b['cer']:.3f} | {a['wer']:.3f} | {b['wer']:.3f} | {b['wer_frontera']:.3f} |")
    out = "\n".join(linies)
    print(out)
    if len(sys.argv) > 2:
        io.open(sys.argv[2], "w", encoding="utf-8").write(out + "\n")
    # tres exemples on el millor LM canvia el text
    millor = None
    for k in d["configs"]:
        p = puntua(versos, k, "parlat", True)
        if p and (millor is None or p["cer"] < millor[1]):
            millor = (k, p["cer"])
    if millor:
        print(f"\nmillor: {millor[0]} CER plegat {millor[1]:.3f}")
        shown = 0
        for x in versos:
            if x["mena"] == "parlat" and x.get(millor[0]) and net(x[millor[0]]) != net(x["greedy"]):
                print(f"  V: {x['veritat']}\n  G: {x['greedy']}\n  L: {x[millor[0]]}\n")
                shown += 1
                if shown >= 6:
                    break
