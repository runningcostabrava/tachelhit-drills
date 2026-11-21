"""L'acord cau amb la llargada de la replica?

Mirant casos ha sortit que al capitol bo les replicas son de 2-3 paraules i casen, i al dolent
son de 8-10 i l'orella es desfa (amb confianca 0,8, que per aixo no serveix de filtre). Si es
aixo, la distribucio de dos pics no diu res dels capitols: diu com de llargues son les seves
frases, i aixo es una propietat del PROGRAMA (una entrevista amb frases curtes contra un
monoleg).

La consequencia seria forta: la taxa d'acord PER REPLICA es una mala mesura, perque castiga les
frases llargues encara que portin paraules ben llegides a dins. La unitat bona es la PARAULA.

Es mira l'acord per trams de llargada, ajuntant tots els capitols, i la llargada mitjana de
cada capitol contra el seu acord.
"""
import io, json, statistics, sys
from pathlib import Path
sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402

SENTIT = Path(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl")
RELLEGIT = Path(r"E:/tamazight/_magatzem/rellegit_bo")

sentit = {}
for l in io.open(SENTIT, encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = (x.get("sentit") or "").strip()

TRAMS = [(1, 1), (2, 2), (3, 3), (4, 5), (6, 8), (9, 12), (13, 99)]
per_tram = {t: [0, 0] for t in TRAMS}
per_cap = {}
for p in sorted(RELLEGIT.glob("*.json")):
    slug = p.stem
    llegit = json.load(io.open(p, encoding="utf-8"))["llegit"]
    if len(llegit) < 100:
        continue
    a = n = 0
    llargs = []
    for k, ull in llegit.items():
        eu, eo = esquelet(ull), esquelet(sentit.get(f"{slug}:{k}", ""))
        if not eu or not eo:
            continue
        np_ = len([w for w in ull.split() if esquelet(w)])
        casa = (lev(eu, eo) / max(len(eu), len(eo))) <= .35
        n += 1
        a += casa
        llargs.append(np_)
        for t in TRAMS:
            if t[0] <= np_ <= t[1]:
                per_tram[t][1] += 1
                per_tram[t][0] += casa
    if n >= 50:
        per_cap[slug] = (a / n, statistics.mean(llargs))

print("acord per llargada de la replica (tots els capitols junts)")
print(f"{'paraules':<12}{'replicas':>10}{'acord':>9}")
for t in TRAMS:
    a, n = per_tram[t]
    if n:
        et = f"{t[0]}" if t[0] == t[1] else (f"{t[0]}-{t[1]}" if t[1] < 99 else f"{t[0]}+")
        print(f"{et:<12}{n:10d}{100*a/n:8.1f}%")

xs = [v[1] for v in per_cap.values()]
ys = [v[0] for v in per_cap.values()]
mx, my = statistics.mean(xs), statistics.mean(ys)
num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** .5
print(f"\ncorrelacio acord <-> paraules per replica: {num/den if den else 0:+.2f}")
print(f"{'capitol':<18}{'acord':>8}{'paraules/replica':>19}")
for slug, (a, ll) in sorted(per_cap.items(), key=lambda kv: -kv[1][0]):
    print(f"{slug[:16]:<18}{100*a:7.1f}%{ll:19.1f}")
