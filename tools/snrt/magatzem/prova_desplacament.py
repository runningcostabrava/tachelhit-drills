"""Els capitols a ~1% comparen cada replica amb el so d'una altra?

Els numeros d'acord no fan un continu: o 23-42% o ~1%, i res al mig. Una averia de qualitat
(fons carregat, lletra petita, parla rapida) donaria un continu. Una distribucio de dos pics
fa pensar en un desajust d'index: si la retxa k de l'ull es compara amb el so de la retxa k+d,
l'acord cau a l'atzar pur encara que les dues lectures siguin bones.

Es prova desplacant l'orella de -3 a +3 retxes. Si a d=0 l'acord es 1% i a d=2 puja a 25%,
el problema no es ni l'ull ni l'orella: es l'aparellament, i es arreglable.
"""
import io, json, sys
from pathlib import Path
sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402

SENTIT = Path(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl")
RELLEGIT = Path(r"E:/tamazight/_magatzem/rellegit_bo")
VISOR = Path(r"E:/tamazight/_visor")

sentit = {}
for l in io.open(SENTIT, encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = (x.get("sentit") or "").strip()

print(f"{'capitol':<18}" + "".join(f"{d:>8}" for d in range(-3, 4)))
for p in sorted(RELLEGIT.glob("*.json")):
    slug = p.stem
    llegit = json.load(io.open(p, encoding="utf-8"))["llegit"]
    if len(llegit) < 100:
        continue
    fila = []
    for d in range(-3, 4):
        a = n = 0
        for k, ull in llegit.items():
            try:
                k2 = str(int(k) + d)
            except ValueError:
                continue
            eu, eo = esquelet(ull), esquelet(sentit.get(f"{slug}:{k2}", ""))
            if not eu or not eo:
                continue
            n += 1
            a += (lev(eu, eo) / max(len(eu), len(eo))) <= .35
        fila.append(100 * a / max(1, n))
    millor = max(range(7), key=lambda i: fila[i]) - 3
    print(f"{slug[:16]:<18}" + "".join(f"{v:7.1f}%" for v in fila)
          + ("   <- el millor es d=%+d" % millor if millor else ""))
