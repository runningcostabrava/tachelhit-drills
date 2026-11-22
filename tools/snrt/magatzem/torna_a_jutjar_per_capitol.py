"""La regla d'acceptacio del cercle, jutjada amb la unitat correcta.

`cercle_virtuos.py:122` decideix si una ronda s'adopta:

    adopta = not absents and not empitjora and len(millora) >= 2

i els veredictes «millora»/«empitjora» surten d'un interval de confianca que
**remostreja FRASES**. Pero les frases d'un mateix capitol no son independents: mateixa veu,
mateix so, mateix lector d'ull, mateix tema. Si un capitol surt be, totes les seves frases
surten be alhora. Remostrejant frases, l'interval es fa estret per una independencia que no hi
es, i una diferencia que ve d'UN capitol es llegeix com a diferencia del model.

Quants capitols hi ha de debo darrere de cada prova:

    zouhir-tests 4 · tfa-226 8 · test-fora 5 · snrt-retingut 4 (per a 1.127 frases)

Aqui es remostreja **el capitol**, que es la unitat que es va mostrejar de debo, i es torna a
aplicar la regla. Es aparellat: a cada replica es trien capitols amb reposicio i es calcula la
diferencia dels dos models **sobre els mateixos capitols**.

No canvia cap fitxer del cercle: nomes diu si el veredicte aguanta.
"""
import io
import json
import random
from collections import defaultdict
from pathlib import Path

import sys
SORTIDA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"E:/tamazight/_magatzem/ronda/sortida")
VEGADES = 2000
LLAVOR = 20261120


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


#: mateixa mesura que `interval_del_tfa.py`: CER micro (errors totals / lletres totals),
#: text cru, aparellat per (video, de, or). L'UNIC canvi es QUE es remostreja.
files = json.load(io.open(SORTIDA / "snrt_B_sortides.json", encoding="utf-8"))
per = defaultdict(dict)
for x in files:
    quin = "abans" if (x.get("model") or "").startswith("abans") else "despres"
    clau = (x.get("video"), str(x.get("de")), x.get("or"))
    d = per[x["prova"]].setdefault(clau, {})
    d[quin] = lev(x.get("or") or "", x.get("dit") or "")
    d["n"] = len(x.get("or") or "")
    d["cap"] = x.get("video")


def delta(mostra):
    ea = sum(x[0] for x in mostra)
    ed = sum(x[1] for x in mostra)
    n = sum(x[2] for x in mostra)
    return (ed - ea) / max(1, n)


def interval(bons, per_cap, unitat):
    rnd = random.Random(LLAVOR)
    caps = sorted(per_cap)
    reps = []
    for _ in range(VEGADES):
        if unitat == "capitol":
            tria = [f for _ in caps for f in per_cap[rnd.choice(caps)]]
        else:
            tria = [bons[rnd.randrange(len(bons))] for _ in bons]
        if tria:
            reps.append(delta(tria))
    reps.sort()
    return reps[int(.025 * len(reps))], reps[int(.975 * len(reps))]


def diu(lo, hi):
    return "MILLORA" if hi < 0 else ("EMPITJORA" if lo > 0 else "no es pot dir")


print(f"{'prova':<16}{'caps':>5}{'frases':>8}{'punt':>9}"
      f"{'   per frase (el que es feia)':<31}{'   per la unitat correcta':<29}")
veredictes = {}
for prova, frases in sorted(per.items()):
    bons, per_cap = [], defaultdict(list)
    for v in frases.values():
        if "abans" in v and "despres" in v and v["n"]:
            t = (v["abans"], v["despres"], v["n"])
            bons.append(t)
            per_cap[v["cap"]].append(t)
    if len(bons) < 30:
        continue
    punt = delta(bons)
    #: La unitat es la que es va mostrejar de debo. Les frases d'un capitol llarg no son
    #: independents (mateixa veu, mateix so, mateix lector), pero els 256 clips del Common
    #: Voice si que ho son: alla el "capitol" es un sol camp i remostrejar-lo dona sempre la
    #: mateixa mostra -- un interval d'amplada zero que diu MILLORA per construccio.
    unitat = "capitol" if (len(per_cap) >= 3 and len(bons) / len(per_cap) >= 5) else "frase"
    fl, fh = interval(bons, per_cap, "frase")
    cl, ch = interval(bons, per_cap, unitat)
    print(f"{prova:<16}{len(per_cap):5d}{len(bons):8d}{punt:+9.4f}"
          f"   [{fl:+.4f}, {fh:+.4f}] {diu(fl, fh):<14}"
          f"   [{cl:+.4f}, {ch:+.4f}] {diu(cl, ch)}  ({unitat})")
    veredictes[prova] = (diu(fl, fh), diu(cl, ch))

print()
for unitat, i in (("per frase", 0), ("per capítol", 1)):
    millora = [p for p, v in veredictes.items() if v[i] == "MILLORA"]
    empitjora = [p for p, v in veredictes.items() if v[i] == "EMPITJORA"]
    adopta = not empitjora and len(millora) >= 2
    print(f"regla {unitat:<12}: millora {len(millora)} {millora} · empitjora {len(empitjora)}"
          f"  ->  {'ADOPTA' if adopta else 'NO ADOPTA'}")
