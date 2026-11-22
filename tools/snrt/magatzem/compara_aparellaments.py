"""El numero de paraules de grau A cau de 13.422 a 2.330. Es el bo, o l'alineacio esta trencada?

Abans cada paraula sentida s'aparellava amb la MES SEMBLANT de la linia, cadascuna pel seu
compte; ara es fa una alineacio global per ordre. El numero cau un 83%, i una caiguda aixi
s'ha de mirar abans de donar-la per bona: pot ser que l'alineacio nova no estigui fent la
seva feina.

Es compten les dues maneres sobre les MATEIXES linies i es miren casos: quines parelles perd
l'alineacio per ordre i si tenia rao de perdre-les.
"""
import io, json, sys
from collections import Counter
sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402
from alinea_paraules import alinea  # noqa: E402

SENTIT = r"E:/tamazight/_sentit/sortida_26/sentit.jsonl"
SEGUR = .85


def prop(a, b):
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


sentit = {}
for l in io.open(SENTIT, encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x

triat = {}
for l in io.open(r"E:/tamazight/_magatzem/text_triat.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        triat[x["id"]] = x

c = Counter()
nomes_veinat, nomes_ordre = [], []
for ident, x in triat.items():
    s = sentit.get(ident, {})
    paraules = s.get("paraules") or []
    ull = [w for w in (x.get("tifinag") or "").split() if w.strip()]
    if not paraules or not ull:
        continue
    parelles = alinea([p["p"] for p in paraules], ull)
    for p, (norma, dist) in zip(paraules, parelles):
        if p["c"] < SEGUR:
            continue
        c["segures"] += 1
        #: veinatge: la mes semblant de la linia, sense mirar l'ordre
        e = esquelet(p["p"])
        millor, d2 = None, 1.0
        for w in ull:
            d = prop(e, esquelet(w))
            if d < d2:
                millor, d2 = w, d
        a_ordre = norma is not None and dist is not None and dist <= .35
        a_veinat = millor is not None and d2 <= .35
        c["A per ordre"] += a_ordre
        c["A per veinatge"] += a_veinat
        if a_veinat and not a_ordre and len(nomes_veinat) < 8:
            nomes_veinat.append((p["p"], millor, round(d2, 2), norma, x.get("tifinag", "")[:46]))
        if a_ordre and not a_veinat and len(nomes_ordre) < 4:
            nomes_ordre.append((p["p"], norma, round(dist, 2)))

print(dict(c))
print("\nparelles que el veinatge dona i l'ordre nega (les 8 primeres):")
print(f"{'sentit':<14}{'veinatge diu':<16}{'dist':>6}  {'ordre diu':<14}linia")
for p, m, d, n, li in nomes_veinat:
    print(f"{p[:13]:<14}{m[:15]:<16}{d:6.2f}  {str(n)[:13]:<14}{li}")
if nomes_ordre:
    print("\ni les que nomes dona l'ordre:")
    for p, n, d in nomes_ordre:
        print(f"   {p} ~ {n}  ({d})")
