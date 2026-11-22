"""La taula norma <-> parla, ANCORADA per les paraules del costat.

Sense ancoratge la taula no dona res de bo: les 8 parelles que sobreviuen a la repeticio son
totes el mateix artefacte, la frase *tutlayt tamazight* aparellada amb un lloc de desplaçament.
La causa es que l'ull i l'orella no parteixen les paraules al mateix lloc, i llavors l'alineacio
llisca dins del grup nominal.

L'ancoratge ho tanca: una parella de grau B nomes val si la paraula de l'ABANS i la del DESPRES
casen totes dues (distancia <= 0,35). Si els dos costats estan clavats, el que hi ha al mig esta
al seu lloc per força, i la diferencia que s'hi veu es de llengua, no d'alineacio.

Es la mateixa idea del 29-10 (els casaments segurs fan d'ancoratge i l'ordre jutja els altres),
aplicada DINS de la linia.

Surt `norma_parla_ancorada.tsv`.
"""
import io, json, os, glob, sys
from collections import defaultdict
sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402
from alinea_paraules import alinea  # noqa: E402

MAG = r"E:/tamazight/_magatzem"
MIN_VEGADES, MIN_BOQUES, SEGUR = 1, 1, .85


def prop(a, b):
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


sentit = {}
for l in io.open(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x

parelles = defaultdict(lambda: {"n": 0, "caps": set(), "ex": []})
mirades = ancorades = 0
for l in io.open(f"{MAG}/text_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    s = sentit.get(x["id"], {})
    paraules = s.get("paraules") or []
    ull = [w for w in (x.get("tifinag") or "").split() if w.strip()]
    if len(paraules) < 3 or len(ull) < 3:
        continue
    al = alinea([p["p"] for p in paraules], ull)
    #: la distancia de cada posicio, o None si no te parella
    dists = [prop(esquelet(paraules[i]["p"]), esquelet(ull[j])) if j is not None else None
             for i, j in al]
    for pos, (i, j) in enumerate(al):
        if j is None or pos == 0 or pos == len(al) - 1:
            continue
        d = dists[pos]
        if d is None or not (.35 < d <= .7) or paraules[i]["c"] < SEGUR:
            continue
        mirades += 1
        da, dp = dists[pos - 1], dists[pos + 1]
        if da is None or dp is None or da > .35 or dp > .35:
            continue
        eu, eo = esquelet(ull[j]), esquelet(paraules[i]["p"])
        if len(eu) < 3 or len(eo) < 3 or abs(len(eu) - len(eo)) > 2:
            continue
        ancorades += 1
        k = (ull[j], paraules[i]["p"])
        v = parelles[k]
        v["n"] += 1
        v["caps"].add(x["capitol"])
        if len(v["ex"]) < 2 and x.get("catala"):
            v["ex"].append(x["catala"][:60])

print(f"parelles de grau B mirades: {mirades} · ancorades pels dos costats: {ancorades}")
bones = {k: v for k, v in parelles.items()
         if v["n"] >= MIN_VEGADES and len(v["caps"]) >= MIN_BOQUES}
print(f"formes diferents ancorades: {len(parelles)} · "
      f"que es repeteixen {MIN_VEGADES}+ vegades en {MIN_BOQUES}+ boques: {len(bones)}")

with io.open(f"{MAG}/norma_parla_ancorada.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("escrit\tsentit\tvegades\tboques\texemple\n")
    for (n, dit), v in sorted(bones.items(), key=lambda kv: -kv[1]["n"]):
        f.write(f"{n}\t{dit}\t{v['n']}\t{len(v['caps'])}\t{v['ex'][0] if v['ex'] else ''}\n")

print(f"\n{'escrit':<16}{'sentit':<16}{'vegades':>8}{'boques':>8}")
for (n, dit), v in sorted(bones.items(), key=lambda kv: -kv[1]["n"])[:30]:
    print(f"{n[:15]:<16}{dit[:15]:<16}{v['n']:8d}{len(v['caps']):8d}")
print(f"\ndesat a {MAG}/norma_parla_ancorada.tsv")
