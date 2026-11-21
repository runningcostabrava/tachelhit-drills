"""El lexic separa de debo, o separaria igual amb les etiquetes a l'atzar?

El lexic diferencial posa tots els grups de la biblioteca al costat tachelhit, amb una rao de
3 a 5 contra 1. Aixo pot voler dir dues coses molt diferents:

  a) que les formes del tachelhit son de debo del tachelhit, i la biblioteca n'es;
  b) que les formes del tachelhit son simplement les paraules amazigues MES FREQUENTS, que
     surten a qualsevol text, i les del rifeny son rareses. Llavors qualsevol corpus del mon
     sortiria «tachelhit» i la prova no val res.

Es distingeix amb una prova nul·la: es reparteixen els 22 episodis en dos grups A i B **a
l'atzar**, de les mateixes mides que els de debo, es fa el lexic igual, i es mira quina rao treu
a la biblioteca. Si les raons de l'atzar son tan grans com la de debo, la separacio no diu res.

PREDICCIO: si la separacio es real, la rao de debo ha de quedar fora del que fa l'atzar gairebe
sempre. Si queda dins del nuvol, ho he de desdir.
"""
import io
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
MANIFEST = Path(r"E:/tamazight/_entrenament/manifest_v3.jsonl")
MIN_TOTAL, MIN_EPISODIS, VEGADES = 12, 3, 200

var = {r["capitol"]: r["varietat"]
       for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}
sentit = {}
for l in io.open(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x

per_ep = defaultdict(lambda: defaultdict(int))
for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    if x["capitol"] not in var:
        continue
    for p in (sentit.get(x["id"], {}).get("paraules") or []):
        if p.get("c", 0) >= .85 and len(esquelet(p["p"])) >= 3:
            per_ep[x["capitol"]][esquelet(p["p"])] += 1

biblio = defaultdict(int)
for l in io.open(MANIFEST, encoding="utf-8"):
    if not l.strip():
        continue
    for w in (json.loads(l).get("text") or "").lower().split():
        w = esquelet(w.strip(".,;:!?«»\"'()[]"))
        if len(w) >= 3:
            biblio[w] += 1
n_biblio = sum(biblio.values())


def fes_lexic(grup_a, grup_b):
    """Les formes de cada grup, pel mateix criteri de sempre."""
    c = defaultdict(lambda: defaultdict(int))
    eps = defaultdict(lambda: defaultdict(set))
    tot = defaultdict(int)
    for cap, formes in per_ep.items():
        g = "a" if cap in grup_a else ("b" if cap in grup_b else None)
        if not g:
            continue
        for forma, n in formes.items():
            c[forma][g] += n
            eps[forma][g].add(cap)
            tot[g] += n
    a, b = set(), set()
    for forma, d in c.items():
        if d["a"] + d["b"] < MIN_TOTAL:
            continue
        pm_a = d["a"] / max(1, tot["a"])
        pm_b = d["b"] / max(1, tot["b"])
        if pm_a > pm_b and len(eps[forma]["a"]) >= MIN_EPISODIS:
            a.add(forma)
        elif pm_b > pm_a and len(eps[forma]["b"]) >= MIN_EPISODIS:
            b.add(forma)
    return a, b


def rao(a, b):
    """Quantes vegades mes densa es la familia A que la B, a la biblioteca."""
    na = sum(k for f, k in biblio.items() if f in a)
    nb = sum(k for f, k in biblio.items() if f in b)
    return (na + .5) / (nb + .5), na, nb


sh_caps = [c for c, v in var.items() if v == "tachelhit" and c in per_ep]
rf_caps = [c for c, v in var.items() if v == "tarifit" and c in per_ep]
a, b = fes_lexic(set(sh_caps), set(rf_caps))
r_debo, na, nb = rao(a, b)
print(f"de debo (tachelhit contra tarifit): {len(a)} i {len(b)} formes · "
      f"{na} i {nb} aparicions a la biblioteca · rao {r_debo:.2f}")

rnd = random.Random(20261120)
tots = sh_caps + rf_caps
raons = []
for _ in range(VEGADES):
    rnd.shuffle(tots)
    ga, gb = set(tots[:len(sh_caps)]), set(tots[len(sh_caps):])
    x, y = fes_lexic(ga, gb)
    raons.append(rao(x, y)[0])
raons.sort()
pitjors = sum(1 for r in raons if r >= r_debo)
print(f"a l'atzar ({VEGADES} repartiments): mediana {raons[len(raons)//2]:.2f} · "
      f"del 5 % al 95 % entre {raons[int(.05*len(raons))]:.2f} i {raons[int(.95*len(raons))]:.2f} · "
      f"maxim {raons[-1]:.2f}")
print(f"\nrepartiments a l'atzar que igualen o superen el de debo: {pitjors} de {VEGADES} "
      f"(p = {(pitjors + 1) / (VEGADES + 1):.3f})")
print("si aixo no es petit, la separacio no vol dir res i ho he de desdir.")
