"""Desfer les cadenes enganxades amb el lexic, i comprovar-ho amb l'acord.

En Pablo: «si el resultat de l'escolta del nostre model es una cadena llarga podries fer el cami
invers, ja que tenim la traduccio de l'arab intentar esbrinar les paraules que hi ha».

El problema existeix i esta mesurat: de 79.969 paraules sentides, **1.816 (2,3 %) tenen 14
lletres o mes** -- `nstwrḫbinanġεdaġrmin`, `mnnismimtqyimzwarmian`. Son runs que el descodificador
no ha sabut separar, i una de sola pot tombar la replica sencera.

El tall es fa amb programacio dinamica sobre el **lexic que ja tenim** (`fitxa_fiabilitat.tsv`):
de totes les maneres de partir la cadena en formes conegudes, la que surti millor puntuada. Cada
forma puntua pel logaritme de les vegades que l'hem sentida i per com de fiable es; cada tall
costa una mica, perque si no sortirien deu paraules d'una lletra.

**I la prova que el pot refutar:** si el tall es bo, l'esquelet no canvia (les lletres son les
mateixes) pero les PARAULES casen millor amb les del subtitol. Es mesura l'acord de paraules
abans i despres sobre les mateixes repliques. Si no puja, el tall no serveix i prou.
"""
import csv
import io
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402
from alinea_paraules import alinea  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
LLARGA = 14          #: a partir d'aqui es sospita que son paraules enganxades
MIN_TROS = 5         #: cap tros mes curt que aixo
COST_TALL = 7.0      #: el que costa posar un tall


def prop(a, b):
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


#: --- el lexic, amb una puntuacio per forma ---
punts = {}
for r in csv.DictReader(io.open(MAG / "fitxa_fiabilitat.tsv", encoding="utf-8", newline=""),
                        delimiter="\t"):
    f = (r.get("forma") or "").strip().lower()
    if len(f) < MIN_TROS:
        continue
    #: NOMES les formes de les quals ens fiem. Amb les 39.274 el tallador podia enrajolar
    #: qualsevol cadena amb bocins sense sentit i l'acord no pujava gens (6,9 % -> 6,9 %).
    v = r.get("verdicte", "")
    if v not in ("de llibre", "sòlida", "la norma no l'escriu"):
        continue
    vegades = int(r.get("vegades") or 0)
    bo = {"de llibre": 1.6, "sòlida": 1.4, "la norma no l'escriu": 1.4}[v]
    punts[f] = math.log(1 + vegades) * bo
print(f"lèxic: {len(punts)} formes\n")


def talla(cadena):
    """La millor particio de `cadena` en formes conegudes, o None si no n'hi ha cap de sencera."""
    c = cadena.lower()
    n = len(c)
    millor = [(-1e9, None)] * (n + 1)
    millor[0] = (0.0, None)
    for i in range(1, n + 1):
        for j in range(max(0, i - 18), i - MIN_TROS + 1):
            if millor[j][0] <= -1e8:
                continue
            p = punts.get(c[j:i])
            if p is None:
                continue
            v = millor[j][0] + p - COST_TALL
            if v > millor[i][0]:
                millor[i] = (v, j)
    if millor[n][0] <= -1e8:
        return None
    trossos, i = [], n
    while i > 0:
        j = millor[i][1]
        trossos.append(cadena[j:i])
        i = j
    return list(reversed(trossos))


#: --- sobre les repliques de debo ---
sentit = {}
for l in io.open(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x
triat = {}
for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        triat[x["id"]] = x

n_rep = n_talls = 0
abans_ok = abans_tot = despres_ok = despres_tot = 0
exemples = []
for ident, x in triat.items():
    ull = [w for w in (x.get("tifinag") or "").split() if w.strip()]
    s = sentit.get(ident)
    if not ull or not s:
        continue
    paraules = [p["p"] for p in (s.get("paraules") or []) if (p.get("p") or "").strip()]
    if not paraules or not any(len(p) >= LLARGA for p in paraules):
        continue
    n_rep += 1
    noves = []
    canviat = False
    for p in paraules:
        if len(p) >= LLARGA:
            t = talla(p)
            if t and len(t) > 1:
                noves.extend(t)
                canviat = True
                n_talls += 1
                if len(exemples) < 8:
                    exemples.append((p, " ".join(t)))
                continue
        noves.append(p)
    if not canviat:
        continue
    for llista, ok, tot in (("a", 0, 0), ("d", 0, 0)):
        pass
    for i, j in alinea(paraules, ull):
        if i is None:
            continue
        abans_tot += 1
        if j is not None and prop(esquelet(paraules[i]), esquelet(ull[j])) <= .35:
            abans_ok += 1
    for i, j in alinea(noves, ull):
        if i is None:
            continue
        despres_tot += 1
        if j is not None and prop(esquelet(noves[i]), esquelet(ull[j])) <= .35:
            despres_ok += 1

print(f"{n_rep} rèpliques amb alguna cadena llarga · {n_talls} cadenes tallades\n")
print(f"{'':<12}{'paraules':>10}{'casen':>8}{'%':>8}")
print(f"{'abans':<12}{abans_tot:10d}{abans_ok:8d}{100*abans_ok/max(1,abans_tot):8.1f}")
print(f"{'després':<12}{despres_tot:10d}{despres_ok:8d}{100*despres_ok/max(1,despres_tot):8.1f}")
print("\nexemples de talls:")
for a, b in exemples:
    print(f"   {a}  ->  {b}")
print("\nSi el percentatge no puja, el tall no serveix: les lletres són les mateixes i l'única")
print("cosa que canvia és on es parteixen.")
