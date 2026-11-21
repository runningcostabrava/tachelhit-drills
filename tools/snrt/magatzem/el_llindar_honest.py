"""La taula que decideix el llindar del cercle, sense les dues trampes que tenia.

El cercle accepta un tall com a etiqueta quan l'esquelet del que l'orella diu i el de la
referencia s'assemblen prou. Triar aquest llindar es la decisio de la ronda, i la taula que la
sostenia enganyava per dos costats:

**1. Les paraules curtes forcen el resultat.** El 23 % de les parelles tenen un esquelet de
referencia d'**una** consonant: alla «distancia relativa <= 0,35» vol dir «identic», i la
precisio es del 100 % per construccio, no perque el filtre funcioni. 1.277 de les 2.971 que
passaven (el 43 %) tenien dues consonants o menys.

**2. El record es calculava sobre una poblacio ja filtrada.** Es comptava sobre les parelles que
l'alineador havia aparellat, i les paraules de la persona que es queden sense parella es
descartaven en silenci: **739 de 4.611 (el 16 %) no arribaven mai al denominador**. Sortia
99,7 % quan de debo es 43 %.

Aqui el record es **sobre tot el que la persona va dir**, i la precisio es dona tambe nomes amb
esquelets de tres consonants o mes, que es on el llindar decideix alguna cosa.

    el_llindar_honest.py
"""
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from alinea_paraules import alinea          # noqa: E402
from tria_el_millor_text import esquelet, lev  # noqa: E402

SORTIDES = Path(r"E:/tamazight/_magatzem/ronda/sortida/snrt_B_sortides.json")
PROVES = ("zouhir-tests", "tfa-226", "cv-zgh-test", "test-fora")
LLINDARS = (0.00, 0.10, 0.15, 0.20, 0.25, 0.35, 0.50)


def prop(a, b):
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


#: Cada parella: (llargada de l'esquelet de la referencia, distancia d'esquelet, es identica?)
parelles = []
tot_ref = sense_parella = 0
for x in json.load(io.open(SORTIDES, encoding="utf-8")):
    if x.get("prova") not in PROVES or (x.get("model") or "").startswith("abans"):
        continue
    v = [w for w in (x.get("or") or "").split() if w.strip()]
    o = [w for w in (x.get("dit") or "").split() if w.strip()]
    tot_ref += len(v)
    aparellades = 0
    for i, j in alinea(v, o):
        if i is None:
            continue
        if j is None:
            continue
        aparellades += 1
        ev, eo = esquelet(v[i]), esquelet(o[j])
        parelles.append((len(ev), prop(ev, eo), v[i].lower() == o[j].lower()))
    sense_parella += len(v) - aparellades

print(f"{tot_ref} paraules de la persona · {len(parelles)} aparellades · "
      f"{sense_parella} sense parella ({100*sense_parella/tot_ref:.0f} %)\n")

curtes = sum(1 for L, _, _ in parelles if L <= 2)
print(f"amb esquelet de referència de 2 consonants o menys: {curtes} "
      f"({100*curtes/len(parelles):.0f} % de les aparellades)\n")

print(f"{'llindar':>8}{'passen':>8}{'precisió':>10}{'record':>9}"
      f"{'   │':>4}{'passen':>8}{'precisió':>10}{'record':>9}   (només esquelet ≥ 3)")
for t in LLINDARS:
    fila = []
    for minim in (1, 3):
        q = [(L, d, ig) for L, d, ig in parelles if L >= minim]
        passen = [(L, d, ig) for L, d, ig in q if d <= t]
        bones = sum(1 for _, _, ig in passen if ig)
        prec = 100 * bones / len(passen) if passen else 0
        #: el record es sobre TOT el que la persona va dir, no sobre el que l'alineador va casar
        rec = 100 * bones / tot_ref
        fila.append((len(passen), prec, rec))
    print(f"{t:>8.2f}{fila[0][0]:>8}{fila[0][1]:>9.1f}%{fila[0][2]:>8.1f}%"
          f"{'   │':>4}{fila[1][0]:>8}{fila[1][1]:>9.1f}%{fila[1][2]:>8.1f}%")

#: Quantes de les que passen el llindar NO son identiques: si en son poques, el llindar no es
#: un llindar, es una comparacio d'igualtat amb un altre nom.
print("\nde les que passen, quantes NO són la mateixa paraula (si són poques, el llindar "
      "és «idèntic» amb un altre nom):")
for t in LLINDARS:
    passen = [(L, d, ig) for L, d, ig in parelles if d <= t]
    diff = sum(1 for _, _, ig in passen if not ig)
    print(f"   llindar {t:.2f}: {len(passen):5d} passen, {diff:5d} no idèntiques "
          f"({100*diff/max(1,len(passen)):.0f} %)")
