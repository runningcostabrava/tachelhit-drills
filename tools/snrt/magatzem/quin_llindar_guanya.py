"""Els dos llindars, cara a cara, nomes alla on la comparacio val.

La ronda es va fer dues vegades: **A** amb llindar d'esquelet 0,35 (el d'ara) i **B** amb 0,20.
El 20-11 al mati vaig dir que A guanyava i que B no passava la regla. Les dues coses s'han de
matisar:

* **B tambe passa la regla** quan es remostreja per capitol, que es la unitat correcta (PR #711).
  El «no passa» sortia de remostrejar frases.
* La fila que feia guanyar A era `snrt-retingut`, i alla **la comparacio no val**: les dues
  execucions van tallar els mateixos capitols en talls diferents (A=279/B=296 en un video, 148
  comuns...), de manera que es comparava el 46 % dels talls, triat per una coincidencia del
  tallador.

Les quatre proves amb **veritat humana** casen al 100 %, i son les uniques on es pot comparar A
contra B de debo. Aqui es fa aparellat, tall a tall, i amb remostreig per capitol.

Negatiu = B (0,20) ho fa millor.

    quin_llindar_guanya.py
"""
import io
import json
import random
from collections import defaultdict
from pathlib import Path

A = Path(r"E:/tamazight/_magatzem/ronda/sortida/snrt_B_sortides.json")
B = Path(r"E:/tamazight/_magatzem/ronda_020/sortida/snrt_B_sortides.json")
HUMANES = ("zouhir-tests", "tfa-226", "cv-zgh-test", "test-fora")
VEGADES = 2000


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


def despres(cami):
    """{(prova, video, de, or): errors del model entrenat}."""
    fora = {}
    for x in json.load(io.open(cami, encoding="utf-8")):
        if (x.get("model") or "").startswith("abans"):
            continue
        de = round(x["de"], 2) if isinstance(x["de"], (int, float)) else str(x["de"])
        fora[(x["prova"], x.get("video"), de, x.get("or") or "")] = lev(x.get("or") or "",
                                                                       x.get("dit") or "")
    return fora


a, b = despres(A), despres(B)
comunes = sorted(set(a) & set(b))
print(f"{len(a)} talls al braç A · {len(b)} al B · {len(comunes)} comuns\n")

print(f"{'prova':<16}{'caps':>5}{'talls':>7}{'A (0,35)':>10}{'B (0,20)':>10}"
      f"{'B − A':>9}   interval per capítol")
for prova in HUMANES:
    q = [k for k in comunes if k[0] == prova]
    if not q:
        continue
    per_cap = defaultdict(list)
    for k in q:
        per_cap[k[1]].append((a[k], b[k], len(k[3])))
    tots = [p for c in per_cap.values() for p in c]
    n = max(1, sum(x[2] for x in tots))
    ca, cb = sum(x[0] for x in tots) / n, sum(x[1] for x in tots) / n
    caps = sorted(per_cap)
    rnd = random.Random(20261120)
    reps = []
    for _ in range(VEGADES):
        tria = [p for _ in caps for p in per_cap[rnd.choice(caps)]] if len(caps) >= 3 else \
               [tots[rnd.randrange(len(tots))] for _ in tots]
        m = max(1, sum(x[2] for x in tria))
        reps.append((sum(x[1] for x in tria) - sum(x[0] for x in tria)) / m)
    reps.sort()
    lo, hi = reps[int(.025 * VEGADES)], reps[int(.975 * VEGADES) - 1]
    diu = "B millor" if hi < 0 else ("A millor" if lo > 0 else "no es pot dir")
    print(f"{prova:<16}{len(per_cap):5d}{len(q):7d}{ca:10.4f}{cb:10.4f}{cb-ca:+9.4f}"
          f"   [{lo:+.4f}, {hi:+.4f}] {diu}")

#: i les quatre juntes, que es com es decideix
tots, per_cap = [], defaultdict(list)
for k in comunes:
    if k[0] in HUMANES:
        per_cap[(k[0], k[1])].append((a[k], b[k], len(k[3])))
tots = [p for c in per_cap.values() for p in c]
n = max(1, sum(x[2] for x in tots))
caps = sorted(per_cap)
rnd = random.Random(20261120)
reps = sorted((sum(x[1] for x in t) - sum(x[0] for x in t)) / max(1, sum(x[2] for x in t))
              for t in ([p for _ in caps for p in per_cap[rnd.choice(caps)]]
                        for _ in range(VEGADES)))
lo, hi = reps[int(.025 * VEGADES)], reps[int(.975 * VEGADES) - 1]
d = (sum(x[1] for x in tots) - sum(x[0] for x in tots)) / n
diu = "B millor" if hi < 0 else ("A millor" if lo > 0 else "NO ES POT DIR: són iguals")
print(f"\nles quatre juntes ({len(caps)} capítols, {len(tots)} talls): "
      f"B − A = {d:+.4f}  [{lo:+.4f}, {hi:+.4f}]  →  {diu}")
