"""El +0,0026 del tfa-226 es un empitjorament de debo o es soroll?

La regla d'acceptacio del cercle demana que **cap prova no empitjori amb interval de confiança**,
i jo he llegit punts. De les cinc proves, quatre milloren i una puja 0,26 punts: tota la decisio
penja d'aquest numero, i 0,26 punts sobre 226 clips pot ser qualsevol cosa.

Es mesura amb remostreig (bootstrap) sobre les MATEIXES frases abans i despres: es trien 226
frases a l'atzar amb reposicio, es calcula la diferencia de CER, i es repeteix mil vegades. Si
l'interval del 95 % passa per zero, no es pot dir que empitjori.

Es fa per a totes cinc, que aixi es veu quines milloren de debo.
"""
import io
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

#: quin braç es mesura: `ronda/sortida` (llindar 0,35) o `ronda_020/sortida` (0,20)
SORTIDA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"E:/tamazight/_magatzem/ronda/sortida")
VEGADES = 1000


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


files = json.load(io.open(SORTIDA / "snrt_B_sortides.json", encoding="utf-8"))
#: per prova i per frase: (errors abans, errors despres, lletres)
per = defaultdict(dict)
for x in files:
    quin = "abans" if (x.get("model") or "").startswith("abans") else "despres"
    clau = (x.get("video"), str(x.get("de")), x.get("or"))
    d = per[x["prova"]].setdefault(clau, {})
    d[quin] = lev(x.get("or") or "", x.get("dit") or "")
    d["n"] = len(x.get("or") or "")

rnd = random.Random(20261120)
print(f"{'prova':<18}{'Δ CER':>9}{'interval 95 %':>22}{'frases':>8}  diu")
for prova, frases in sorted(per.items()):
    bons = [(v["abans"], v["despres"], v["n"]) for v in frases.values()
            if "abans" in v and "despres" in v and v["n"]]
    if len(bons) < 30:
        continue
    def delta(mostra):
        ea = sum(x[0] for x in mostra)
        ed = sum(x[1] for x in mostra)
        n = sum(x[2] for x in mostra)
        return (ed - ea) / max(1, n)
    punt = delta(bons)
    reps = sorted(delta([bons[rnd.randrange(len(bons))] for _ in bons])
                  for _ in range(VEGADES))
    baix, alt = reps[int(.025 * VEGADES)], reps[int(.975 * VEGADES)]
    if alt < 0:
        diu = "MILLORA"
    elif baix > 0:
        diu = "EMPITJORA"
    else:
        diu = "no es pot dir (passa per zero)"
    print(f"{prova:<18}{punt:+9.4f}   [{baix:+.4f}, {alt:+.4f}]{len(bons):8d}  {diu}")
print(f"\n(remostreig de {VEGADES} vegades sobre les mateixes frases abans i després)")
