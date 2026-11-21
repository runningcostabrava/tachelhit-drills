"""La variacio contra la norma de l'IRCAM, varietat per varietat.

Fins ara la taula de variacio barrejava les tres llengues i per aixo la dominaven la k->š i
l'l->r, que son del rifeny i no diuen res del tachelhit. Separades, cada varietat diu la seva
diferencia amb la norma -- que es justament el que aquest projecte necessita: com parla la gent
del Sus i com parla la de l'Atles central, comparat amb el que l'IRCAM escriu.

El metode es el de METODE.md §9.1, sense canvis: dues formes sentides que casen totes dues amb la
MATEIXA paraula escrita, cada una acordada diverses vegades, i l'escapçament separat mirant si
una forma es un tros de la paraula ESCRITA.

    variacio_per_varietat.py [varietat]
"""
import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
MIN_ACORD = 2

var = {r["capitol"]: r["varietat"]
       for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}


def es_tros(curt, llarg):
    i = 0
    for c in llarg:
        if i < len(curt) and curt[i] == c:
            i += 1
    return i == len(curt)


def canvi(a, b):
    if len(a) != len(b):
        return None
    dif = [(x, y) for x, y in zip(a, b) if x != y]
    return dif[0] if len(dif) == 1 else None


#: les ocurrencies, per varietat: forma escrita -> forma sentida -> vegades acordades
dades = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
eps = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
exemple = {}
for l in io.open(MAG / "ocurrencies_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    v = var.get(x["capitol"])
    if not v or not x.get("norma") or x.get("dist") is None or x["dist"] > .35:
        continue
    dades[v][x["norma"]][x["sentit"]] += 1
    eps[v][x["norma"]][x["sentit"]].add(x["capitol"])
    if (x["norma"], x["sentit"]) not in exemple and x.get("catala"):
        exemple[(x["norma"], x["sentit"])] = x["catala"][:52]

nomes = sys.argv[1] if len(sys.argv) > 1 else None
for v in sorted(dades):
    if nomes and v != nomes:
        continue
    canvis = Counter()
    parelles = []
    for escrit, formes in dades[v].items():
        bones = {f: n for f, n in formes.items() if n >= MIN_ACORD}
        if len(bones) < 2:
            continue
        ee = esquelet(escrit)
        vistes = sorted(bones.items(), key=lambda kv: -kv[1])
        for i in range(len(vistes)):
            for j in range(i + 1, len(vistes)):
                (fa, na), (fb, nb) = vistes[i], vistes[j]
                ea, eb = esquelet(fa), esquelet(fb)
                if not ea or not eb or ea == eb:
                    continue
                curt, llarg = (ea, eb) if len(ea) <= len(eb) else (eb, ea)
                tots_dos = (ee and len(ea) < len(ee) and len(eb) < len(ee)
                            and es_tros(ea, ee) and es_tros(eb, ee))
                if es_tros(curt, llarg) or tots_dos:
                    continue
                if len(ea) < 3 or len(eb) < 3 or abs(len(ea) - len(eb)) > 2:
                    continue
                c = canvi(ea, eb)
                parelles.append((min(na, nb), escrit, fa, na, fb, nb, c))
                if c:
                    canvis[tuple(sorted(c))] += min(na, nb)
    parelles.sort(reverse=True)
    print(f"\n=== {v}: {len(parelles)} parelles de variacio")
    print(f"{'escrit':<14}{'forma A':<14}{'forma B':<14}{'canvi':>7}  significat")
    for pes, escrit, fa, na, fb, nb, c in parelles[:12]:
        et = f"{c[0]}>{c[1]}" if c else ""
        print(f"{escrit[:13]:<14}{(fa + '(' + str(na) + ')')[:13]:<14}"
              f"{(fb + '(' + str(nb) + ')')[:13]:<14}{et:>7}  "
              f"{exemple.get((escrit, fa), '')[:34]}")
    if canvis:
        print("   canvis: " + " · ".join(f"{a}~{b} {n}" for (a, b), n in canvis.most_common(8)))
