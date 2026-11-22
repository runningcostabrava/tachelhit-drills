"""La taula estàndard ↔ dialecte, ara amb les paraules alineades per ordre.

La primera versió aparellava cada paraula sentida amb la més semblant de la línia, cadascuna pel
seu compte, i sortien parelles inventades (`nnk` amb `ungal`). Ara l'aparellament ve de
`alinea_paraules.py`, que fa una alineació global: respecta l'ordre i no deixa que dues paraules
sentides es mengin la mateixa de la pantalla.

Es demana, per a cada correspondència:
  - que l'orella la senti amb confiança alta (si dubta, la diferència pot ser seva);
  - que les dues formes **s'assemblin prou** (distància ≤ 0,6): si no s'assemblen gens, no són la
    mateixa paraula dita de dues maneres, és que l'alineació ha fet el que ha pogut;
  - i que surti **en més d'un capítol**: una vegada és casualitat; repetida amb veus diferents,
    és un patró.
"""
import io
import json
from collections import defaultdict
from pathlib import Path

MAG = Path(r"E:\tamazight\_magatzem")
DESTI = MAG / "estandard_dialecte.jsonl"
CONF_MIN, DIST_MAX, MIN_CAP = 0.9, 0.6, 2

files = [json.loads(l) for l in io.open(MAG / "parelles_alineades.jsonl", encoding="utf-8")
         if l.strip()]
print(f"paraules alineades: {len(files)}")

p = defaultdict(lambda: {"cap": set(), "n": 0, "ex": []})
for r in files:
    if not r.get("norma_llati") or r["conf"] < CONF_MIN or r["dist"] is None:
        continue
    if r["dist"] == 0 or r["dist"] > DIST_MAX:
        continue
    a, b = r["norma_llati"], r["parla"].lower()
    if len(a) < 2 or len(b) < 2:
        continue
    d = p[(a, b)]
    d["cap"].add(r["capitol"])
    d["n"] += 1
    if len(d["ex"]) < 2 and r.get("catala"):
        d["ex"].append(r["catala"][:58])

bones = {k: v for k, v in p.items() if len(v["cap"]) >= MIN_CAP}
print(f"parelles diferents: {len(p)}   en {MIN_CAP}+ capítols: {len(bones)}")

with io.open(DESTI, "w", encoding="utf-8", newline="\n") as f:
    for (a, b), v in sorted(bones.items(), key=lambda t: -t[1]["n"]):
        f.write(json.dumps({"norma": a, "parla": b, "vegades": v["n"],
                            "capitols": len(v["cap"]), "exemples": v["ex"]},
                           ensure_ascii=False) + "\n")
print(f"desat a {DESTI}\n")
print(f"{'la norma escriu':>16}  {'es diu':<16} vegades capítols")
for (a, b), v in sorted(bones.items(), key=lambda t: -t[1]["n"])[:30]:
    print(f"{a:>16}  {b:<16} {v['n']:5d}  {len(v['cap']):4d}")

una = sum(v["n"] for (a, b), v in bones.items()
          if abs(len(a) - len(b)) <= 1 and sum(x != y for x, y in zip(a, b)) <= 1)
tot = sum(v["n"] for v in bones.values())
print(f"\nde {tot} ocurrències: {una} ({100*una/max(1,tot):.0f}%) difereixen en una lletra "
      f"(ortografia o fonètica), {tot-una} en més")
