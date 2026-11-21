"""Aparella les paraules de l'orella amb les de l'ull per ORDRE, no per semblança.

L'error d'abans: per a cada paraula sentida buscava la més propera de la línia, cadascuna pel
seu compte. Quan l'ordre o el nombre de paraules no casa, això aparella coses que no tenen res
a veure, i la taula estàndard ↔ dialecte s'omple de parelles inventades (`nnk` amb `ungal`).

És la lliçó del 29-10-2026: **aparellar per ordre**. Aquí es fa una alineació global de les dues
llistes de paraules (Needleman-Wunsch amb el cost de l'esquelet consonàntic): cada paraula de
l'orella s'aparella amb com a molt una de l'ull, sense creuaments, o amb cap.

Surt `parelles_alineades.jsonl`: una línia per paraula sentida, amb la seva parella si en té.
"""
import io
import json
import unicodedata
from pathlib import Path

MAG = Path(r"E:\tamazight\_magatzem")
ACORD = MAG / "acord_26.jsonl"
SENTIT = Path(r"E:\tamazight\_sentit\sortida_26\sentit.jsonl")
DESTI = MAG / "parelles_alineades.jsonl"

TIF = {"ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "ḍ", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k", "ⵀ": "h",
       "ⵃ": "ḥ", "ⵄ": "ε", "ⵅ": "ḫ", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l", "ⵎ": "m", "ⵏ": "n",
       "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "ġ", "ⵙ": "s", "ⵚ": "ṣ", "ⵛ": "š", "ⵜ": "t", "ⵟ": "ṭ",
       "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "ẓ", "ⵯ": "w"}
LLATI = {"ɣ": "ġ", "γ": "ġ", "ɛ": "ε", "ṛ": "r", "c": "š", "x": "ḫ", "χ": "ḫ", "ž": "j",
         "ǧ": "j", "ʷ": "w", "v": "f", "p": "b", "o": "u"}
VOCALS = set("aeiou")


def a_llati(t, de_tifinag):
    fora = []
    for c in unicodedata.normalize("NFC", t or "").lower():
        c = TIF.get(c) if de_tifinag else LLATI.get(c, c)
        if c and c.isalpha():
            fora.append(c)
    return "".join(fora)


def esquelet(t):
    return "".join(c for c in t if c not in VOCALS)


def lev(a, b):
    if not a or not b:
        return max(len(a), len(b))
    ant = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        act = [i]
        for j, cb in enumerate(b, 1):
            act.append(min(ant[j] + 1, act[j - 1] + 1, ant[j - 1] + (ca != cb)))
        ant = act
    return ant[-1]


def distancia(a, b):
    ea, eb = esquelet(a), esquelet(b)
    if not ea or not eb:
        return 1.0
    return lev(ea, eb) / max(len(ea), len(eb))


FORAT = 0.8   #: deixar una paraula sense parella costa això; per sobre, val més no aparellar-la


def alinea(orella, ull):
    """Needleman-Wunsch sobre dues llistes de paraules. Torna parelles (i, j) o (i, None)."""
    n, m = len(orella), len(ull)
    d = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        d[i][0] = d[i - 1][0] + FORAT
    for j in range(1, m + 1):
        d[0][j] = d[0][j - 1] + FORAT
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j - 1] + distancia(orella[i - 1], ull[j - 1]),
                          d[i - 1][j] + FORAT, d[i][j - 1] + FORAT)
    parelles, i, j = [], n, m
    while i > 0:
        if j > 0 and abs(d[i][j] - (d[i - 1][j - 1] + distancia(orella[i - 1], ull[j - 1]))) < 1e-9:
            parelles.append((i - 1, j - 1)); i, j = i - 1, j - 1
        elif abs(d[i][j] - (d[i - 1][j] + FORAT)) < 1e-9:
            parelles.append((i - 1, None)); i -= 1
        else:
            j -= 1
    return parelles[::-1]


sentit = {}
for l in io.open(SENTIT, encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x


def main():
    n_linies = n_par = n_sense = 0
    with io.open(DESTI, "w", encoding="utf-8", newline="\n") as f:
        for l in io.open(ACORD, encoding="utf-8"):
            if not l.strip():
                continue
            r = json.loads(l)
            s = sentit.get(r["id"], {})
            paraules = s.get("paraules") or []
            ull = [w for w in (r.get("tifinag") or "").split() if w.strip()]
            if not paraules or not ull:
                continue
            n_linies += 1
            o_lat = [a_llati(p["p"], False) for p in paraules]
            u_lat = [a_llati(w, True) for w in ull]
            for i, j in alinea(o_lat, u_lat):
                p = paraules[i]
                parella = ull[j] if j is not None else None
                dist = distancia(o_lat[i], u_lat[j]) if j is not None else None
                if j is None:
                    n_sense += 1
                else:
                    n_par += 1
                f.write(json.dumps({"id": r["id"], "capitol": r["capitol"],
                                    "parla": p["p"], "conf": p["c"],
                                    "norma": parella, "norma_llati": u_lat[j] if j is not None else None,
                                    "dist": None if dist is None else round(dist, 3),
                                    "catala": r.get("catala")}, ensure_ascii=False) + "\n")

    print(f"línies alineades: {n_linies}")
    print(f"   paraules amb parella: {n_par}")
    print(f"   paraules sense parella: {n_sense}")
    print(f"desat a {DESTI}")


if __name__ == "__main__":
    main()
