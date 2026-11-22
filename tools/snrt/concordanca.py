# -*- coding: utf-8 -*-
"""Concordància so <-> text SENSE parlant natiu (#601, 18-11-2026): dos canals independents han de dir el mateix.
El text surt dels píxels del vídeo (OCR de tifinag); el model acústic escolta l'àudio sense veure'l. Si el que sent s'assembla
al text MÉS que a una vintena de textos d'altres talls del mateix capítol, és molt poc probable que sigui casualitat.

El tifinag de la SNRT segueix la norma IRCAM i no escriu les vocals neutres, que l'ASR sí que posa (el 17-11, CER mediana 0,83):
per això es compara l'ESQUELET consonàntic (sense vocals ni geminació), que no depèn d'aquesta diferència d'escriptura.
Es compara contra controls: la puntuació és el RANG del text real entre els controls, no un CER absolut; i el llindar es fixa
amb la taxa de falsa acceptació (FAR) mesurada barrejant els parells. Pur Python: el fa servir el nucli de Kaggle i les proves.
"""
import random

PLEGA = {"ġ": "g", "ε": "", "ḥ": "h", "ḫ": "x", "ḍ": "d", "ṭ": "t", "ẓ": "z", "ṣ": "s", "š": "c", "ṛ": "r"}
VOCALS = set("aiueo")
RANG_MIN, MARGE_MIN, CONTROLS = 0.95, 0.15, 20


def esquelet(t):
    """Text ric (lletres llatines riques, sense espais ni vocals ni lletres repetides seguides)."""
    out = []
    for c in (t or "").lower():
        c = PLEGA.get(c, c)
        if not c or c in VOCALS or not c.isalpha():
            continue
        if not out or out[-1] != c:
            out.append(c)
    return "".join(out)


def dist(a, b):
    if a == b:
        return 0
    if not a or not b:
        return max(len(a), len(b))
    ant = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        act = [i]
        for j, cb in enumerate(b, 1):
            act.append(min(ant[j] + 1, act[j - 1] + 1, ant[j - 1] + (ca != cb)))
        ant = act
    return ant[-1]


def cer_esq(hip, ref):
    h, r = esquelet(hip), esquelet(ref)
    return dist(h, r) / max(len(r), 1)


def controls_de(i, textos, k=CONTROLS, llavor=1114):
    """k textos d'ALTRES talls del capítol amb esquelet de longitud semblant (0,6–1,6×); determinista per (llavor, i)."""
    n = len(esquelet(textos[i]))
    cand = [j for j, t in enumerate(textos) if j != i and 0.6 * n <= len(esquelet(t)) <= 1.6 * max(n, 1) and esquelet(t) != esquelet(textos[i])]
    random.Random(llavor * 100003 + i).shuffle(cand)
    return [textos[j] for j in cand[:k]]


def puntua(hip, ref, controls):
    """-> {cer, rang, marge}: rang = part dels controls que s'assemblen MENYS a la hipòtesi que el text real (empat = ½);
    marge = CER mediana dels controls − CER del text real."""
    c = cer_esq(hip, ref)
    cs = sorted(cer_esq(hip, x) for x in controls)
    if not cs:
        return {"cer": c, "rang": None, "marge": None}
    rang = sum(1.0 if x > c else 0.5 if x == c else 0.0 for x in cs) / len(cs)
    return {"cer": round(c, 4), "rang": round(rang, 3), "marge": round(cs[len(cs) // 2] - c, 4)}


def alta_certesa(p, rang_min=RANG_MIN, marge_min=MARGE_MIN):
    return p["rang"] is not None and p["rang"] >= rang_min and p["marge"] >= marge_min


def far(hips, textos, llavor=1114, **llindars):
    """Taxa de falsa acceptació: la hipòtesi del tall i s'aparella amb el text d'un altre tall (rotació) i es compta quants
    passen igualment la porta. Si és alta, la porta no distingeix res."""
    n = len(textos)
    if n < 3:
        return None
    desp = (llavor % (n - 1)) + 1
    passa = tot = 0
    for i in range(n):
        j = (i + desp) % n
        ctrl = controls_de(j, textos)
        if not ctrl:
            continue
        tot += 1
        passa += alta_certesa(puntua(hips[i], textos[j], ctrl), **llindars)
    return passa / tot if tot else None
