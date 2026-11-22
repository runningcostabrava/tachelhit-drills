"""Un episodi es pot classificar nomes pel seu lexic? Provat deixant-ne un fora.

El lexic diferencial (`lexic_diferencial.tsv`) s'ha tret dels episodis tachelhit i tarifit, de
manera que mirar com de be els separa seria trampa: els ha vist. La prova honesta es
**deixar-ne un fora**: per cada episodi, es refa el lexic amb els ALTRES i despres es puntua
l'episodi que no ha participat.

Els tres de l'Atles central no han participat mai en el lexic (nomes s'hi van fer servir les dues
bandes), de manera que son una prova de fora de mostra de franc: la puntuacio ha de dir on cauen
en el continu.

La puntuacio es simple i explicable: de les formes que l'episodi diu, quantes son de la banda
tachelhit i quantes de la tarifit, per mil paraules de l'episodi. Es diu la rao.
"""
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
MIN_TOTAL, MIN_EPISODIS = 12, 3

var = {r["capitol"]: r["varietat"]
       for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}
titols = {r["capitol"]: r["titol"]
          for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}

sentit = {}
for l in io.open(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x

#: les formes segures de cada episodi
per_ep = defaultdict(lambda: defaultdict(int))
for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    if x["capitol"] not in var:
        continue
    s = sentit.get(x["id"], {})
    for p in (s.get("paraules") or []):
        if p.get("c", 0) >= .85 and len(esquelet(p["p"])) >= 3:
            per_ep[x["capitol"]][p["p"]] += 1


def fes_lexic(fora):
    """El lexic diferencial fet NOMES amb els episodis de les dues bandes, menys `fora`."""
    c = defaultdict(lambda: defaultdict(int))
    eps = defaultdict(lambda: defaultdict(set))
    tot = defaultdict(int)
    for cap, formes in per_ep.items():
        v = var.get(cap)
        if cap == fora or v not in ("tachelhit", "tarifit"):
            continue
        for forma, n in formes.items():
            c[forma][v] += n
            eps[forma][v].add(cap)
            tot[v] += n
    sh, rf = set(), set()
    for forma, d in c.items():
        if d["tachelhit"] + d["tarifit"] < MIN_TOTAL:
            continue
        pm_sh = 1000 * d["tachelhit"] / max(1, tot["tachelhit"])
        pm_rf = 1000 * d["tarifit"] / max(1, tot["tarifit"])
        if pm_sh > pm_rf and len(eps[forma]["tachelhit"]) >= MIN_EPISODIS:
            sh.add(forma)
        elif pm_rf > pm_sh and len(eps[forma]["tarifit"]) >= MIN_EPISODIS:
            rf.add(forma)
    return sh, rf


print(f"{'episodi':<26}{'varietat marcada':<26}{'sh/1000':>9}{'rf/1000':>9}{'diu':>12}")
encerts = total = 0
for cap in sorted(per_ep, key=lambda c: (var.get(c, "z"), titols.get(c, c))):
    formes = per_ep[cap]
    n = sum(formes.values())
    if n < 200:
        continue
    sh, rf = fes_lexic(cap)
    n_sh = 1000 * sum(v for f, v in formes.items() if f in sh) / n
    n_rf = 1000 * sum(v for f, v in formes.items() if f in rf) / n
    diu = "tachelhit" if n_sh > 1.6 * n_rf else ("tarifit" if n_rf > 1.6 * n_sh else "al mig")
    marcada = var.get(cap, "?")
    if marcada in ("tachelhit", "tarifit"):
        total += 1
        encerts += diu == marcada
    print(f"{titols.get(cap, cap)[:24]:<26}{marcada:<26}{n_sh:9.1f}{n_rf:9.1f}{diu:>12}")
print(f"\nde fora de mostra, a les dues bandes: {encerts} de {total} ben classificats")
print("els tres de l'Atles central no han participat MAI en el lexic: on cauen ho diu el continu")
