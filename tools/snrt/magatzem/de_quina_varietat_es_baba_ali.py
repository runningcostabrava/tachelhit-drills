"""De quina varietat es el Baba Ali, dit pel lexic.

El classificador per lexic nomes necessita el que sent l'orella -- no el tifinag, que al Baba Ali
gairebe no es llegeix. I esta validat: deixant-ne un fora, encerta 20 de 22 episodis de Tadfi, i
els tres de l'Atles central (que no van participar mai en el lexic) cauen entremig i tirant cap
al tachelhit, que es on la geografia els posa.

El lexic es fa amb els 22 episodis de Tadfi de les dues bandes i es puntua el Baba Ali, que no hi
ha participat. La condicio de comparabilitat: el Baba Ali s'ha sentit amb el MATEIX model
(MMS-1b-all + `shi` + l'adaptador afinat).

Importa perque el Baba Ali son 30 episodis: unes 7.500 repliques. Saber de quina varietat son
canvia que valen.
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
BABA = Path(sys.argv[1]) if len(sys.argv) > 1 else MAG / "prova_baba" / "sentit_nostre.jsonl"

var = {r["capitol"]: r["varietat"]
       for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}

sentit = {}
for l in io.open(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x

#: les formes segures de cada episodi de Tadfi
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

c = defaultdict(lambda: defaultdict(int))
eps = defaultdict(lambda: defaultdict(set))
tot = defaultdict(int)
for cap, formes in per_ep.items():
    v = var.get(cap)
    if v not in ("tachelhit", "tarifit"):
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
print(f"lèxic: {len(sh)} formes del tachelhit · {len(rf)} del tarifit")

if not BABA.exists():
    raise SystemExit(f"encara no hi ha {BABA}")
baba = defaultdict(lambda: defaultdict(int))
for l in io.open(BABA, encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    ep = x["id"].split(":")[0]
    for p in (x.get("paraules") or []):
        if p.get("c", 0) >= .85 and len(esquelet(p["p"])) >= 3:
            baba[ep][p["p"]] += 1

print(f"\n{'episodi':<18}{'paraules':>9}{'sh/1000':>9}{'rf/1000':>9}{'diu':>12}")
t_sh = t_rf = t_n = 0
for ep in sorted(baba):
    formes = baba[ep]
    n = sum(formes.values())
    if n < 100:
        print(f"{ep:<18}{n:9d}   (poques paraules per dir-ne res)")
        continue
    n_sh = 1000 * sum(v for f, v in formes.items() if f in sh) / n
    n_rf = 1000 * sum(v for f, v in formes.items() if f in rf) / n
    diu = "tachelhit" if n_sh > 1.6 * n_rf else ("tarifit" if n_rf > 1.6 * n_sh else "al mig")
    print(f"{ep:<18}{n:9d}{n_sh:9.1f}{n_rf:9.1f}{diu:>12}")
    t_sh += sum(v for f, v in formes.items() if f in sh)
    t_rf += sum(v for f, v in formes.items() if f in rf)
    t_n += n

if t_n:
    a, b = 1000 * t_sh / t_n, 1000 * t_rf / t_n
    print(f"\nen conjunt: sh {a:.1f}/1000 · rf {b:.1f}/1000")
    print("per comparar (dels episodis de Tadfi, de fora de mostra):")
    print("   tachelhit      89-192/1000 de sh · 16-38 de rf")
    print("   Atles central  61-106/1000 de sh · 28-37 de rf")
    print("   tarifit         8-60/1000 de sh · 42-75 de rf")
