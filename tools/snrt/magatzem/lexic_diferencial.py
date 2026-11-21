"""Quines formes distingeixen el tachelhit del tarifit dins del nostre propi corpus.

Ara que cada episodi porta la seva varietat (`varietats.json`), es pot fer una cosa que abans no:
comptar cada forma sentida per mil paraules a cada varietat i veure quines es reparteixen
desigualment. Aixo dona un **lexic diferencial** tret de casa, sense diccionari ni informant.

Dues precaucions:

  - es compta per MIL paraules, no en brut, perque les dues meitats no tenen la mateixa mida;
  - es demana un minim d'ocurrencies i que surti en diversos episodis de la seva banda, perque
    si no el que surt es el vocabulari d'UN convidat (el seu poble, el titol del seu llibre) i no
    de la varietat.

Les formes surten del nostre transcriptor, que es de tachelhit: les del tarifit les sentira
pitjor, i aixo es un biaix que cal dir. Pero el que es busca aqui no es la forma exacta sino
QUINES es reparteixen desigualment, i aixo el biaix no ho inventa.

Surt `lexic_diferencial.tsv`.
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

sentit = {}
for l in io.open(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x

compte = defaultdict(lambda: defaultdict(int))
episodis = defaultdict(lambda: defaultdict(set))
total = defaultdict(int)
exemple = {}
for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    v = var.get(x["capitol"])
    if v not in ("tachelhit", "tarifit"):
        continue
    s = sentit.get(x["id"], {})
    for p in (s.get("paraules") or []):
        if p.get("c", 0) < .85:
            continue
        e = esquelet(p["p"])
        if len(e) < 3:
            continue
        compte[p["p"]][v] += 1
        episodis[p["p"]][v].add(x["capitol"])
        total[v] += 1
        if p["p"] not in exemple and (x.get("catala") or "").strip():
            exemple[p["p"]] = x["catala"][:58]

files = []
for forma, c in compte.items():
    n = c["tachelhit"] + c["tarifit"]
    if n < MIN_TOTAL:
        continue
    pm_sh = 1000 * c["tachelhit"] / max(1, total["tachelhit"])
    pm_rf = 1000 * c["tarifit"] / max(1, total["tarifit"])
    #: de quina banda es, i si hi surt en prou episodis per no ser d'un convidat sol
    if pm_sh > pm_rf:
        banda, forca, eps = "tachelhit", pm_sh / max(pm_rf, .01), len(episodis[forma]["tachelhit"])
    else:
        banda, forca, eps = "tarifit", pm_rf / max(pm_sh, .01), len(episodis[forma]["tarifit"])
    if eps < MIN_EPISODIS:
        continue
    files.append((forca, banda, forma, c["tachelhit"], c["tarifit"], eps,
                  exemple.get(forma, "")))

files.sort(reverse=True)
with io.open(MAG / "lexic_diferencial.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("forma\tbanda\tforca\tn_tachelhit\tn_tarifit\tepisodis\texemple\n")
    for forca, banda, forma, a, b, eps, ex in files:
        f.write(f"{forma}\t{banda}\t{forca:.1f}\t{a}\t{b}\t{eps}\t{ex}\n")

print(f"paraules segures comptades: tachelhit {total['tachelhit']} · tarifit {total['tarifit']}")
print(f"formes amb {MIN_TOTAL}+ ocurrencies i {MIN_EPISODIS}+ episodis: {len(files)}")
for banda in ("tarifit", "tachelhit"):
    seves = [f for f in files if f[1] == banda][:14]
    print(f"\n--- les mes del {banda}")
    print(f"{'forma':<16}{'sh':>5}{'rf':>5}{'eps':>5}  significat de la seva linia")
    for forca, b, forma, a, bb, eps, ex in seves:
        print(f"{forma[:15]:<16}{a:5d}{bb:5d}{eps:5d}  {ex[:42]}")
print(f"\ndesat a {MAG / 'lexic_diferencial.tsv'}")
