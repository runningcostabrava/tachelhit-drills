"""El diccionari norma <-> rifeny, tret de les parelles ANCORADES que son paraules diferents.

Si el subtitol dels episodis rifenys es una traduccio a la norma de l'IRCAM (i els arabismes
diuen que si: l'orella hi casa igual que als tachelhit i amb el tifinag tres vegades menys),
llavors alla on l'ull i l'orella diuen paraules COMPLETAMENT diferents no hi ha soroll: hi ha la
parella de traduccio. `ⵜⵔⵉⵍⵉⵜ` escrit i *tadhišt* dit; `ⵉⵛⵇⴰ` escrit i *təqsəḥ* dit.

Fins ara ho buscava amb el filtre al reves: demanant que es diferenciessin en UNA consonant, que
es el que fa una variant fonetica. Una substitucio lexica es l'altra cosa: distancia GRAN.

Les dues condicions que les fan de fiar, les mateixes de sempre:

  - **ancoratge**: la paraula d'abans i la de despres han de casar (distancia <= 0,35). Si els
    dos costats estan clavats, el que hi ha al mig esta al seu lloc per força.
  - **repeticio en boques diferents**: la mateixa parella ha de sortir en dos episodis o mes, que
    vol dir dos convidats diferents. Una vegada pot ser qualsevol cosa.

    diccionari_norma_rifeny.py [varietat]
"""
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402
from alinea_paraules import alinea  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
VARIETAT = sys.argv[1] if len(sys.argv) > 1 else "tarifit"
LLUNY, A_PROP, SEGUR = .6, .35, .85
MIN_BOQUES = 2

var = {r["capitol"]: r["varietat"]
       for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}

sentit = {}
for l in io.open(r"E:/tamazight/_sentit/sortida_26/sentit.jsonl", encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x


def prop(a, b):
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


parelles = defaultdict(lambda: {"n": 0, "caps": set(), "ex": []})
mirades = ancorades = 0
for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    if var.get(x["capitol"]) != VARIETAT:
        continue
    s = sentit.get(x["id"], {})
    paraules = s.get("paraules") or []
    ull = [w for w in (x.get("tifinag") or "").split() if w.strip()]
    if len(paraules) < 3 or len(ull) < 3:
        continue
    al = alinea([p["p"] for p in paraules], ull)
    dists = [prop(esquelet(paraules[i]["p"]), esquelet(ull[j])) if j is not None else None
             for i, j in al]
    for pos, (i, j) in enumerate(al):
        if j is None or pos == 0 or pos == len(al) - 1:
            continue
        d = dists[pos]
        if d is None or d < LLUNY or paraules[i]["c"] < SEGUR:
            continue
        mirades += 1
        da, dp = dists[pos - 1], dists[pos + 1]
        if da is None or dp is None or da > A_PROP or dp > A_PROP:
            continue
        eu, eo = esquelet(ull[j]), esquelet(paraules[i]["p"])
        if len(eu) < 3 or len(eo) < 3:
            continue
        ancorades += 1
        v = parelles[(ull[j], paraules[i]["p"])]
        v["n"] += 1
        v["caps"].add(x["capitol"])
        if len(v["ex"]) < 2 and (x.get("catala") or "").strip():
            v["ex"].append(x["catala"][:56])

print(f"{VARIETAT}: parelles llunyanes mirades {mirades} · ancorades pels dos costats {ancorades}")
bones = {k: v for k, v in parelles.items() if len(v["caps"]) >= MIN_BOQUES}
print(f"formes diferents ancorades {len(parelles)} · en {MIN_BOQUES}+ boques: {len(bones)}")

if bones:
    with io.open(MAG / f"diccionari_{VARIETAT}.tsv", "w", encoding="utf-8",
                 newline="\n") as f:
        f.write("escrit_a_la_norma\tdit\tvegades\tboques\texemple\n")
        for (n, dit), v in sorted(bones.items(), key=lambda kv: -kv[1]["n"]):
            f.write(f"{n}\t{dit}\t{v['n']}\t{len(v['caps'])}\t"
                    f"{v['ex'][0] if v['ex'] else ''}\n")
    print(f"\n{'escrit (norma)':<16}{'dit':<16}{'veg':>5}{'boques':>7}  significat")
    for (n, dit), v in sorted(bones.items(), key=lambda kv: -kv[1]["n"])[:20]:
        print(f"{n[:15]:<16}{dit[:15]:<16}{v['n']:5d}{len(v['caps']):7d}  "
              f"{v['ex'][0][:36] if v['ex'] else ''}")
    print(f"\ndesat a {MAG}/diccionari_{VARIETAT}.tsv")
else:
    print("cap parella no es repeteix en dues boques: encara no hi ha materia per al diccionari")
    mostra = sorted(parelles.items(), key=lambda kv: -kv[1]["n"])[:12]
    if mostra:
        print(f"\nles ancorades d'una sola boca, per si diuen alguna cosa:")
        for (n, dit), v in mostra:
            print(f"   {n[:14]:<16}{dit[:14]:<16}{v['ex'][0][:40] if v['ex'] else ''}")
