"""L'orella falla, o el subtitol esta traduit a l'estandard?

Mirant una linia de l'episodi de Khbiza (0,4 % d'acord) ha sortit una altra explicacio possible:

    tifinag  ⵎⴽⵍⵍⵉ ⵜ ⴷⵍ ⵖⵔ ⵏⵎⴰⵍⵍⵓ, ⵉⵛⵇⴰ ⴰⴷ ⵏⴰⵍ ⴽⵔⴰ ⵏ ⵜⵔⵉⵍⵉⵜ ⴳⵉⵙ
    catala   Tal com vaig entrar al sindicat, es dificil trobar-hi una dona
    orella   nnaqaba ... tadišt n tarifšt

L'orella sent *nnaqaba* (النقابة, el sindicat) i *tadišt* (dona), i aixo es el que diu el catala.
El tifinag diu el mateix amb PARAULES DIFERENTS. Si aixo passa sovint, l'orella no falla: el
subtitol es una traduccio a la norma de l'IRCAM, i per al rifeny la traduccio canvia gairebe tot.

El tercer testimoni que ho separa, i de franc: **els arabismes**. Una paraula arab que el
convidat diu surt tambe al subtitol ARAB, amb les seves consonants. Si l'orella encerta
arabismes als episodis rifenys al mateix ritme que als tachelhit, l'orella funciona i el que
discrepa es el tifinag.

Es compta, per episodi: de les paraules sentides amb confiança alta, quantes casen amb una
paraula del subtitol ARAB de la mateixa replica (esquelet de consonants, distancia <= 0,25
perque son paraules curtes), i quantes casen amb una del TIFINAG.
"""
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"E:/tamazight/_magatzem")
from tria_el_millor_text import esquelet, lev  # noqa: E402
from parla_arab_o_amazic import esquelet_arab  # noqa: E402

MAG = Path(r"E:/tamazight/_magatzem")
SENTIT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"E:/tamazight/_sentit/sortida_26/sentit.jsonl")
LLINDAR = .25
MIN_LLETRES = 4

var = {r["capitol"]: r["varietat"]
       for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}
titols = {r["capitol"]: r["titol"]
          for r in json.load(io.open(MAG / "varietats.json", encoding="utf-8"))}

sentit = {}
for l in io.open(SENTIT, encoding="utf-8"):
    if l.strip():
        x = json.loads(l)
        sentit[x["id"]] = x


def prop(a, b):
    return 1.0 if not a or not b else lev(a, b) / max(len(a), len(b))


c = defaultdict(lambda: {"n": 0, "arab": 0, "tif": 0})
exemples = []
for l in io.open(MAG / "text_triat.jsonl", encoding="utf-8"):
    if not l.strip():
        continue
    x = json.loads(l)
    s = sentit.get(x["id"])
    if not s:
        continue
    ar = [esquelet_arab(w) for w in (x.get("arab") or "").split()]
    tf = [esquelet(w) for w in (x.get("tifinag") or "").split()]
    ar = [e for e in ar if len(e) >= MIN_LLETRES]
    tf = [e for e in tf if len(e) >= MIN_LLETRES]
    if not ar and not tf:
        continue
    d = c[x["capitol"]]
    for p in (s.get("paraules") or []):
        if p.get("c", 0) < .85:
            continue
        e = esquelet(p["p"])
        if len(e) < MIN_LLETRES:
            continue
        d["n"] += 1
        casa_ar = any(prop(e, a) <= LLINDAR for a in ar)
        casa_tf = any(prop(e, t) <= LLINDAR for t in tf)
        d["arab"] += casa_ar
        d["tif"] += casa_tf
        if (casa_ar and not casa_tf and len(exemples) < 6
                and var.get(x["capitol"]) == "tarifit"):
            exemples.append((p["p"], (x.get("arab") or "")[:34], (x.get("catala") or "")[:40]))

files = []
for cap, d in c.items():
    if d["n"] < 100:
        continue
    files.append((var.get(cap, "?"), titols.get(cap, cap), d["n"],
                  d["arab"] / d["n"], d["tif"] / d["n"]))
files.sort()

print(f"{'varietat':<12}{'episodi':<24}{'paraules':>9}{'casa amb arab':>15}{'casa amb tifinag':>18}")
for v, t, n, pa, pt in files:
    print(f"{v[:10]:<12}{t[:22]:<24}{n:9d}{100*pa:14.1f}%{100*pt:17.1f}%")

print(f"\n{'varietat':<26}{'casa amb arab':>15}{'casa amb tifinag':>18}{'rao':>8}")
per_var = defaultdict(lambda: [0, 0, 0])
for v, t, n, pa, pt in files:
    g = per_var[v]
    g[0] += pa * n
    g[1] += pt * n
    g[2] += n
for v, g in sorted(per_var.items()):
    pa, pt = 100 * g[0] / g[2], 100 * g[1] / g[2]
    print(f"{v:<26}{pa:14.1f}%{pt:17.1f}%{pa/max(pt,.01):8.2f}")

if exemples:
    print("\narabismes que l'orella encerta i el tifinag no porta (episodis rifenys):")
    for p, ar, ca in exemples:
        print(f"   {p:<16}{ar:<36}{ca}")
print("\nsi l'orella casa amb l'arab igual a les dues varietats, l'orella funciona i el que")
print("discrepa es el tifinag: el subtitol esta traduit a la norma.")
