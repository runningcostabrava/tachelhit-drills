"""El glossari que surt del cami invers: forma, que vol dir, i amb quina forca es sap.

La fitxa de fiabilitat (`fitxa_de_fiabilitat.py`) diu quines formes es diuen i si un diccionari
les te, **pero no diu que volen dir**. Aquestes si: han sortit perque el significat de l'arab
feia esperar una paraula concreta dins d'una cadena enganxada, i **l'ull l'hi ha trobat**.

L'index de fiabilitat te tres senyals, i cap d'ells surt de la nostra orella sola:

  * **vegades** -- quants cops la parella forma/significat s'ha confirmat;
  * **capitols** -- en quants capitols diferents (un sol capitol pot ser una casualitat d'aquell
    parlant o d'aquell tema);
  * **l'ull** -- totes son confirmades per l'ull, que llegeix la imatge i no ha sentit res; el
    que canvia es quantes vegades.

Veredictes:
  `ferma`     tres capitols o mes -> no depen d'un parlant ni d'un tema
  `bona`      dos capitols
  `una sola`  un capitol: val, pero es una sola boca

    glossari_del_significat.py
"""
import collections
import io
import json
from pathlib import Path

MAG = Path(r"E:/tamazight/_magatzem")
ENTRA = MAG / "formes_pel_significat.json"
SURT = MAG / "glossari_del_significat.tsv"

trob = json.load(io.open(ENTRA, encoding="utf-8"))
print(f"{len(trob)} troballes confirmades per l'ull")

per = collections.defaultdict(lambda: {"cops": 0, "caps": set(), "cadenes": set(),
                                       "frases": []})
for t in trob:
    d = per[(t["forma"], t["vol_dir"])]
    d["cops"] += 1
    d["caps"].add(t.get("capitol") or "?")
    d["cadenes"].add(t.get("cadena") or "")
    if t.get("catala") and len(d["frases"]) < 2:
        d["frases"].append(t["catala"])

files = []
for (forma, vol), d in per.items():
    n_caps = len(d["caps"])
    verdicte = "ferma" if n_caps >= 3 else ("bona" if n_caps == 2 else "una sola")
    files.append({"forma": forma, "vol_dir": vol, "cops": d["cops"], "capitols": n_caps,
                  "cadenes": len(d["cadenes"]), "verdicte": verdicte,
                  "exemple": (d["frases"] or [""])[0]})
files.sort(key=lambda r: (-r["capitols"], -r["cops"], r["forma"]))

with io.open(SURT, "w", encoding="utf-8", newline="\n") as f:
    f.write("forma\tvol_dir\tcops\tcapitols\tcadenes\tverdicte\texemple\n")
    for r in files:
        f.write("\t".join(str(r[k]) for k in
                          ("forma", "vol_dir", "cops", "capitols", "cadenes", "verdicte",
                           "exemple")) + "\n")

c = collections.Counter(r["verdicte"] for r in files)
print(f"\n{len(files)} parelles forma/significat")
for v in ("ferma", "bona", "una sola"):
    print(f"   {v:<10}{c[v]:5d}")

print("\nLes que s'aguanten en més capítols:")
print(f"{'forma':<18}{'vol dir':<18}{'cops':>5}{'caps':>6}  exemple")
for r in files[:14]:
    print(f"{r['forma']:<18}{r['vol_dir']:<18}{r['cops']:>5}{r['capitols']:>6}  "
          f"{r['exemple'][:46]}")
print(f"\nescrit {SURT.name}")
