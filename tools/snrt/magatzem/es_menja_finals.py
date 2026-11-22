"""L'orella es menja el final de les paraules? I quant?

Mirant les 43 parelles ancorades, el defecte que mes es repeteix no es de llengua sino de
model: `iskkiln` surt `iskil`, `tullist` surt `tulli`, `asmuttg` surt `asmut`, `muḥmmd` surt
`muḥm`. Si aixo es un biaix i no una impressio meva, s'ha de veure en dos numeros:

  1. l'esquelet de l'orella ha de ser MES CURT que el de l'ull, de mitjana;
  2. els errors han d'estar al FINAL de la paraula mes que al principi.

El segon es mesura amb el prefix comu: si l'orella encerta el principi i falla el final, el
prefix comu sera gran comparat amb la llargada. Si s'equivoques a l'atzar, no.

Importa perque diu que es pot guanyar sense tocar el model: la regla del grau A castiga igual
un error al principi (que vol dir «no ho ha entes») i una terminacio escapçada (que vol dir
«ho ha entes i no ho ha acabat d'escriure»).
"""
import io, json, statistics, sys
from collections import Counter
sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402

def prefix(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def sufix(a, b):
    return prefix(a[::-1], b[::-1])


dif, prefixos, sufixos, c = [], [], [], Counter()
for l in io.open(r"E:/tamazight/_magatzem/ocurrencies_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    if not x.get("norma") or x.get("dist") is None or x["conf"] < .85:
        continue
    eu, eo = esquelet(x["norma"]), x["esquelet"]
    if len(eu) < 3 or len(eo) < 3:
        continue
    c["parelles"] += 1
    dif.append(len(eo) - len(eu))
    if eu != eo:
        c["diferents"] += 1
        p, s = prefix(eu, eo), sufix(eu, eo)
        prefixos.append(p / max(len(eu), len(eo)))
        sufixos.append(s / max(len(eu), len(eo)))
        if p > s:
            c["falla al final"] += 1
        elif s > p:
            c["falla al principi"] += 1
        else:
            c["igual"] += 1

print(f"parelles mirades: {c['parelles']} · diferents: {c['diferents']}")
print(f"\nllargada de l'esquelet, orella menys ull:")
print(f"   mitjana {statistics.mean(dif):+.2f} consonants · mediana {statistics.median(dif):+.0f}")
print(f"   l'orella es mes curta: {100*sum(1 for d in dif if d < 0)/len(dif):.0f}% "
      f"· mes llarga: {100*sum(1 for d in dif if d > 0)/len(dif):.0f}% "
      f"· igual: {100*sum(1 for d in dif if d == 0)/len(dif):.0f}%")
print(f"\non falla, quan no casen exactament:")
for k in ("falla al final", "falla al principi", "igual"):
    print(f"   {k:<20}{c[k]:6d}  {100*c[k]/max(1,c['diferents']):5.1f}%")
print(f"\nprefix comu mitja: {100*statistics.mean(prefixos):.0f}% de la paraula"
      f" · sufix comu mitja: {100*statistics.mean(sufixos):.0f}%")
