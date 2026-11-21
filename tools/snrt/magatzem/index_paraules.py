"""L'index per paraula: una fila per forma, amb de que se'n pot fiar un.

El que demanaves: «pots tenir un index per paraula». Les ocurrencies ja hi eren
(`ocurrencies_triat.jsonl`, una linia per paraula sentida); el que faltava es la taula d'una
fila per FORMA, que es on es treballa.

La fiabilitat no es un numero inventat per mi: son els fets que la sostenen, tots quatre
comptables i cap d'ells opinable.

    vegades      quantes vegades s'ha sentit la forma
    amb acord    de quantes l'ull hi casa (distancia <= 0,35 sobre l'esquelet de consonants)
    boques       en quants episodis diferents, que vol dir quants convidats diferents
    confiança    la mitjana de la que diu el transcriptor

L'ordre es per **vegades amb acord**, que es el fet mes fort que tenim: dos testimonis que no
saben res l'un de l'altre dient la mateixa cosa, i diverses vegades. No hi ha cap pes ni cap
formula: una forma acordada deu vegades per cinc boques es solida i no cal cap teoria per
dir-ho.

Surt `index_paraules.tsv`.
"""
import io
import json
from collections import defaultdict
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")

formes = defaultdict(lambda: {"n": 0, "acord": 0, "caps": set(), "conf": [], "normes":
                              defaultdict(int), "ex": None})
for l in io.open(MAG / "ocurrencies_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    e = x.get("esquelet") or ""
    if len(e) < 2:
        continue
    f = formes[x["sentit"]]
    f["n"] += 1
    f["caps"].add(x["capitol"])
    if x.get("conf") is not None:
        f["conf"].append(x["conf"])
    casa = x.get("norma") and x.get("dist") is not None and x["dist"] <= .35
    if casa:
        f["acord"] += 1
        f["normes"][x["norma"]] += 1
        if not f["ex"] and x.get("catala"):
            f["ex"] = x["catala"][:70]
    elif not f["ex"] and x.get("catala"):
        f["ex"] = x["catala"][:70]

files = []
for forma, f in formes.items():
    norma = max(f["normes"], key=f["normes"].get) if f["normes"] else ""
    files.append((f["acord"], f["n"], len(f["caps"]),
                  sum(f["conf"]) / len(f["conf"]) if f["conf"] else 0, forma, norma,
                  f["ex"] or ""))
files.sort(key=lambda r: (-r[0], -r[2], -r[1]))

with io.open(MAG / "index_paraules.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("sentit\tescrit\tvegades\tamb_acord\tboques\tconfianca\texemple\n")
    for acord, n, boques, conf, forma, norma, ex in files:
        f.write(f"{forma}\t{norma}\t{n}\t{acord}\t{boques}\t{conf:.3f}\t{ex}\n")

print(f"formes diferents: {len(files)}")
for llindar in (1, 2, 3, 5, 10):
    q = sum(1 for r in files if r[0] >= llindar)
    print(f"   acordades {llindar}+ vegades: {q}")
print(f"   acordades 2+ vegades i en 2+ boques: "
      f"{sum(1 for r in files if r[0] >= 2 and r[2] >= 2)}")

print(f"\n{'sentit':<16}{'escrit':<14}{'veg':>5}{'acord':>7}{'boques':>8}{'conf':>7}  significat")
for acord, n, boques, conf, forma, norma, ex in files[:24]:
    print(f"{forma[:15]:<16}{norma[:13]:<14}{n:5d}{acord:7d}{boques:8d}{conf:7.2f}  {ex[:40]}")
print(f"\ndesat a {MAG / 'index_paraules.tsv'}")
