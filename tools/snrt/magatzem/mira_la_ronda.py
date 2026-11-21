"""Llegir el resultat de la ronda: per prova i, als capitols retinguts, per CAPITOL.

La predicció que vaig escriure abans de mesurar-la: els dos retinguts que l'orella entén
(Zahour, Akounad) han de millorar i els dos que no (Khbiza, Abarnous) **no s'han de moure**. Si
els dolents també milloren, el límit és el domini i no el parlant, i el pla canvia.

El numero global de `snrt-retingut` no serveix per jutjar-ho: barreja els quatre capitols i els
dos dolents hi queden diluits. Per aixo es llegeix `snrt_B_sortides.json`, que porta una fila
per tall amb el capitol, i es calcula el CER abans i despres capitol a capitol.

També es diu si la regla d'acceptació es compleix, que no la toco: `M_{r+1}` només si dues
proves milloren i cap no empitjora.

    mira_la_ronda.py [carpeta_de_sortida]
"""
import io
import json
import glob
import os
import sys
from collections import defaultdict
from pathlib import Path

SORTIDA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"E:/tamazight/_magatzem/ronda/sortida")
RETINGUTS = {"jerkqzqplguvpzoh": "Zahour (l'entén)", "wckionryvrwatrvs": "Akounad (l'entén)",
             "hmssyuzoyqzywbaj": "Khbiza (no)", "oeeljuwkqlqtebzr": "Abarnous (no)"}


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


res = None
for p in SORTIDA.glob("*_resultat.json"):
    res = json.load(io.open(p, encoding="utf-8"))
    print(f"=== {p.name}")
    print("config:", json.dumps(res.get("config", {}), ensure_ascii=False))
    r = res.get("resultats", {})
    if "abans" in r and "despres" in r:
        print(f"\n{'prova':<18}{'abans':>9}{'despres':>10}{'canvi':>9}")
        milloren = empitjoren = 0
        for nom in r["abans"]:
            a = r["abans"][nom]["cer_ric"]
            d = r["despres"][nom]["cer_ric"]
            print(f"{nom:<18}{a:9.4f}{d:10.4f}{d-a:+9.4f}")
            if d < a - 1e-6:
                milloren += 1
            elif d > a + 1e-6:
                empitjoren += 1
        print(f"\nproves que milloren: {milloren} · que empitjoren: {empitjoren}")
        print("la regla d'acceptacio ("
              + ("ES COMPLEIX" if milloren >= 2 and empitjoren == 0 else "NO es compleix")
              + "): dues milloren i cap empitjora")

for p in SORTIDA.glob("*_sortides.json"):
    files = json.load(io.open(p, encoding="utf-8"))
    per = defaultdict(lambda: {"abans": [0, 0], "despres": [0, 0]})
    #: el nucli pot etiquetar "despres" o "després": s accepten tots dos
    for x in files:
        if x.get("prova") != "snrt-retingut":
            continue
        slug = (x.get("video") or "")[:16]
        etiqueta = x.get("model", "abans")
        etiqueta = "abans" if etiqueta.startswith("abans") else "despres"
        c = per[slug][etiqueta]
        c[0] += lev(x.get("or") or "", x.get("dit") or "")
        c[1] += len(x.get("or") or "")
    if not per:
        continue
    print(f"\n=== {p.name}: els capitols retinguts, un per un")
    print(f"{'capitol':<22}{'talls':>7}{'abans':>9}{'despres':>10}{'canvi':>9}")
    for slug, c in sorted(per.items(), key=lambda kv: RETINGUTS.get(kv[0], "z")):
        a = c["abans"][0] / max(1, c["abans"][1])
        d = c["despres"][0] / max(1, c["despres"][1])
        n = sum(1 for x in files if (x.get("video") or "")[:16] == slug
                and (x.get("model") or "").startswith("abans"))
        print(f"{RETINGUTS.get(slug, slug)[:20]:<22}{n:7d}{a:9.4f}{d:10.4f}{d-a:+9.4f}")
    print("\nla predicció era: els dos que l'entén milloren, els dos que no NO es mouen")
